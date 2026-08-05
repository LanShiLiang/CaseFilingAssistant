from __future__ import annotations

from pathlib import Path

from app.extraction import extract_pages, parse_legal_basis

from .helpers import legal_basis_docx, synthetic_identity_png

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_extracts_structured_facts_with_provenance(tmp_path: Path) -> None:
    path = tmp_path / "legal-basis.docx"
    path.write_bytes(legal_basis_docx())

    result = parse_legal_basis(path, DOCX_MIME, "document-test", 20)

    assert result.facts["case_number"] == "（2026）京0105民初123号"
    assert result.facts["document_type"] == "民事判决书"
    assert result.facts["rendering_court"] == "北京市朝阳区人民法院"
    assert result.facts["applicant_name"] == "测试甲"
    assert result.facts["respondent_name"] == "测试乙"
    assert result.facts["judgment_amount"] == "10000.00"
    assert result.sources["case_number"][0]["document_id"] == "document-test"
    assert result.sources["case_number"][0]["confidence"] == 0.92


def test_image_without_ocr_degrades_to_manual_input(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "front.png"
    path.write_bytes(synthetic_identity_png("FRONT"))
    monkeypatch.setattr("app.extraction.image_ocr_available", lambda: False)

    pages, warnings = extract_pages(path, "image/png", 20)

    assert pages[0].method == "ocr"
    assert pages[0].text == ""
    assert warnings == ["image_ocr_unavailable_manual_input_allowed"]
