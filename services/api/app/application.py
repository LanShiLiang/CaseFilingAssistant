from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.dossier import DossierV1
from app.errors import DomainError
from app.models import Generation, Job, Matter, ValidationRun
from app.schemas import (
    GenerationResponse,
    GenerationStartResponse,
    ValidationIssueResponse,
    ValidationResponse,
)
from app.services import generation_to_response, get_matter
from app.storage import LocalBlobStore
from app.validation import validate_matter


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validation_input(matter: Matter) -> dict[str, Any]:
    dossier = DossierV1.from_matter(matter)
    active_documents = sorted(
        (
            {
                "id": item.id,
                "kind": item.kind,
                "sha256": item.sha256,
                "parse_revision": item.parse_revision,
            }
            for item in matter.documents
            if item.active
        ),
        key=lambda item: (item["kind"], item["id"]),
    )
    return {
        "matter_id": matter.id,
        "revision": matter.revision,
        "workflow_profile": matter.workflow_profile,
        "eligibility_confirmed": matter.eligibility_confirmed,
        "dossier": dossier.model_dump(mode="json"),
        "active_documents": active_documents,
    }


def run_validation(
    session: Session,
    matter_id: str,
    expected_revision: int,
    settings: Settings,
) -> ValidationResponse:
    matter = get_matter(session, matter_id, lock=True)
    if matter.revision != expected_revision:
        raise DomainError(
            "revision_conflict",
            "事项已被更新，请刷新后重试。",
            409,
            {"current_revision": matter.revision},
        )

    issues = validate_matter(matter)
    issue_payload = [issue.__dict__ for issue in issues]
    blocking_count = sum(issue.severity == "blocking" for issue in issues)
    input_hash = _stable_hash(_validation_input(matter))
    validation_run = session.scalar(
        select(ValidationRun).where(
            ValidationRun.matter_id == matter.id,
            ValidationRun.revision == matter.revision,
            ValidationRun.input_hash == input_hash,
            ValidationRun.rule_version == settings.rule_set_version,
        )
    )
    if validation_run is None:
        validation_run = ValidationRun(
            matter_id=matter.id,
            revision=matter.revision,
            input_hash=input_hash,
            rule_version=settings.rule_set_version,
            issues=issue_payload,
            passed=blocking_count == 0,
        )
        session.add(validation_run)
    matter.validated_revision = matter.revision if blocking_count == 0 else None
    session.commit()
    return ValidationResponse(
        matter_id=matter.id,
        revision=matter.revision,
        blocking_count=blocking_count,
        issues=[ValidationIssueResponse(**item) for item in issue_payload],
    )


def _generation_input(
    matter: Matter, validation_run: ValidationRun, settings: Settings
) -> dict[str, Any]:
    dossier = DossierV1.from_matter(matter)
    confirmed_facts = {
        key: value
        for key, value in dossier.facts.items()
        if dossier.confirmations.get(key) == "confirmed"
    }
    confirmed_sources = {
        key: [item.model_dump(mode="json") for item in dossier.sources.get(key, [])]
        for key in confirmed_facts
    }
    return {
        "schema_version": "generation_input_v1",
        "matter_id": matter.id,
        "revision": matter.revision,
        "workflow_profile": matter.workflow_profile,
        "facts": confirmed_facts,
        "sources": confirmed_sources,
        "validation_run_id": validation_run.id,
        "template_version": settings.template_version,
        "rule_set_version": settings.rule_set_version,
    }


