from __future__ import annotations

from app.extraction import ExtractionResult
from app.jobs import JobProcessor
from app.models import Document, Job, Matter

from .conftest import ApiHarness
from .helpers import legal_basis_docx


def _create_matter(harness: ApiHarness) -> dict:
    response = harness.client.post(
        "/api/v1/matters",
        headers={"Idempotency-Key": "worker-safety-matter"},
        json={
            "eligibility_confirmed": True,
            "eligibility_version": "self_single_v1.0.0",
        },
    )
    assert response.status_code == 201
    return response.json()


def _upload_basis(harness: ApiHarness, matter: dict) -> dict:
    response = harness.client.post(
        f"/api/v1/matters/{matter['id']}/documents",
        data={"kind": "legal_basis", "expected_revision": str(matter["revision"])},
        files={
            "file": (
                "synthetic-basis.docx",
                legal_basis_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    return response.json()


def test_parse_publish_uses_current_revision_and_never_overwrites_confirmation(
    api_harness: ApiHarness, monkeypatch
) -> None:
    matter_payload = _create_matter(api_harness)
    upload = _upload_basis(api_harness, matter_payload)
    processor = JobProcessor(
        api_harness.app.state.database,
        api_harness.app.state.store,
        api_harness.settings,
    )
    claimed = processor.claim()
    assert claimed is not None

    def slow_result(*_args, **_kwargs) -> ExtractionResult:
        # 用独立事务稳定模拟“worker 解析期间，用户已经保存确认字段”。
        with api_harness.app.state.database.session_factory.begin() as session:
            matter = session.get(Matter, matter_payload["id"])
            assert matter is not None
            matter.facts = {**matter.facts, "case_number": "USER-CONFIRMED-NUMBER"}
            matter.confirmations = {**matter.confirmations, "case_number": "confirmed"}
            matter.revision += 1
        return ExtractionResult(
            text="synthetic extracted text",
            facts={"case_number": "STALE-OCR-NUMBER"},
            sources={
                "case_number": [
                    {
                        "document_id": upload["document"]["id"],
                        "page": 1,
                        "snippet": "STALE-OCR-NUMBER",
                        "extraction_method": "text",
                        "confidence": 0.9,
                    }
                ]
            },
            warnings=[],
        )

    monkeypatch.setattr("app.jobs.parse_legal_basis", slow_result)
    processor.process(claimed)

    with api_harness.app.state.database.session_factory() as session:
        matter = session.get(Matter, matter_payload["id"])
        job = session.get(Job, upload["job_id"])
        assert matter is not None and job is not None
        assert matter.facts["case_number"] == "USER-CONFIRMED-NUMBER"
        assert matter.confirmations["case_number"] == "confirmed"
        assert job.status == "completed"
        assert job.result["superseded"] is True


def test_stolen_lease_cannot_publish_or_change_document_state(api_harness: ApiHarness) -> None:
    matter = _create_matter(api_harness)
    upload = _upload_basis(api_harness, matter)
    processor = JobProcessor(
        api_harness.app.state.database,
        api_harness.app.state.store,
        api_harness.settings,
    )
    claimed = processor.claim()
    assert claimed is not None
    assert processor.heartbeat(claimed) is True

    with api_harness.app.state.database.session_factory.begin() as session:
        job = session.get(Job, claimed.id)
        assert job is not None
        job.lease_token = "replacement-worker-token"

    assert processor.heartbeat(claimed) is False
    processor.process(claimed)

    with api_harness.app.state.database.session_factory() as session:
        job = session.get(Job, upload["job_id"])
        document = session.get(Document, upload["document"]["id"])
        assert job is not None and document is not None
        assert job.status == "running"
        assert job.lease_token == "replacement-worker-token"
        assert document.parse_status == "pending"
