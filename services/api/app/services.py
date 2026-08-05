from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.errors import DomainError
from app.models import Document, Generation, IdempotencyRecord, Job, Matter
from app.schemas import GenerationResponse, JobResponse, MatterDocumentResponse, MatterResponse
from app.storage import LocalBlobStore

ALLOWED_FACTS = {
    "document_type",
    "case_number",
    "document_date",
    "rendering_court",
    "applicant_name",
    "applicant_id",
    "applicant_identity_address",
    "respondent_name",
    "respondent_id",
    "judgment_amount",
    "paid_amount",
    "outstanding_amount",
    "request_text",
    "filing_court",
    "service_address",
    "phone",
    "bank_account",
    "property_clues",
}

DOCUMENT_RULES: dict[str, tuple[set[str], set[str]]] = {
    "legal_basis": (
        {".pdf", ".docx", ".jpg", ".jpeg", ".png"},
        {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png",
        },
    ),
    "applicant_id_front": ({".jpg", ".jpeg", ".png"}, {"image/jpeg", "image/png"}),
    "applicant_id_back": ({".jpg", ".jpeg", ".png"}, {"image/jpeg", "image/png"}),
    "respondent_id_front": ({".jpg", ".jpeg", ".png"}, {"image/jpeg", "image/png"}),
    "respondent_id_back": ({".jpg", ".jpeg", ".png"}, {"image/jpeg", "image/png"}),
    "performance_evidence": (
        {".pdf", ".jpg", ".jpeg", ".png"},
        {"application/pdf", "image/jpeg", "image/png"},
    ),
}


def _request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def get_idempotent_response(
    session: Session, scope: str, key: str | None, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if not key:
        return None
    record = session.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.scope == scope, IdempotencyRecord.key == key
        )
    )
    if not record:
        return None
    if record.request_hash != _request_hash(payload):
        raise DomainError(
            "idempotency_key_reused",
            "同一幂等键已用于不同请求。",
            status_code=409,
        )
    return record.response


def save_idempotent_response(
    session: Session, scope: str, key: str | None, payload: dict[str, Any], response: dict[str, Any]
) -> None:
    if key:
        session.add(
            IdempotencyRecord(
                scope=scope,
                key=key,
                request_hash=_request_hash(payload),
                response=response,
            )
        )


def _matter_query(matter_id: str):
    return (
        select(Matter)
        .where(Matter.id == matter_id)
        .options(selectinload(Matter.documents), selectinload(Matter.generations))
    )


def get_matter(session: Session, matter_id: str, *, lock: bool = False) -> Matter:
    query = _matter_query(matter_id)
    if lock:
        query = query.with_for_update()
    matter = session.scalar(query)
    if not matter:
        raise DomainError("matter_not_found", "事项不存在。", status_code=404)
    return matter


def matter_to_response(matter: Matter) -> MatterResponse:
    legal_basis = next(
        (
            document
            for document in sorted(matter.documents, key=lambda item: item.created_at, reverse=True)
            if document.kind == "legal_basis"
        ),
        None,
    )
    case_number = matter.facts.get("case_number")
    if not legal_basis:
        title_state, display_title = "pending_upload", "待上传执行依据"
    elif legal_basis.parse_status in {"pending", "processing"}:
        title_state, display_title = "processing", "正在识别执行依据"
    elif case_number and matter.confirmations.get("case_number") == "confirmed":
        title_state, display_title = "case_number_ready", case_number
    else:
        title_state, display_title = "pending_confirmation", "案号待确认"
    latest_generation = max(matter.generations, key=lambda item: item.created_at, default=None)
    generated_revision = (
        latest_generation.revision
        if latest_generation and latest_generation.status == "completed"
        else None
    )
    return MatterResponse(
        id=matter.id,
        workflow_profile=matter.workflow_profile,
        eligibility_version=matter.eligibility_version,
        eligibility_confirmed=matter.eligibility_confirmed,
        revision=matter.revision,
        title_state=title_state,
        display_title=display_title,
        facts=dict(matter.facts),
        confirmations=dict(matter.confirmations),
        sources=dict(matter.sources),
        documents=[MatterDocumentResponse.model_validate(item) for item in matter.documents],
        validated_revision=matter.validated_revision,
        generated_revision=generated_revision,
        latest_generation_id=latest_generation.id if latest_generation else None,
        created_at=matter.created_at,
        updated_at=matter.updated_at,
    )


def job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        kind=job.kind,
        status=job.status,
        attempt=job.attempt_count,
        max_attempts=job.max_attempts,
        progress=job.progress,
        error_code=job.error_code,
        result=dict(job.result),
    )


def generation_to_response(generation: Generation, current_revision: int) -> GenerationResponse:
    status = generation.status
    if status == "completed" and generation.revision != current_revision:
        status = "superseded"
    preview_url = (
        f"/api/v1/generations/{generation.id}/preview"
        if generation.preview_key and status == "completed"
        else None
    )
    download_url = (
        f"/api/v1/generations/{generation.id}/download"
        if generation.package_key and status == "completed" and generation.final_confirmed
        else None
    )
    return GenerationResponse(
        id=generation.id,
        matter_id=generation.matter_id,
        revision=generation.revision,
        status=status,
        final_confirmed=generation.final_confirmed,
        preview_url=preview_url,
        download_url=download_url,
        sha256=generation.sha256,
        created_at=generation.created_at,
    )


