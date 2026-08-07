from __future__ import annotations

import hashlib
import json
import zipfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import Settings
from app.dossier import AmountComputationV1, DossierV2
from app.errors import DomainError
from app.models import Document, Generation, IdempotencyRecord, Job, Matter
from app.schemas import (
    GenerationResponse,
    JobResponse,
    MatterDocumentResponse,
    MatterResponse,
    StepGateResponse,
    UploadResponse,
)
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

REPLACEABLE_DOCUMENT_KINDS = {
    "legal_basis",
    "applicant_id_front",
    "applicant_id_back",
    "respondent_id_front",
    "respondent_id_back",
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
    dossier = DossierV2.from_matter(matter)
    legal_basis = next(
        (
            document
            for document in sorted(matter.documents, key=lambda item: item.created_at, reverse=True)
            if document.kind == "legal_basis" and document.active
        ),
        None,
    )
    case_number = dossier.facts.get("case_number")
    if not legal_basis:
        title_state, display_title = "pending_upload", "待上传执行依据"
    elif legal_basis.parse_status in {"pending", "processing"}:
        title_state, display_title = "processing", "正在识别执行依据"
    elif case_number and dossier.confirmations.get("case_number") == "confirmed":
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
        dossier_schema_version=dossier.schema_version,
        title_state=title_state,
        display_title=display_title,
        facts=dict(dossier.facts),
        confirmations=dict(dossier.confirmations),
        sources={
            key: [reference.model_dump(mode="json") for reference in references]
            for key, references in dossier.sources.items()
        },
        scope_signals=[signal.model_dump(mode="json") for signal in dossier.scope_signals],
        amount_computation=dossier.amount_computation,
        documents=[MatterDocumentResponse.model_validate(item) for item in matter.documents],
        step_gates=_step_gates(matter, dossier),
        validated_revision=matter.validated_revision,
        generated_revision=generated_revision,
        latest_generation_id=latest_generation.id if latest_generation else None,
        created_at=matter.created_at,
        updated_at=matter.updated_at,
    )


def _step_gates(matter: Matter, dossier: DossierV2) -> list[StepGateResponse]:
    """服务端统一派生步骤门禁；客户端只能把这些状态映射为界面。"""

    active_kinds = {item.kind for item in matter.documents if item.active}
    step_one_fields = {
        "document_type",
        "case_number",
        "rendering_court",
        "applicant_name",
        "applicant_id",
        "respondent_name",
    }
    step_two_fields = {
        "judgment_amount",
        "paid_amount",
        "outstanding_amount",
        "request_text",
        "filing_court",
        "service_address",
    }

    def confirmed(fields: set[str]) -> bool:
        return all(
            dossier.facts.get(field, "").strip()
            and dossier.confirmations.get(field) == "confirmed"
            for field in fields
        )

    missing_materials = [
        kind
        for kind in (
            "legal_basis",
            "applicant_id_front",
            "applicant_id_back",
            "respondent_id_front",
            "respondent_id_back",
        )
        if kind not in active_kinds
    ]
    step_one_complete = not missing_materials and confirmed(step_one_fields)
    step_two_complete = step_one_complete and confirmed(step_two_fields)
    review_complete = step_two_complete and matter.validated_revision == matter.revision
    export_allowed = review_complete and matter.generated_revision == matter.revision

    return [
        StepGateResponse(
            step="parties_and_basis",
            state="complete" if step_one_complete else "available",
            allowed=True,
            reasons=[],
        ),
        StepGateResponse(
            step="application",
            state=("complete" if step_two_complete else "available")
            if step_one_complete
            else "locked",
            allowed=step_one_complete,
            reasons=[] if step_one_complete else ["parties_and_basis_incomplete"],
        ),
        StepGateResponse(
            step="review",
            state="complete"
            if review_complete
            else ("available" if step_two_complete else "locked"),
            allowed=step_two_complete,
            reasons=[] if step_two_complete else ["application_incomplete"],
        ),
        StepGateResponse(
            step="export",
            state="available" if export_allowed else "locked",
            allowed=export_allowed,
            reasons=[] if export_allowed else ["current_generation_required"],
        ),
    ]


