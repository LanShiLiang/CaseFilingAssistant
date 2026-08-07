from __future__ import annotations

import time

from app.health import worker_health


def test_worker_health_reports_stable_degraded_reasons(api_harness) -> None:
    settings = api_harness.settings

    assert worker_health(settings) == (False, "worker_heartbeat_missing")

    settings.worker_heartbeat_file.write_text(
        str(time.time() - settings.worker_heartbeat_max_age_seconds - 1),
        encoding="ascii",
    )
    assert worker_health(settings) == (False, "worker_heartbeat_stale")

    settings.worker_heartbeat_file.write_text(str(time.time()), encoding="ascii")
    assert worker_health(settings) == (True, None)

    response = api_harness.client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.json()["worker"] is True
    assert response.json()["worker_reason"] is None
