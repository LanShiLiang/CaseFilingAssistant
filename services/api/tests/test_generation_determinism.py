from __future__ import annotations

import io
from datetime import UTC, datetime

from pypdf import PdfReader

from app.generation import GenerationContext, generate_package


def test_package_is_deterministic_and_user_text_is_not_pdf_markup() -> None:
    context = GenerationContext(
        schema_version="generation_input_v1",
        matter_id="00000000-0000-0000-0000-000000000001",
        revision=7,
        workflow_profile="self_single_v1",
        facts={
            "document_type": "民事判决书",
            "case_number": "（2026）示例民初1号",
            "rendering_court": "北京市示例区人民法院",
            "applicant_name": "<link href='file:///C:/Windows/win.ini'>测试甲</link>",
            "applicant_id": "TEST-ID-APPLICANT",
            "respondent_name": "测试乙",
            "respondent_id": "TEST-ID-RESPONDENT",
            "judgment_amount": "10000.00",
            "paid_amount": "2500.00",
            "outstanding_amount": "7500.00",
            "request_text": "请求执行尚未履行金额。",
            "filing_court": "北京市示例区人民法院",
            "service_address": "测试地址（非真实）",
        },
        sources={},
        amount_computation={
            "schema_version": "amount_computation_v1",
            "input_revision": 7,
            "judgment_amount": "10000.00",
            "paid_amount": "2500.00",
            "result": "7500.00",
            "confirmation_status": "confirmed",
        },
        validation_run_id="00000000-0000-0000-0000-000000000002",
        template_version="self_single_v1.0.0",
        rule_set_version="national_baseline_v1.0.0",
        generated_at=datetime(2026, 8, 7, 8, 0, tzinfo=UTC),
    )

    first = generate_package(context)
    second = generate_package(context)

    assert first.package_bytes == second.package_bytes
    assert first.preview_pdf == second.preview_pdf
    assert first.package_sha256 == second.package_sha256
    assert len(PdfReader(io.BytesIO(first.preview_pdf)).pages) >= 1