def create_matter(
    session: Session,
    *,
    eligibility_confirmed: bool,
    eligibility_version: str,
    idempotency_key: str | None,
) -> MatterResponse:
    if not eligibility_confirmed:
        raise DomainError(
            "eligibility_not_confirmed", "必须确认 4 项适用条件后才能新建事项。", status_code=422
        )
    payload = {
        "eligibility_confirmed": eligibility_confirmed,
        "eligibility_version": eligibility_version,
    }
    previous = get_idempotent_response(session, "create_matter", idempotency_key, payload)
    if previous:
        return MatterResponse.model_validate(previous)
    matter = Matter(
        eligibility_confirmed=True,
        eligibility_version=eligibility_version,
        revision=1,
    )
    session.add(matter)
    session.flush()
    response = matter_to_response(matter)
    save_idempotent_response(
        session, "create_matter", idempotency_key, payload, response.model_dump(mode="json")
    )
    session.commit()
    return response


def _validate_magic(content: bytes, suffix: str) -> None:
    signatures = {
        ".pdf": content.startswith(b"%PDF"),
        ".png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": content.startswith(b"\xff\xd8\xff"),
        ".jpeg": content.startswith(b"\xff\xd8\xff"),
        ".docx": content.startswith(b"PK"),
    }
    if suffix not in signatures or not signatures[suffix]:
        raise DomainError("file_signature_mismatch", "文件内容与扩展名不一致。", status_code=415)


def upload_document(
    session: Session,
    store: LocalBlobStore,
    settings: Settings,
    matter_id: str,
    kind: str,
    expected_revision: int,
    upload: UploadFile,
) -> tuple[Document, Job, int]:
    if kind not in DOCUMENT_RULES:
        raise DomainError("unsupported_document_kind", "不支持的材料类型。", status_code=422)
    matter = get_matter(session, matter_id, lock=True)
    if matter.revision != expected_revision:
        raise DomainError(
            "revision_conflict",
            "事项已被更新，请刷新后重试。",
            status_code=409,
            details={"current_revision": matter.revision},
        )
    filename = Path(upload.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    allowed_suffixes, allowed_mimes = DOCUMENT_RULES[kind]
    mime_type = (upload.content_type or "application/octet-stream").lower()
    if suffix not in allowed_suffixes or mime_type not in allowed_mimes:
        raise DomainError("unsupported_media_type", "文件格式不符合该材料类型要求。", 415)
    content = upload.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise DomainError("file_too_large", "文件超过 20MB 限制。", 413)
    if not content:
        raise DomainError("empty_file", "文件不能为空。", 422)
    _validate_magic(content, suffix)
    blob = store.write_bytes("uploads", suffix, content)

    # 替换同类主材料时保留旧记录用于审计，但只让最新一份参与后续提取。
    matter.revision += 1
    matter.validated_revision = None
    document = Document(
        matter_id=matter.id,
        kind=kind,
        filename=filename,
        mime_type=mime_type,
        storage_key=blob.key,
        sha256=blob.sha256,
        size_bytes=blob.size_bytes,
        parse_status="pending",
    )
    session.add(document)
    session.flush()
    job = Job(
        kind="parse_document",
        dedupe_key=f"{document.id}:{matter.revision}",
        matter_id=matter.id,
        input_revision=matter.revision,
        payload={"document_id": document.id},
        max_attempts=settings.worker_max_attempts,
    )
    session.add(job)
    session.commit()
    return document, job, matter.revision


def save_confirmed_facts(
    session: Session,
    matter_id: str,
    expected_revision: int,
    fields: dict[str, str],
    confirm_fields: list[str],
) -> MatterResponse:
    matter = get_matter(session, matter_id, lock=True)
    if matter.revision != expected_revision:
        raise DomainError(
            "revision_conflict",
            "事项已被更新，请刷新后重试。",
            409,
            {"current_revision": matter.revision},
        )
    unknown = set(fields) - ALLOWED_FACTS
    if unknown:
        raise DomainError(
            "unknown_fact_field", "包含未定义字段。", 422, {"fields": sorted(unknown)}
        )
    if set(confirm_fields) - set(fields):
        raise DomainError("confirmation_without_value", "确认字段必须同时提交当前值。", 422)

    next_facts = dict(matter.facts)
    next_confirmations = dict(matter.confirmations)
    next_sources = dict(matter.sources)
    for field, value in fields.items():
        next_facts[field] = value
        next_confirmations[field] = "confirmed" if field in confirm_fields else "pending"
        if field not in next_sources or matter.facts.get(field) != value:
            next_sources[field] = [
                {
                    "document_id": "user",
                    "page": None,
                    "snippet": "用户填写或编辑后确认",
                    "extraction_method": "user",
                    "confidence": None,
                }
            ]

    # 尚未履行金额只由两个已提交字段确定性计算，并单独记录可审计的计算来源。
    try:
        judgment = Decimal(next_facts.get("judgment_amount", ""))
        paid = Decimal(next_facts.get("paid_amount", ""))
        if judgment >= 0 and paid >= 0:
            next_facts["outstanding_amount"] = f"{judgment - paid:.2f}"
            if "judgment_amount" in confirm_fields and "paid_amount" in confirm_fields:
                next_confirmations["outstanding_amount"] = "confirmed"
                next_sources["outstanding_amount"] = [
                    {
                        "document_id": "deterministic",
                        "page": None,
                        "snippet": "文书确定金额 - 已履行金额",
                        "extraction_method": "deterministic",
                        "confidence": None,
                    }
                ]
    except InvalidOperation:
        pass

    matter.facts = next_facts
    matter.confirmations = next_confirmations
    matter.sources = next_sources
    # 每次事实确认都产生新 revision，并立即废止旧校验/旧生成资格。
    matter.revision += 1
    matter.validated_revision = None
    session.commit()
    return matter_to_response(matter)
