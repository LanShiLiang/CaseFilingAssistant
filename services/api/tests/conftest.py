from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import create_app
from app.config import Settings
from app.jobs import JobProcessor


@dataclass(frozen=True)
class ApiHarness:
    client: TestClient
    app: FastAPI
    settings: Settings

    def run_next_job(self) -> str:
        processor = JobProcessor(
            self.app.state.database,
            self.app.state.store,
            self.settings,
        )
        job_id = processor.claim()
        assert job_id is not None, "预期至少有一个待处理任务"
        processor.process(job_id)
        return job_id


@pytest.fixture
def api_harness(tmp_path: Path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        storage_root=tmp_path / "storage",
        worker_heartbeat_file=tmp_path / "worker-heartbeat",
        worker_poll_seconds=0.01,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield ApiHarness(client=client, app=app, settings=settings)
