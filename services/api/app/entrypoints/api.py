import logging

import uvicorn

from app.config import get_settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    uvicorn.run("app.api:app", host="0.0.0.0", port=settings.api_port, proxy_headers=False)


if __name__ == "__main__":
    main()
