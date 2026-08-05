import logging

from app.config import get_settings
from app.database import Database
from app.jobs import JobProcessor
from app.storage import LocalBlobStore


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = get_settings()
    processor = JobProcessor(Database(settings), LocalBlobStore(settings.storage_root), settings)
    processor.run_forever()


if __name__ == "__main__":
    main()
