from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中管理 API、worker 和 migrate 共用配置，避免三个入口各自解释环境变量。"""

    model_config = SettingsConfigDict(
        env_prefix="CFA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Case Filing Assistant API"
    environment: str = "local"
    api_port: int = 8000
    database_url: str = "sqlite:///./.local/case_filing.db"
    storage_root: Path = Path("./.local/storage")
    max_upload_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 200
    worker_poll_seconds: float = 0.5
    worker_lease_seconds: int = 60
    worker_max_attempts: int = 3
    worker_heartbeat_file: Path = Path("./.local/worker-heartbeat")
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://127.0.0.1:3000"])
    template_version: str = "self_single_v1.0.0"
    rule_set_version: str = "national_baseline_v1.0.0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
