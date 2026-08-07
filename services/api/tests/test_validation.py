from __future__ import annotations

from types import SimpleNamespace

from app.validation import validate_matter


def complete_matter(**overrides):
    facts = {
        "document_type": "民事判决书",
        "case_number": "（2026）京0105民初123号",
        "rendering_court": "北京市朝阳区人民法院",
        "applicant_name": "测试甲",
        "applicant_id": "TEST-ID-APPLICANT",
        "respondent_name": "测试乙",
        "judgment_amount": "10000.00",
        "paid_amount": "2500.00",
        "outstanding_amount": "7500.00",
        "request_text": "请求强制执行尚未履行的金钱给付义务。",
        "filing_court": "北京市朝阳区人民法院",
        "service_address": "测试地址（非真实）",
    }
    values = {
        "eligibility_confirmed": True,
        "dossier_schema_version": "dossier_v1",
        "documents": [
            SimpleNamespace(kind="legal_basis", active=True),
            SimpleNamespace(kind="applicant_id_front", active=True),
            SimpleNamespace(kind="applicant_id_back", active=True),
        ],
        "facts": facts,
        "confirmations": {key: "confirmed" for key in facts},
        "sources": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_complete_matter_has_no_blocking_issue() -> None:
    issues = validate_matter(complete_matter())

    assert not [issue for issue in issues if issue.severity == "blocking"]
    assert any(issue.code == "draft_only" for issue in issues)


def test_amount_mismatch_is_blocking() -> None:
    matter = complete_matter()
    matter.facts["outstanding_amount"] = "7000.00"

    issues = validate_matter(matter)

    assert any(issue.code == "amount_computation_mismatch" for issue in issues)
