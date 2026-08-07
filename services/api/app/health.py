from __future__ import annotations

import time

from app.config import Settings


def worker_health(settings: Settings) -> tuple[bool, str | None]:
    """只暴露脱敏能力状态，不把心跳路径、主机信息或异常正文返回给客户端。"""

    try:
        heartbeat = float(settings.worker_heartbeat_file.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return False, "worker_heartbeat_missing"

    if time.time() - heartbeat > settings.worker_heartbeat_max_age_seconds:
        return False, "worker_heartbeat_stale"
    return True, None
