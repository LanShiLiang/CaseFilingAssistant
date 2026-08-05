from __future__ import annotations

import logging
import secrets
import time
from datetime import timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Database
from app.extraction import extract_pages, parse_legal_basis
from app.generation import generate_package
from app.models import Document, Generation, Job, Matter, utc_now
from app.storage import LocalBlobStore
from app.validation import validate_matter

logger = logging.getLogger(__name__)


class JobProcessor:
    def __init__(self, database: Database, store: LocalBlobStore, settings: Settings):
        self.database = database
        self.store = store
        self.settings = settings

    def claim(self) -> str | None:
        now = utc_now()
        with self.database.session_factory.begin() as session:
            # PostgreSQL 以行锁跳过其他 worker 已领取的任务；租约过期的 running 任务可被安全接管。
            query = (
                select(Job)
                .where(
                    or_(
                        and_(
                            Job.status.in_(["pending", "retry_scheduled"]), Job.available_at <= now
                        ),
                        and_(Job.status == "running", Job.leased_until < now),
                    )
                )
                .order_by(Job.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            job = session.scalar(query)
            if not job:
                return None
            job.status = "running"
            job.attempt_count += 1
            job.progress = 5
            job.lease_token = secrets.token_hex(24)
            job.leased_until = now + timedelta(seconds=self.settings.worker_lease_seconds)
            return job.id

    def process(self, job_id: str) -> None:
        try:
            with self.database.session_factory() as session:
                job = session.get(Job, job_id)
                if not job or job.status != "running":
                    return
                if job.kind == "parse_document":
                    self._parse_document(session, job)
                elif job.kind == "generate_package":
                    self._generate_package(session, job)
                else:
                    raise ValueError("unknown_job_kind")
                session.commit()
        except Exception as exc:  # noqa: BLE001 - worker 必须把未知错误收敛为稳定任务状态
            logger.exception(
                "job_failed", extra={"job_id": job_id, "error_code": type(exc).__name__}
            )
            self._record_failure(job_id, exc)

    def _parse_document(self, session: Session, job: Job) -> None:
        document = session.get(Document, str(job.payload["document_id"]))
        matter = session.get(Matter, job.matter_id)
        if not document or not matter:
            raise ValueError("job_input_missing")
        document.parse_status = "processing"
        job.progress = 20
        path = self.store.path_for(document.storage_key)
        if document.kind == "legal_basis":
            result = parse_legal_basis(
                path, document.mime_type, document.id, self.settings.max_pdf_pages
            )
            document.extracted_text = result.text
            if matter.revision == job.input_revision:
                # 抽取结果只补充未确认字段；用户已确认的事实永远不会被后台候选覆盖。
                next_facts = dict(matter.facts)
                next_sources = dict(matter.sources)
                next_confirmations = dict(matter.confirmations)
                for field, value in result.facts.items():
                    if next_confirmations.get(field) != "confirmed":
                        next_facts[field] = value
                        next_sources[field] = result.sources.get(field, [])
                        next_confirmations[field] = "pending"
                matter.facts = next_facts
                matter.sources = next_sources
                matter.confirmations = next_confirmations
                job.result = {"facts": sorted(result.facts), "warnings": result.warnings}
            else:
                job.result = {"superseded": True, "warnings": result.warnings}
        else:
            pages, warnings = extract_pages(path, document.mime_type, self.settings.max_pdf_pages)
            document.extracted_text = "\n\f\n".join(page.text for page in pages)
            job.result = {"warnings": warnings}
        document.parse_status = "completed"
        job.status = "completed"
        job.progress = 100
        job.lease_token = None
        job.leased_until = None

    def _generate_package(self, session: Session, job: Job) -> None:
        matter = session.get(Matter, job.matter_id)
        generation = session.get(Generation, str(job.payload["generation_id"]))
        if not matter or not generation:
            raise ValueError("job_input_missing")
        if matter.revision != job.input_revision:
            generation.status = "superseded"
            job.status = "completed"
            job.progress = 100
            job.result = {"superseded": True}
            return
        blocking = [issue for issue in validate_matter(matter) if issue.severity == "blocking"]
        if blocking:
            generation.status = "failed"
            generation.error_code = "validation_blocked"
            raise ValueError("validation_blocked")
        generation.status = "processing"
        job.progress = 30
        result = generate_package(matter, self.settings)
        package_blob = self.store.write_bytes("generated", ".zip", result.package_bytes)
        preview_blob = self.store.write_bytes("generated", ".pdf", result.preview_pdf)

        # 发布前再次核对 revision，防止慢任务把旧文书标记为当前版本。
        session.refresh(matter)
        if matter.revision != job.input_revision:
            generation.status = "superseded"
            job.result = {"superseded": True}
        else:
            generation.package_key = package_blob.key
            generation.preview_key = preview_blob.key
            generation.sha256 = result.package_sha256
            generation.status = "completed"
            matter.generated_revision = matter.revision
            job.result = {"generation_id": generation.id, "manifest": result.manifest}
        job.status = "completed"
        job.progress = 100
        job.lease_token = None
        job.leased_until = None

    def _record_failure(self, job_id: str, exc: Exception) -> None:
        with self.database.session_factory.begin() as session:
            job = session.get(Job, job_id)
            if not job:
                return
            # 输入/规则错误不可通过重试恢复；瞬时异常采用有上限的指数退避，避免任务无限膨胀。
            terminal = isinstance(exc, ValueError) or job.attempt_count >= job.max_attempts
            job.error_code = str(exc) if str(exc) else type(exc).__name__
            job.lease_token = None
            job.leased_until = None
            if terminal:
                job.status = "failed_terminal"
                job.progress = None
                if job.kind == "parse_document":
                    document = session.get(Document, str(job.payload.get("document_id", "")))
                    if document:
                        document.parse_status = "failed"
                if job.kind == "generate_package":
                    generation = session.get(Generation, str(job.payload.get("generation_id", "")))
                    if generation:
                        generation.status = "failed"
                        generation.error_code = job.error_code
            else:
                job.status = "retry_scheduled"
                job.available_at = utc_now() + timedelta(seconds=2**job.attempt_count)
                job.progress = None

    def run_forever(self) -> None:
        logger.info("worker_started")
        while True:
            self.settings.worker_heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
            self.settings.worker_heartbeat_file.write_text(str(time.time()), encoding="ascii")
            job_id = self.claim()
            if job_id:
                self.process(job_id)
            else:
                time.sleep(self.settings.worker_poll_seconds)
