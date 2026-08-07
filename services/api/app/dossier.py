from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models import Matter


class SourceRefV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    parse_revision: int | None = Field(default=None, ge=1)
    page: int | None = None
    snippet: str
    extraction_method: Literal["text", "ocr", "user", "deterministic"]
    confidence: float | None = Field(default=None, ge=0, le=1)


ScopeSignalCode = Literal[
    "unsupported_multiple_applicants",
    "unsupported_multiple_respondents",
    "unsupported_representative",
    "unsupported_organization_party",
    "unsupported_multiple_obligations",
    "unsupported_complex_obligation",
]


class ScopeSignalV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    code: ScopeSignalCode
    document_id: str
    page: int | None = None
    snippet: str
    status: Literal["open", "dismissed_as_parse_error"] = "open"


class AmountComputationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["amount_computation_v1"] = "amount_computation_v1"
    formula_version: Literal["outstanding_amount_v1"] = "outstanding_amount_v1"
    input_revision: int = Field(ge=1)
    judgment_amount: str
    paid_amount: str
    result: str
    confirmation_status: Literal["pending", "confirmed", "invalidated"]


class DossierV2(BaseModel):
    """Matter JSON 列的单一类型边界；业务代码不得各自解释裸字典。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dossier_v2"] = "dossier_v2"
    facts: dict[str, str] = Field(default_factory=dict)
    confirmations: dict[str, Literal["pending", "confirmed", "invalidated"]] = Field(
        default_factory=dict
    )
    sources: dict[str, list[SourceRefV2]] = Field(default_factory=dict)
    scope_signals: list[ScopeSignalV1] = Field(default_factory=list)
    amount_computation: AmountComputationV1 | None = None

    @classmethod
    def from_matter(cls, matter: Matter) -> DossierV2:
        schema_version = getattr(matter, "dossier_schema_version", "dossier_v2")
        if schema_version == "dossier_v1":
            schema_version = "dossier_v2"
        return cls.model_validate(
            {
                "schema_version": schema_version,
                "facts": matter.facts,
                "confirmations": matter.confirmations,
                "sources": matter.sources,
                "scope_signals": getattr(matter, "scope_signals", []),
                "amount_computation": getattr(matter, "amount_computation", None) or None,
            }
        )

    def apply_to(self, matter: Matter) -> None:
        payload = self.model_dump(mode="json")
        matter.dossier_schema_version = payload["schema_version"]
        matter.facts = payload["facts"]
        matter.confirmations = payload["confirmations"]
        matter.sources = payload["sources"]
        matter.scope_signals = payload["scope_signals"]
        matter.amount_computation = payload["amount_computation"] or {}
