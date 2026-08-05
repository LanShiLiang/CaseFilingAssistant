from __future__ import annotations

import io
import json
import zipfile

from docx import Document as WordDocument
from pypdf import PdfReader

from .conftest import ApiHarness
from .helpers import legal_basis_docx, synthetic_identity_png

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def create_matter(harness: ApiHarness) -> dict:
    response = harness.client.post(
        "/api/v1/matters",
        headers={"Idempotency-Key": "test-create-matter"},
        json={
            "eligibility_confirmed": True,
            "eligibility_version": "self_single_v1.0.0",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(
    harness: ApiHarness,
    matter_id: str,
    revision: int,
    kind: str,
    filename: str,
    mime_type: str,
    content: bytes,
) -> dict:
    response = harness.client.post(
        f"/api/v1/matters/{matter_id}/documents",
        data={"kind": kind, "expected_revision": str(revision)},
        files={"file": (filename, content, mime_type)},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_full_draft_generation_flow(api_harness: ApiHarness) -> None:
    matter = create_matter(api_harness)
    matter_id = matter["id"]
    assert matter["display_title"] == "待上传执行依据"

    legal = upload(
        api_harness,
        matter_id,
        matter["revision"],
        "legal_basis",
        "虚构判决书.docx",
        DOCX_MIME,
        legal_basis_docx(),
    )
    api_harness.run_next_job()
    matter = api_harness.client.get(f"/api/v1/matters/{matter_id}").json()
    assert matter["revision"] == legal["revision"]
    assert matter["title_state"] == "pending_confirmation"
    assert matter["facts"]["judgment_amount"] == "10000.00"

    front = upload(
        api_harness,
        matter_id,
        matter["revision"],
        "applicant_id_front",
        "申请人身份证人像面_测试.png",
        "image/png",
        synthetic_identity_png("FRONT"),
    )
    api_harness.run_next_job()
    back = upload(
        api_harness,
        matter_id,
        front["revision"],
        "applicant_id_back",
        "申请人身份证国徽面_测试.png",
        "image/png",
        synthetic_identity_png("BACK"),
    )
    api_harness.run_next_job()

    step_one = {
        "document_type": "民事判决书",
        "case_number": "（2026）京0105民初123号",
        "document_date": "2026-08-06",
        "rendering_court": "北京市朝阳区人民法院",
        "applicant_name": "测试甲",
        "applicant_id": "TEST-ID-APPLICANT",
        "respondent_name": "测试乙",
        "respondent_id": "TEST-ID-RESPONDENT",
    }
    response = api_harness.client.put(
        f"/api/v1/matters/{matter_id}/facts",
        json={
            "expected_revision": back["revision"],
            "fields": step_one,
            "confirm_fields": list(step_one),
        },
    )
    assert response.status_code == 200, response.text
    matter = response.json()
    assert matter["display_title"] == "（2026）京0105民初123号"

    step_two = {
        "judgment_amount": "10000.00",
        "paid_amount": "2500.00",
        "request_text": "请求强制执行人民币7500.00元。",
        "filing_court": "北京市朝阳区人民法院",
        "service_address": "测试地址（非真实）",
        "phone": "TEST-PHONE",
        "bank_account": "TEST-BANK-ACCOUNT",
        "property_clues": "暂无财产线索。",
    }
    response = api_harness.client.put(
        f"/api/v1/matters/{matter_id}/facts",
        json={
            "expected_revision": matter["revision"],
            "fields": step_two,
            "confirm_fields": list(step_two),
        },
    )
    assert response.status_code == 200, response.text
    matter = response.json()
    assert matter["facts"]["outstanding_amount"] == "7500.00"
    assert matter["confirmations"]["outstanding_amount"] == "confirmed"

    validation = api_harness.client.post(
        f"/api/v1/matters/{matter_id}/validate",
        json={"expected_revision": matter["revision"]},
    )
    assert validation.status_code == 200, validation.text
    assert validation.json()["blocking_count"] == 0

    started = api_harness.client.post(
        f"/api/v1/matters/{matter_id}/generations",
        json={"expected_revision": matter["revision"]},
    )
    assert started.status_code == 202, started.text
    generation_id = started.json()["generation"]["id"]
    api_harness.run_next_job()

    generation = api_harness.client.get(f"/api/v1/generations/{generation_id}")
    assert generation.status_code == 200
    assert generation.json()["status"] == "completed"
    assert generation.json()["download_url"] is None

    preview = api_harness.client.get(f"/api/v1/generations/{generation_id}/preview")
    assert preview.status_code == 200
    assert len(PdfReader(io.BytesIO(preview.content)).pages) >= 1

    locked = api_harness.client.get(f"/api/v1/generations/{generation_id}/download")
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "download_locked"

    confirmed = api_harness.client.post(
        f"/api/v1/generations/{generation_id}/confirm",
        json={"expected_revision": matter["revision"]},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["download_url"]

    package = api_harness.client.get(f"/api/v1/generations/{generation_id}/download")
    assert package.status_code == 200
    with zipfile.ZipFile(io.BytesIO(package.content)) as archive:
        names = set(archive.namelist())
        assert {
            "申请执行书_草稿.docx",
            "材料清单_草稿.docx",
            "字段来源核对表_内部审阅.docx",
            "申请执行书_预览.pdf",
            "manifest.json",
        } <= names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["draft_only"] is True
        assert manifest["revision"] == matter["revision"]
        application = WordDocument(io.BytesIO(archive.read("申请执行书_草稿.docx")))
        assert "申请执行书（草稿）" in "\n".join(p.text for p in application.paragraphs)


def test_revision_conflict_and_upload_signature_are_structured(api_harness: ApiHarness) -> None:
    matter = create_matter(api_harness)
    matter_id = matter["id"]
    bad_upload = api_harness.client.post(
        f"/api/v1/matters/{matter_id}/documents",
        data={"kind": "legal_basis", "expected_revision": str(matter["revision"])},
        files={"file": ("伪装.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert bad_upload.status_code == 415
    assert bad_upload.json()["error"]["code"] == "file_signature_mismatch"

    conflict = api_harness.client.put(
        f"/api/v1/matters/{matter_id}/facts",
        json={
            "expected_revision": matter["revision"] + 1,
            "fields": {"applicant_name": "测试甲"},
            "confirm_fields": ["applicant_name"],
        },
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "revision_conflict"
    assert conflict.headers["cache-control"] == "no-store, private"
    assert conflict.headers["x-request-id"]
