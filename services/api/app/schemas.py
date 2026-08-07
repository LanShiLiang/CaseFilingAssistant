from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.dossier import AmountComputationV1, ScopeSignalV1

DocumentKind = Literal[
    "legal_basis",
    "applicant_id_front",
    "applicant_id_back",
    "respondent_id_front",
    "respondent_id_back",
    "performance_evidence",
]
ConfirmationState = Literal["pending", "confirmed", "invalidated"]
ExtractionMethod = Literal["text", "ocr", "user", "deterministic"]
DocumentParseStatus = Literal["pending", "processing", "completed", "failed"]
JobStatus = Literal["pending", "running", "retry_scheduled", "completed", "failed_terminal"]
JobKind = Literal["parse_document", "generate_package"]
GenerationStatus = Literal["pending", "processing", "completed", "superseded", "failed"]
MatterTitleState = Literal[
    "pending_upload", "processing", "pending_confirmation", "case_number_ready"
]
StepKey = Literal["parties_and_basis", "application", "review", "export"]
StepState = Literal["available", "locked", "complete", "blocked"]


class CreateMatterRequest(BaseModel):
    eligibility_confirmed: bool
    eligibility_version: Literal["self_single_v1.0.0"] = "self_single_v1.0.0"


class SaveFactsRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    fields: dict[str, str]
    confirm_fields: list[str]
    dismissed_scope_signal_ids: list[str] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: dict[str, str]) -> dict[str, str]:
        return {key: item.strip() for key, item in value.items()}


class RevisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class ExportAttestationRequest(RevisionRequest):
    attestation_version: Literal["export_attestation_v1"] = "export_attestation_v1"
    critical_fields_reviewed: Literal[True]
    manual_review_understood: Literal[True]
    local_requirements_reviewed: Literal[True]


class MatterDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: DocumentKind
    filename: str
    parse_status: DocumentParseStatus
    active: bool
    parse_revision: int
    created_at: datetime


class SourceReferenceResponse(BaseModel):
    document_id: str
    parse_revision: int | None = None
    page: int | None
    snippet: str
    extraction_method: ExtractionMethod
    confidence: float | None


class StepGateResponse(BaseModel):
    step: StepKey
    state: StepState
    allowed: bool
    reasons: list[str] = Field(default_factory=list)


class MatterResponse(BaseModel):
    id: str
    workflow_profile: Literal["self_single_v1"]
    eligibility_version: str
    eligibility_confirmed: bool
    revision: int
    dossier_schema_version: Literal["dossier_v2"]
    title_state: MatterTitleState
    display_title: str
    facts: dict[str, str]
    confirmations: dict[str, ConfirmationState]
    sources: dict[str, list[SourceReferenceResponse]]
    scope_signals: list[ScopeSignalV1]
    amount_computation: AmountComputationV1 | None
    documents: list[MatterDocumentResponse]
    step_gates: list[StepGateResponse]
    validated_revision: int | None
    generated_revision: int | None
    latest_generation_id: str | None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    document: MatterDocumentResponse
    job_id: str
    revision: int


class JobResponse(BaseModel):
    id: str
    kind: JobKind
    status: JobStatus
    attempt: int
    max_attempts: int
    progress: int | None
    error_code: str | None
    retryable: bool
    result: dict[str, Any]


class ValidationIssueResponse(BaseModel):
    code: str
    severity: Literal["blocking", "warning", "info"]
    field: str | None = None
    message: str


class ValidationResponse(BaseModel):
    matter_id: str
    revision: int
    blocking_count: int
    issues: list[ValidationIssueResponse]


class GenerationResponse(BaseModel):
    id: str
    matter_id: str
    revision: int
    status: GenerationStatus
    final_confirmed: bool
    final_confirmed_at: datetime | None
    export_attestation_version: str | None
    preview_url: str | None
    download_url: str | None
    sha256: str | None
    created_at: datetime


class GenerationStartResponse(BaseModel):
    generation: GenerationResponse
    job_id: str


class CapabilityResponse(BaseModel):
    database: bool
    storage: bool
    worker: bool
    worker_reason: Literal[
        "worker_heartbeat_missing", "worker_heartbeat_stale"
    ] | None = None
    text_pdf: bool = True
    docx: bool
    image_ocr: bool
    generation: bool
