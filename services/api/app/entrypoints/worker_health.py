import sys
import time

from sqlalchemy import text

from app.config import get_settings
from app.database import Database


def main() -> None:
    settings = get_settings()
    try:
        age = time.time() - float(settings.worker_heartbeat_file.read_text(encoding="ascii"))
        with Database(settings).session_factory() as session:
            session.execute(text("SELECT 1"))
        if age > max(10, settings.worker_poll_seconds * 10):
            raise RuntimeError("worker_heartbeat_stale")
    except Exception:  # noqa: BLE001 - 健康命令只通过退出码表达结果
        sys.exit(1)


if __name__ == "__main__":
    main()
