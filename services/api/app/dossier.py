from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models import Matter


class SourceRefV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    page: int | None = None
    snippet: str
    extraction_method: Literal["text", "ocr", "user", "deterministic"]
    confidence: float | None = Field(default=None, ge=0, le=1)


class DossierV1(BaseModel):
    """Matter JSON 列的单一类型边界；业务代码不得各自解释裸字典。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["dossier_v1"] = "dossier_v1"
    facts: dict[str, str] = Field(default_factory=dict)
    confirmations: dict[str, Literal["pending", "confirmed", "invalidated"]] = Field(
        default_factory=dict
    )
    sources: dict[str, list[SourceRefV1]] = Field(default_factory=dict)

    @classmethod
    def from_matter(cls, matter: Matter) -> DossierV1:
        return cls.model_validate(
            {
                "schema_version": matter.dossier_schema_version,
                "facts": matter.facts,
                "confirmations": matter.confirmations,
                "sources": matter.sources,
            }
        )

    def apply_to(self, matter: Matter) -> None:
        payload = self.model_dump(mode="json")
        matter.dossier_schema_version = payload["schema_version"]
        matter.facts = payload["facts"]
        matter.confirmations = payload["confirmations"]
        matter.sources = payload["sources"]