def start_generation(
    session: Session,
    matter_id: str,
    expected_revision: int,
    settings: Settings,
) -> GenerationStartResponse:
    matter = get_matter(session, matter_id, lock=True)
    if matter.revision != expected_revision:
        raise DomainError("revision_conflict", "事项已被更新，请刷新后重试。", 409)
    if matter.validated_revision != matter.revision:
        raise DomainError("validation_required", "当前版本必须先通过检查。", 409)

    blocking = [issue for issue in validate_matter(matter) if issue.severity == "blocking"]
    if blocking:
        raise DomainError("validation_blocked", "当前事项仍有阻断问题。", 409)
    current_input_hash = _stable_hash(_validation_input(matter))
    validation_run = session.scalar(
        select(ValidationRun)
        .where(
            ValidationRun.matter_id == matter.id,
            ValidationRun.revision == matter.revision,
            ValidationRun.input_hash == current_input_hash,
            ValidationRun.rule_version == settings.rule_set_version,
            ValidationRun.passed.is_(True),
        )
        .order_by(ValidationRun.created_at.desc())
        .limit(1)
    )
    if validation_run is None:
        raise DomainError("validation_required", "当前版本缺少可审计的检查记录。", 409)

    existing = session.scalar(
        select(Generation).where(
            Generation.matter_id == matter.id, Generation.revision == matter.revision
        )
    )
    if existing:
        job = session.scalar(
            select(Job).where(
                Job.kind == "generate_package",
                Job.dedupe_key == f"{matter.id}:{matter.revision}",
            )
        )
        if not job:
            raise DomainError("generation_job_missing", "生成任务状态异常。", 500)
        return GenerationStartResponse(
            generation=generation_to_response(existing, matter.revision), job_id=job.id
        )

    input_snapshot = _generation_input(matter, validation_run, settings)
    input_hash = _stable_hash(input_snapshot)
    generation = Generation(
        matter_id=matter.id,
        revision=matter.revision,
        validation_run_id=validation_run.id,
        input_snapshot=input_snapshot,
        input_hash=input_hash,
    )
    session.add(generation)
    session.flush()
    job = Job(
        kind="generate_package",
        dedupe_key=f"{matter.id}:{matter.revision}",
        matter_id=matter.id,
        input_revision=matter.revision,
        payload={"generation_id": generation.id},
        max_attempts=settings.worker_max_attempts,
    )
    session.add(job)
    session.commit()
    return GenerationStartResponse(
        generation=generation_to_response(generation, matter.revision), job_id=job.id
    )


def confirm_generation(
    session: Session, generation_id: str, expected_revision: int
) -> GenerationResponse:
    generation = session.get(Generation, generation_id)
    if not generation:
        raise DomainError("generation_not_found", "生成记录不存在。", 404)
    matter = get_matter(session, generation.matter_id, lock=True)
    if (
        generation.status != "completed"
        or generation.revision != matter.revision
        or expected_revision != matter.revision
    ):
        raise DomainError("generation_superseded", "文书版本已失效，请重新生成。", 409)
    generation.final_confirmed = True
    session.commit()
    return generation_to_response(generation, matter.revision)


@dataclass(frozen=True)
class GenerationArtifact:
    path: Path
    media_type: str
    filename: str


def get_generation_artifact(
    session: Session,
    store: LocalBlobStore,
    generation_id: str,
    *,
    kind: str,
) -> GenerationArtifact:
    """集中执行 preview/download 的 revision 与最终确认门禁。"""

    generation = session.get(Generation, generation_id)
    if generation is None:
        raise DomainError("generation_not_found", "生成记录不存在。", 404)

    if kind == "preview":
        storage_key = generation.preview_key
        if storage_key is None:
            raise DomainError("preview_not_found", "预览尚未生成。", 404)
        matter = get_matter(session, generation.matter_id)
        if generation.status != "completed" or generation.revision != matter.revision:
            raise DomainError("generation_superseded", "预览版本已失效。", 409)
        media_type = "application/pdf"
        filename = "申请执行书_草稿预览.pdf"
    elif kind == "download":
        storage_key = generation.package_key
        if storage_key is None:
            raise DomainError("generation_not_found", "材料包尚未生成。", 404)
        matter = get_matter(session, generation.matter_id)
        if (
            generation.status != "completed"
            or generation.revision != matter.revision
            or not generation.final_confirmed
        ):
            raise DomainError("download_locked", "请先预览并确认当前版本。", 409)
        media_type = "application/zip"
        filename = "申请强制执行材料包_草稿.zip"
    else:
        raise ValueError("unknown_generation_artifact_kind")

    try:
        path = store.path_for(storage_key)
    except FileNotFoundError as exc:
        raise DomainError("artifact_unavailable", "生成文件暂不可用，请重新生成。", 503) from exc
    return GenerationArtifact(path=path, media_type=media_type, filename=filename)
