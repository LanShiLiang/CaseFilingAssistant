from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Matter(Base):
    __tablename__ = "matters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workflow_profile: Mapped[str] = mapped_column(String(40), default="self_single_v1")
    eligibility_version: Mapped[str] = mapped_column(String(40))
    eligibility_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    dossier_schema_version: Mapped[str] = mapped_column(String(40), default="dossier_v2")
    facts: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    confirmations: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    sources: Mapped[dict[str, list[dict[str, Any]]]] = mapped_column(JSON, default=dict)
    scope_signals: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    amount_computation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validated_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generated_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    documents: Mapped[list[Document]] = relationship(
        back_populates="matter", cascade="all, delete-orphan", lazy="selectin"
    )
    generations: Mapped[list[Generation]] = relationship(
        back_populates="matter", cascade="all, delete-orphan", lazy="selectin"
    )
    validation_runs: Mapped[list[ValidationRun]] = relationship(
        back_populates="matter", cascade="all, delete-orphan", lazy="selectin"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    matter_id: Mapped[str] = mapped_column(ForeignKey("matters.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(30), default="pending")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    parse_revision: Mapped[int] = mapped_column(Integer, default=1)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    matter: Mapped[Matter] = relationship(back_populates="documents")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("kind", "dedupe_key", name="uq_job_kind_dedupe"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(180))
    matter_id: Mapped[str] = mapped_column(String(36), index=True)
    input_revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    progress: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class Generation(Base):
    __tablename__ = "generations"
    __table_args__ = (
        UniqueConstraint("matter_id", "revision", name="uq_generation_matter_revision"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    matter_id: Mapped[str] = mapped_column(ForeignKey("matters.id", ondelete="CASCADE"), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    validation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("validation_runs.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    final_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    export_attestation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    final_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    package_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    package_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preview_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preview_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artifact_manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    matter: Mapped[Matter] = relationship(back_populates="generations")


class ValidationRun(Base):
    __tablename__ = "validation_runs"
    __table_args__ = (
        UniqueConstraint(
            "matter_id",
            "revision",
            "input_hash",
            "rule_version",
            name="uq_validation_input",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    matter_id: Mapped[str] = mapped_column(
        ForeignKey("matters.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    input_hash: Mapped[str] = mapped_column(String(64))
    rule_version: Mapped[str] = mapped_column(String(80))
    issues: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    matter: Mapped[Matter] = relationship(back_populates="validation_runs")


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("scope", "key", name="uq_idempotency_scope_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scope: Mapped[str] = mapped_column(String(120))
    key: Mapped[str] = mapped_column(String(120))
    request_hash: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
