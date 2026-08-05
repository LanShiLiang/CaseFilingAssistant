from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import Settings


class Base(DeclarativeBase):
    pass


class Database:
    """封装引擎与会话工厂，便于生产 PostgreSQL 和测试 SQLite 共享业务代码。"""

    def __init__(self, settings: Settings):
        connect_args = (
            {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        )
        engine_kwargs: dict[str, object] = {
            "pool_pre_ping": True,
            "connect_args": connect_args,
        }
        if not settings.database_url.startswith("sqlite"):
            engine_kwargs.update({"pool_size": 10, "max_overflow": 10, "pool_timeout": 10})
        self.engine: Engine = create_engine(settings.database_url, **engine_kwargs)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    def session(self) -> Generator[Session, None, None]:
        with self.session_factory() as session:
            yield session
