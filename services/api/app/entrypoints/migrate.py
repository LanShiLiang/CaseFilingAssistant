from alembic import command
from alembic.config import Config


def main() -> None:
    configuration = Config("alembic.ini")
    command.upgrade(configuration, "head")


if __name__ == "__main__":
    main()
