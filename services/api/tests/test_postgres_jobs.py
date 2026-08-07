from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.config import Settings, get_settings
from app.database import Base, Database
from app.jobs import JobProcessor
from app.models import Job, Matter
from app.storage import LocalBlobStore

POSTGRES_URL = os.getenv("CFA_TEST_POSTGRES_URL")
API_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not POSTGRES_URL, reason="仅在 CI 的隔离 PostgreSQL 数据库中运行")
def test_postgres_workers_claim_distinct_jobs(tmp_path, monkeypatch) -> None:
    database_name = make_url(str(POSTGRES_URL)).database or ""
    if "test" not in database_name.lower():
        pytest.skip("CFA_TEST_POSTGRES_URL 必须指向名称含 test 的隔离数据库")
    settings = Settings(
        environment="test-postgres",
        database_url=str(POSTGRES_URL),
        storage_root=tmp_path / "storage",
        worker_heartbeat_file=tmp_path / "worker-heartbeat",
    )
    database = Database(settings)
    Base.metadata.drop_all(database.engine)
    with database.engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    monkeypatch.setenv("CFA_DATABASE_URL", str(POSTGRES_URL))
    get_settings.cache_clear()
    configuration = Config(str(API_ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(API_ROOT / "migrations"))
    command.upgrade(configuration, "head")
    try:
        with database.session_factory.begin() as session:
            first = Matter(
                eligibility_version="self_single_v1.0.0", eligibility_confirmed=True
            )
            second = Matter(
                eligibility_version="self_single_v1.0.0", eligibility_confirmed=True
            )
            session.add_all([first, second])
            session.flush()
            session.add_all(
                [
                    Job(
                        kind="parse_document",
                        dedupe_key="postgres-claim-first",
                        matter_id=first.id,
                        input_revision=first.revision,
                        payload={"document_id": "synthetic-first"},
                    ),
                    Job(
                        kind="parse_document",
                        dedupe_key="postgres-claim-second",
                        matter_id=second.id,
                        input_revision=second.revision,
                        payload={"document_id": "synthetic-second"},
                    ),
                ]
            )

        first_worker = JobProcessor(database, LocalBlobStore(settings.storage_root), settings)
        second_worker = JobProcessor(database, LocalBlobStore(settings.storage_root), settings)
        first_claim = first_worker.claim()
        second_claim = second_worker.claim()

        assert first_claim is not None and second_claim is not None
        assert first_claim.id != second_claim.id
        assert first_claim.lease_token != second_claim.lease_token
    finally:
        Base.metadata.drop_all(database.engine)
        with database.engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        database.engine.dispose()
