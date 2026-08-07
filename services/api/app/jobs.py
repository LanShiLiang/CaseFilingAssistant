from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.dossier import DossierV2
from app.extraction import ExtractionResult, extract_pages, parse_legal_basis
from app.generation import GenerationContext, generate_package
from app.models import Document, Generation, Job, Matter, ValidationRun, utc_now
from app.storage import LocalBlobStore, StoredBlob

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClaimedJob:
    id: str
    lease_token: str
    input_revision: int
    kind: str


class JobProcessor:
    """可靠任务编排器：耗时计算不持有业务事务，所有发布均受租约 CAS 保护。"""

    def __init__(self, database: Database, store: LocalBlobStore, settings: Settings):
        self.database = database
        self.store = store
        self.settings = settings
        self.worker_id = f"worker-{secrets.token_hex(6)}"

    def claim(self) -> ClaimedJob | None:
        now = utc_now()
        with self.database.session_factory.begin() as session:
            exhausted = session.scalars(
                select(Job)
                .where(
                    Job.status == "running",
                    Job.leased_until < now,
                    Job.attempt_count >= Job.max_attempts,
                )
                .with_for_update(skip_locked=True)
            ).all()
            for job in exhausted:
                job.status = "failed_terminal"
                job.error_code = "worker_attempts_exhausted"
                job.progress = None
                job.lease_owner = None
                job.lease_token = None
                job.leased_until = None
                job.heartbeat_at = None
                if job.kind == "parse_document":
                    document = session.get(Document, str(job.payload.get("document_id", "")))
                    if document:
                        document.parse_status = "failed"
                elif job.kind == "generate_package":
                    generation = session.get(
                        Generation, str(job.payload.get("generation_id", ""))
                    )
                    if generation:
                        generation.status = "failed"
                        generation.error_code = job.error_code
            query = (
                select(Job)
                .where(
                    or_(
                        and_(
                            Job.status.in_(["pending", "retry_scheduled"]),
                            Job.available_at <= now,
                        ),
                        and_(
                            Job.status == "running",
                            Job.leased_until < now,
                            Job.attempt_count < Job.max_attempts,
                        ),
                    )
                )
                .order_by(Job.created_at, Job.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            job = session.scalar(query)
            if not job:
                return None
            token = secrets.token_hex(24)
            job.status = "running"
            job.attempt_count += 1
            job.progress = 5
            job.lease_owner = self.worker_id
            job.lease_token = token
            job.heartbeat_at = now
            job.leased_until = now + timedelta(seconds=self.settings.worker_lease_seconds)
            return ClaimedJob(
                id=job.id,
                lease_token=token,
                input_revision=job.input_revision,
                kind=job.kind,
            )

    def heartbeat(self, claimed: ClaimedJob) -> bool:
        now = utc_now()
        with self.database.session_factory.begin() as session:
            result = session.execute(
                update(Job)
                .where(
                    Job.id == claimed.id,
                    Job.status == "running",
                    Job.lease_token == claimed.lease_token,
                )
                .values(
                    heartbeat_at=now,
                    leased_until=now + timedelta(seconds=self.settings.worker_lease_seconds),
                )
            )
            return result.rowcount == 1

    def _heartbeat_loop(
        self, claimed: ClaimedJob, stop: threading.Event, lost: threading.Event
    ) -> None:
        interval = max(0.5, min(10.0, self.settings.worker_lease_seconds / 3))
        while not stop.wait(interval):
            try:
                if not self.heartbeat(claimed):
                    lost.set()
                    return
                self._touch_worker_heartbeat()
            except Exception:  # noqa: BLE001 - 发布 CAS 仍会阻止失租任务写回
                logger.warning("job_heartbeat_failed", extra={"job_id": claimed.id})

    def _touch_worker_heartbeat(self) -> None:
        heartbeat = self.settings.worker_heartbeat_file
        heartbeat.parent.mkdir(parents=True, exist_ok=True)
        temporary = heartbeat.with_name(f".{heartbeat.name}.{self.worker_id}.tmp")
        temporary.write_text(str(time.time()), encoding="ascii")
        os.replace(temporary, heartbeat)

    def cleanup_orphans(self) -> None:
        """只清理超过安全窗口且没有数据库引用的临时/正式 Blob。"""

        with self.database.session_factory() as session:
            upload_keys = set(session.scalars(select(Document.storage_key)).all())
            package_keys = {
                key for key in session.scalars(select(Generation.package_key)).all() if key
            }
            preview_keys = {
                key for key in session.scalars(select(Generation.preview_key)).all() if key
            }
        referenced_generated = package_keys | preview_keys
        self.store.delete_unreferenced(
            "staging", set(), self.settings.blob_orphan_grace_seconds
        )
        self.store.delete_unreferenced(
            "uploads", upload_keys, self.settings.blob_orphan_grace_seconds
        )
        self.store.delete_unreferenced(
            "generated", referenced_generated, self.settings.blob_orphan_grace_seconds
        )

    def process(self, claimed: ClaimedJob) -> None:
        stop = threading.Event()
        lost = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            args=(claimed, stop, lost),
            name=f"job-heartbeat-{claimed.id}",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            if claimed.kind == "parse_document":
                self._parse_document(claimed)
            elif claimed.kind == "generate_package":
                self._generate_package(claimed)
            else:
                raise ValueError("unknown_job_kind")
        except Exception as exc:  # noqa: BLE001 - worker 必须把未知错误收敛为任务状态
            logger.error(
                "job_failed",
                extra={"job_id": claimed.id, "error_code": type(exc).__name__},
            )
            self._record_failure(claimed, exc)
        finally:
            stop.set()
            heartbeat_thread.join(timeout=2)
            if lost.is_set():
                logger.warning("job_lease_lost", extra={"job_id": claimed.id})

    @staticmethod
    def _owned_job(session: Session, claimed: ClaimedJob, *, lock: bool = False) -> Job | None:
        query = select(Job).where(
            Job.id == claimed.id,
            Job.status == "running",
            Job.lease_token == claimed.lease_token,
        )
        if lock:
            query = query.with_for_update()
        return session.scalar(query)

    @staticmethod
    def _finish(job: Job, result: dict[str, object]) -> None:
        job.status = "completed"
        job.progress = 100
        job.result = result
        job.lease_owner = None
        job.lease_token = None
        job.leased_until = None
        job.heartbeat_at = None

    def _parse_document(self, claimed: ClaimedJob) -> None:
        with self.database.session_factory.begin() as session:
            job = self._owned_job(session, claimed, lock=True)
            if job is None:
                return
            document = session.get(Document, str(job.payload.get("document_id", "")))
            if document is None:
                raise ValueError("job_input_missing")
            if not document.active or document.parse_revision != claimed.input_revision:
                self._finish(job, {"superseded": True})
                return
            document.parse_status = "processing"
            job.progress = 20
            document_id = document.id
            document_kind = document.kind
            mime_type = document.mime_type
            path = self.store.path_for(document.storage_key)

        extraction: ExtractionResult | None = None
        if document_kind == "legal_basis":
            extraction = parse_legal_basis(
                path, mime_type, document_id, self.settings.max_pdf_pages
            )
            extracted_text = extraction.text
            warnings = extraction.warnings
        else:
            pages, warnings = extract_pages(path, mime_type, self.settings.max_pdf_pages)
            extracted_text = "\n\f\n".join(page.text for page in pages)

        # 耗时解析完成后重新开启短事务并读取最新 aggregate，禁止用旧 Session 覆盖用户确认。
        with self.database.session_factory.begin() as session:
            job = self._owned_job(session, claimed, lock=True)
            if job is None:
                return
            document = session.get(Document, document_id)
            matter = session.scalar(
                select(Matter).where(Matter.id == job.matter_id).with_for_update()
            )
            if document is None or matter is None:
                raise ValueError("job_input_missing")
            document.extracted_text = extracted_text
            document.parse_status = "completed"

            if matter.revision != claimed.input_revision or not document.active:
                self._finish(job, {"superseded": True, "warnings": warnings})
                return

            result_payload: dict[str, object] = {"warnings": warnings}
            if extraction is not None:
                dossier = DossierV2.from_matter(matter)
                dossier_payload = dossier.model_dump(mode="json")
                next_facts = dossier_payload["facts"]
                next_sources = dossier_payload["sources"]
                next_confirmations = dossier_payload["confirmations"]
                for field, value in extraction.facts.items():
                    if next_confirmations.get(field) != "confirmed":
                        next_facts[field] = value
                        next_sources[field] = [
                            {**source, "parse_revision": document.parse_revision}
                            for source in extraction.sources.get(field, [])
                        ]
                        next_confirmations[field] = "pending"
                next_scope_signals = [
                    signal
                    for signal in dossier_payload["scope_signals"]
                    if signal["document_id"] != document.id
                ]
                next_scope_signals.extend(extraction.scope_signals)
                DossierV2(
                    facts=next_facts,
                    sources=next_sources,
                    confirmations=next_confirmations,
                    scope_signals=next_scope_signals,
                    amount_computation=dossier.amount_computation,
                ).apply_to(matter)
                result_payload["facts"] = sorted(extraction.facts)
            self._finish(job, result_payload)

    @staticmethod
    def _snapshot_hash(snapshot: dict[str, object]) -> str:
        payload = json.dumps(
            snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _generate_package(self, claimed: ClaimedJob) -> None:
        with self.database.session_factory.begin() as session:
            job = self._owned_job(session, claimed, lock=True)
            if job is None:
                return
            matter = session.get(Matter, job.matter_id)
            generation = session.get(Generation, str(job.payload.get("generation_id", "")))
            if matter is None or generation is None:
                raise ValueError("job_input_missing")
            if matter.revision != claimed.input_revision:
                generation.status = "superseded"
                self._finish(job, {"superseded": True})
                return
            validation_run = session.get(ValidationRun, generation.validation_run_id)
            if validation_run is None or not validation_run.passed:
                raise ValueError("validation_run_invalid")
            if not generation.input_snapshot or generation.input_hash != self._snapshot_hash(
                generation.input_snapshot
            ):
                raise ValueError("generation_input_invalid")
            context = GenerationContext.from_payload(generation.input_snapshot)
            generation.status = "processing"
            job.progress = 30

        result = generate_package(context)
        staged_package = self.store.stage_bytes(".zip", result.package_bytes)
        staged_preview = self.store.stage_bytes(".pdf", result.preview_pdf)
        published: list[StoredBlob] = []
        try:
            with self.database.session_factory.begin() as session:
                job = self._owned_job(session, claimed, lock=True)
                if job is None:
                    return
                matter = session.scalar(
                    select(Matter).where(Matter.id == job.matter_id).with_for_update()
                )
                generation = session.get(
                    Generation, str(job.payload.get("generation_id", ""))
                )
                if matter is None or generation is None:
                    raise ValueError("job_input_missing")
                if matter.revision != claimed.input_revision:
                    generation.status = "superseded"
                    self._finish(job, {"superseded": True})
                    return

                package_blob = self.store.publish(staged_package, "generated")
                published.append(package_blob)
                preview_blob = self.store.publish(staged_preview, "generated")
                published.append(preview_blob)
                generation.package_key = package_blob.key
                generation.preview_key = preview_blob.key
                generation.sha256 = result.package_sha256
                generation.package_size_bytes = package_blob.size_bytes
                generation.preview_sha256 = result.preview_sha256
                generation.preview_size_bytes = preview_blob.size_bytes
                generation.artifact_manifest = result.manifest
                generation.status = "completed"
                matter.generated_revision = matter.revision
                self._finish(
                    job,
                    {"generation_id": generation.id, "manifest": result.manifest},
                )
        except Exception:
            for blob in published:
                self.store.delete(blob.key)
            raise
        finally:
            self.store.delete(staged_package.key)
            self.store.delete(staged_preview.key)

    def _record_failure(self, claimed: ClaimedJob, exc: Exception) -> None:
        with self.database.session_factory.begin() as session:
            job = self._owned_job(session, claimed, lock=True)
            if job is None:
                return
            terminal = isinstance(exc, ValueError) or job.attempt_count >= job.max_attempts
            job.error_code = str(exc) if str(exc) else type(exc).__name__
            job.lease_owner = None
            job.lease_token = None
            job.leased_until = None
            job.heartbeat_at = None
            if terminal:
                job.status = "failed_terminal"
                job.progress = None
                if job.kind == "parse_document":
                    document = session.get(Document, str(job.payload.get("document_id", "")))
                    if document:
                        document.parse_status = "failed"
                if job.kind == "generate_package":
                    generation = session.get(
                        Generation, str(job.payload.get("generation_id", ""))
                    )
                    if generation:
                        generation.status = "failed"
                        generation.error_code = job.error_code
            else:
                job.status = "retry_scheduled"
                # 小幅 jitter 避免数据库恢复时多个失败任务同一时刻争抢连接。
                retry_delay = 2**job.attempt_count + secrets.randbelow(1000) / 1000
                job.available_at = utc_now() + timedelta(seconds=retry_delay)
                job.progress = None

    def run_forever(self) -> None:
        logger.info("worker_started")
        self.cleanup_orphans()
        idle_cycles = 0
        while True:
            self._touch_worker_heartbeat()
            claimed = self.claim()
            if claimed:
                idle_cycles = 0
                self.process(claimed)
            else:
                idle_cycles += 1
                if idle_cycles % 240 == 0:
                    self.cleanup_orphans()
                time.sleep(self.settings.worker_poll_seconds)
