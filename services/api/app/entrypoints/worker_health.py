import sys

from sqlalchemy import text

from app.config import get_settings
from app.database import Database
from app.health import worker_health


def main() -> None:
    settings = get_settings()
    try:
        with Database(settings).session_factory() as session:
            session.execute(text("SELECT 1"))
        healthy, reason = worker_health(settings)
        if not healthy:
            raise RuntimeError(reason)
    except Exception:  # noqa: BLE001 - 健康命令只通过退出码表达结果
        sys.exit(1)


if __name__ == "__main__":
    main()
