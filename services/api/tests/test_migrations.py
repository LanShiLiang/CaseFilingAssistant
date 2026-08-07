from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import get_settings

API_ROOT = Path(__file__).resolve().parents[1]


def _configuration(database_url: str, monkeypatch) -> Config:
    monkeypatch.setenv("CFA_DATABASE_URL", database_url)
    get_settings.cache_clear()
    configuration = Config(str(API_ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(API_ROOT / "migrations"))
    return configuration


def test_empty_database_upgrades_to_architecture_hardening(tmp_path: Path, monkeypatch) -> None:
    url = f"sqlite:///{(tmp_path / 'empty.db').as_posix()}"
    configuration = _configuration(url, monkeypatch)
    command.upgrade(configuration, "head")

    inspector = inspect(create_engine(url))
    assert "validation_runs" in inspector.get_table_names()
    assert "dossier_schema_version" in {
        item["name"] for item in inspector.get_columns("matters")
    }
    assert {"active", "parse_revision"}.issubset(
        {item["name"] for item in inspector.get_columns("documents")}
    )
    assert {"lease_owner", "heartbeat_at"}.issubset(
        {item["name"] for item in inspector.get_columns("jobs")}
    )
    assert {"validation_run_id", "input_snapshot", "input_hash"}.issubset(
        {item["name"] for item in inspector.get_columns("generations")}
    )

    # downgrade 不是生产恢复手段，但必须保证本 revision 的约束和列能一致撤销。
    command.downgrade(configuration, "0001_initial")
    downgraded = inspect(create_engine(url))
    assert "validation_runs" not in downgraded.get_table_names()
    assert "validation_run_id" not in {
        item["name"] for item in downgraded.get_columns("generations")
    }
    assert "dossier_schema_version" not in {
        item["name"] for item in downgraded.get_columns("matters")
    }


def test_v010_database_upgrades_without_rewriting_initial_revision(
    tmp_path: Path, monkeypatch
) -> None:
    url = f"sqlite:///{(tmp_path / 'v010.db').as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        # 只构造 0002 所需的 v0.1.0 表边界，验证已发布 revision 的前向升级路径。
        connection.execute(text("CREATE TABLE matters (id VARCHAR(36) PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE documents ("
                "id VARCHAR(36) PRIMARY KEY, matter_id VARCHAR(36), kind VARCHAR(40))"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE jobs (id VARCHAR(36) PRIMARY KEY, "
                "lease_token VARCHAR(64), leased_until DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE generations (id VARCHAR(36) PRIMARY KEY, "
                "matter_id VARCHAR(36))"
            )
        )
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('0001_initial')")
        )

    command.upgrade(_configuration(url, monkeypatch), "head")

    inspector = inspect(engine)
    assert "validation_runs" in inspector.get_table_names()
    assert "input_snapshot" in {
        item["name"] for item in inspector.get_columns("generations")
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0002_architecture_hardening"
        )
