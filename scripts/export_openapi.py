from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository_root / "services" / "api"))
    from app.api import create_app  # noqa: PLC0415 - 需要先设置服务端源码搜索路径
    from app.config import Settings  # noqa: PLC0415

    output = Path(sys.argv[1]).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(Settings(environment="schema"))
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