def job_is_retryable(job: Job) -> bool:
    return job.status == "failed_terminal" and not (job.error_code or "").startswith(
        ("unsupported_", "file_", "pdf_", "image_", "job_input_", "validation_")
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
        retryable=job_is_retryable(job),
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
        final_confirmed_at=generation.final_confirmed_at,
        export_attestation_version=(generation.export_attestation or {}).get(
            "attestation_version"
        ),
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
    try:
        session.commit()
    except IntegrityError:
        # 并发使用同一幂等键时，唯一约束决定唯一赢家；失败事务回滚后重读赢家结果。
        session.rollback()
        concurrent_response = get_idempotent_response(
            session, "create_matter", idempotency_key, payload
        )
        if concurrent_response:
            return MatterResponse.model_validate(concurrent_response)
        raise
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


def _validate_docx_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > 2_000:
                raise DomainError("docx_archive_limit_exceeded", "DOCX 内部文件数量过多。", 413)
            expanded = sum(item.file_size for item in members)
            if expanded > 100 * 1024 * 1024:
                raise DomainError("docx_archive_limit_exceeded", "DOCX 解压后内容过大。", 413)
            names = {item.filename for item in members}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise DomainError("invalid_docx", "DOCX 结构不完整。", 415)
            if any(
                name.startswith(("/", "\\")) or ".." in Path(name).parts for name in names
            ):
                raise DomainError("invalid_docx", "DOCX 包含不安全路径。", 415)
    except zipfile.BadZipFile as exc:
        raise DomainError("invalid_docx", "DOCX 文件损坏。", 415) from exc


def upload_document(
    session: Session,
    store: LocalBlobStore,
    settings: Settings,
    matter_id: str,
    kind: str,
    expected_revision: int,
    upload: UploadFile,
    idempotency_key: str | None,
) -> UploadResponse:
    if kind not in DOCUMENT_RULES:
        raise DomainError("unsupported_document_kind", "不支持的材料类型。", status_code=422)
    filename = Path(upload.filename or "upload").name
    suffix = Path(filename).suffix.lower()
    allowed_suffixes, allowed_mimes = DOCUMENT_RULES[kind]
    mime_type = (upload.content_type or "application/octet-stream").lower()
    if suffix not in allowed_suffixes or mime_type not in allowed_mimes:
        raise DomainError("unsupported_media_type", "文件格式不符合该材料类型要求。", 415)
    try:
        staged = store.stage_stream(suffix, upload.file, settings.max_upload_bytes)
    except ValueError as exc:
        if str(exc) == "file_too_large":
            raise DomainError("file_too_large", "文件超过 20MB 限制。", 413) from exc
        if str(exc) == "empty_file":
            raise DomainError("empty_file", "文件不能为空。", 422) from exc
        raise
    blob = None
    try:
        _validate_magic(store.read_prefix(staged.key), suffix)
        if suffix == ".docx":
            _validate_docx_archive(store.path_for(staged.key))
        request_payload = {
            "matter_id": matter_id,
            "kind": kind,
            "expected_revision": expected_revision,
            "filename": filename,
            "sha256": staged.sha256,
            "size_bytes": staged.size_bytes,
        }
        scope = f"upload_document:{matter_id}"
        previous = get_idempotent_response(
            session, scope, idempotency_key, request_payload
        )
        if previous:
            return UploadResponse.model_validate(previous)
        matter = get_matter(session, matter_id, lock=True)
        previous = get_idempotent_response(
            session, scope, idempotency_key, request_payload
        )
        if previous:
            return UploadResponse.model_validate(previous)
        if matter.revision != expected_revision:
            raise DomainError(
                "revision_conflict",
                "事项已被更新，请刷新后重试。",
                status_code=409,
                details={"current_revision": matter.revision},
            )
        # 替换同类主材料时保留旧记录用于审计，但只让最新一份参与后续提取。
        replaced_document_ids: set[str] = set()
        if kind in REPLACEABLE_DOCUMENT_KINDS:
            for existing in matter.documents:
                if existing.kind == kind and existing.active:
                    existing.active = False
                    replaced_document_ids.add(existing.id)
        if replaced_document_ids:
            dossier = DossierV2.from_matter(matter)
            payload = dossier.model_dump(mode="json")
            for field, references in payload["sources"].items():
                if any(item["document_id"] in replaced_document_ids for item in references):
                    payload["confirmations"][field] = "invalidated"
            payload["scope_signals"] = [
                signal
                for signal in payload["scope_signals"]
                if signal["document_id"] not in replaced_document_ids
            ]
            if any(
                payload["confirmations"].get(field) == "invalidated"
                for field in ("judgment_amount", "paid_amount")
            ) and payload["amount_computation"]:
                payload["amount_computation"]["confirmation_status"] = "invalidated"
                payload["confirmations"]["outstanding_amount"] = "invalidated"
            DossierV2.model_validate(payload).apply_to(matter)
        matter.revision += 1
        matter.validated_revision = None
        blob = store.publish(staged, "uploads")
        document = Document(
            matter_id=matter.id,
            kind=kind,
            filename=filename,
            mime_type=mime_type,
            storage_key=blob.key,
            sha256=blob.sha256,
            size_bytes=blob.size_bytes,
            parse_status="pending",
            parse_revision=matter.revision,
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
        session.flush()
        response = UploadResponse(
            document=document, job_id=job.id, revision=matter.revision
        )
        save_idempotent_response(
            session,
            scope,
            idempotency_key,
            request_payload,
            response.model_dump(mode="json"),
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            if blob is not None:
                store.delete(blob.key)
                blob = None
            concurrent_response = get_idempotent_response(
                session, scope, idempotency_key, request_payload
            )
            if concurrent_response:
                return UploadResponse.model_validate(concurrent_response)
            raise
        return response
    except Exception:
        session.rollback()
        if blob is not None:
            store.delete(blob.key)
        raise
    finally:
        # publish 成功后 staging key 已被移动；失败时清理仍保持幂等。
        store.delete(staged.key)


def save_confirmed_facts(
    session: Session,
    matter_id: str,
    expected_revision: int,
    fields: dict[str, str],
    confirm_fields: list[str],
    dismissed_scope_signal_ids: list[str] | None = None,
    idempotency_key: str | None = None,
) -> MatterResponse:
    request_payload = {
        "matter_id": matter_id,
        "expected_revision": expected_revision,
        "fields": fields,
        "confirm_fields": sorted(confirm_fields),
        "dismissed_scope_signal_ids": sorted(dismissed_scope_signal_ids or []),
    }
    scope = f"save_facts:{matter_id}"
    previous = get_idempotent_response(session, scope, idempotency_key, request_payload)
    if previous:
        return MatterResponse.model_validate(previous)
    matter = get_matter(session, matter_id, lock=True)
    previous = get_idempotent_response(session, scope, idempotency_key, request_payload)
    if previous:
        return MatterResponse.model_validate(previous)
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

    dossier = DossierV2.from_matter(matter)
    dossier_payload = dossier.model_dump(mode="json")
    next_facts = dossier_payload["facts"]
    next_confirmations = dossier_payload["confirmations"]
    next_sources = dossier_payload["sources"]
    next_scope_signals = dossier_payload["scope_signals"]
    dismissed = set(dismissed_scope_signal_ids or [])
    known_signal_ids = {signal["id"] for signal in next_scope_signals}
    if dismissed - known_signal_ids:
        raise DomainError("unknown_scope_signal", "包含不存在的复杂性信号。", 422)
    for signal in next_scope_signals:
        if signal["id"] in dismissed:
            signal["status"] = "dismissed_as_parse_error"
    for field, value in fields.items():
        next_facts[field] = value
        next_confirmations[field] = "confirmed" if field in confirm_fields else "pending"
        if (
            field not in next_sources
            or dossier.facts.get(field) != value
            or dossier.confirmations.get(field) == "invalidated"
        ):
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
    amount_computation = None
    try:
        judgment = Decimal(next_facts.get("judgment_amount", ""))
        paid = Decimal(next_facts.get("paid_amount", ""))
        if judgment >= 0 and paid >= 0:
            next_facts["outstanding_amount"] = f"{judgment - paid:.2f}"
            amount_confirmed = all(
                next_confirmations.get(field) == "confirmed"
                for field in ("judgment_amount", "paid_amount")
            )
            next_confirmations["outstanding_amount"] = (
                "confirmed" if amount_confirmed else "pending"
            )
            if amount_confirmed:
                next_confirmations["outstanding_amount"] = "confirmed"
                next_sources["outstanding_amount"] = [
                    {
                        "document_id": "deterministic",
                        "parse_revision": None,
                        "page": None,
                        "snippet": "文书确定金额 - 已履行金额",
                        "extraction_method": "deterministic",
                        "confidence": None,
                    }
                ]
            amount_computation = AmountComputationV1(
                input_revision=matter.revision + 1,
                judgment_amount=f"{judgment:.2f}",
                paid_amount=f"{paid:.2f}",
                result=f"{judgment - paid:.2f}",
                confirmation_status="confirmed" if amount_confirmed else "pending",
            )
    except InvalidOperation:
        amount_computation = None

    DossierV2(
        facts=next_facts,
        confirmations=next_confirmations,
        sources=next_sources,
        scope_signals=next_scope_signals,
        amount_computation=amount_computation,
    ).apply_to(matter)
    # 每次事实确认都产生新 revision，并立即废止旧校验/旧生成资格。
    matter.revision += 1
    matter.validated_revision = None
    response = matter_to_response(matter)
    save_idempotent_response(
        session,
        scope,
        idempotency_key,
        request_payload,
        response.model_dump(mode="json"),
    )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        concurrent_response = get_idempotent_response(
            session, scope, idempotency_key, request_payload
        )
        if concurrent_response:
            return MatterResponse.model_validate(concurrent_response)
        raise
    return response
