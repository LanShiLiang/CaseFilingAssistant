from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.dossier import DossierV1


def test_dossier_is_the_only_json_boundary() -> None:
    matter = SimpleNamespace(
        dossier_schema_version="dossier_v1",
        facts={"case_number": "（2026）示例民初001号"},
        confirmations={"case_number": "confirmed"},
        sources={
            "case_number": [
                {
                    "document_id": "test-document",
                    "page": 1,
                    "snippet": "完全虚构的测试案号",
                    "extraction_method": "text",
                    "confidence": 0.99,
                }
            ]
        },
    )

    dossier = DossierV1.from_matter(matter)
    assert dossier.sources["case_number"][0].page == 1

    dossier.apply_to(matter)
    assert matter.dossier_schema_version == "dossier_v1"
    assert matter.sources["case_number"][0]["extraction_method"] == "text"


def test_dossier_rejects_unknown_confirmation_state() -> None:
    with pytest.raises(ValidationError):
        DossierV1(
            facts={"case_number": "TEST"},
            confirmations={"case_number": "silently_accepted"},
        )
