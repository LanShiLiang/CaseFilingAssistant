from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DocumentKind = Literal[
    "legal_basis",
    "applicant_id_front",
    "applicant_id_back",
    "respondent_id_front",
    "respondent_id_back",
    "performance_evidence",
]


class CreateMatterRequest(BaseModel):
    eligibility_confirmed: bool
    eligibility_version: str = "self_single_v1.0.0"


class SaveFactsRequest(BaseModel):
    expected_revision: int = Field(ge=1)
    fields: dict[str, str]
    confirm_fields: list[str]

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: dict[str, str]) -> dict[str, str]:
        return {key: item.strip() for key, item in value.items()}


class RevisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class MatterDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    filename: str
    parse_status: str
    created_at: datetime


class MatterResponse(BaseModel):
    id: str
    workflow_profile: str
    eligibility_version: str
    eligibility_confirmed: bool
    revision: int
    title_state: str
    display_title: str
    facts: dict[str, str]
    confirmations: dict[str, str]
    sources: dict[str, list[dict[str, Any]]]
    documents: list[MatterDocumentResponse]
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
    kind: str
    status: str
    attempt: int
    max_attempts: int
    progress: int | None
    error_code: str | None
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
    status: str
    final_confirmed: bool
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
    text_pdf: bool = True
    docx: bool = True
    image_ocr: bool
    generation: bool = True
