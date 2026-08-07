"""增加任务租约、材料版本、校验记录和不可变生成输入。

Revision ID: 0002_architecture_hardening
Revises: 0001_initial

`0001_initial` 使用动态 metadata 建库，因此空库执行 0001 时可能已经得到本版本字段。
这里对列和表做存在性判断，兼容“已发布 v0.1.0 数据库升级”和“当前代码空库建库”两条路径；
后续迁移不得继续依赖动态 metadata。
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_architecture_hardening"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table_name)}


def _indexes(table_name: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_indexes(table_name)}


def _foreign_keys(table_name: str) -> set[str]:
    return {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_foreign_keys(table_name)
        if item["name"]
    }


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "validation_runs" not in tables:
        op.create_table(
            "validation_runs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("matter_id", sa.String(length=36), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("input_hash", sa.String(length=64), nullable=False),
            sa.Column("rule_version", sa.String(length=80), nullable=False),
            sa.Column("issues", sa.JSON(), nullable=False),
            sa.Column("passed", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["matter_id"], ["matters.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "matter_id",
                "revision",
                "input_hash",
                "rule_version",
                name="uq_validation_input",
            ),
        )
        op.create_index("ix_validation_runs_matter_id", "validation_runs", ["matter_id"])
        op.create_index("ix_validation_runs_passed", "validation_runs", ["passed"])

    matter_columns = _columns("matters")
    if "dossier_schema_version" not in matter_columns:
        op.add_column(
            "matters",
            sa.Column(
                "dossier_schema_version",
                sa.String(length=40),
                nullable=False,
                server_default="dossier_v1",
            ),
        )

    document_columns = _columns("documents")
    with op.batch_alter_table("documents") as batch:
        if "active" not in document_columns:
            batch.add_column(
                sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true())
            )
        if "parse_revision" not in document_columns:
            batch.add_column(
                sa.Column("parse_revision", sa.Integer(), nullable=False, server_default="1")
            )
    if "ix_documents_active" not in _indexes("documents"):
        op.create_index("ix_documents_active", "documents", ["active"])

    job_columns = _columns("jobs")
    with op.batch_alter_table("jobs") as batch:
        if "lease_owner" not in job_columns:
            batch.add_column(sa.Column("lease_owner", sa.String(length=120), nullable=True))
        if "heartbeat_at" not in job_columns:
            batch.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))

    generation_columns = _columns("generations")
    with op.batch_alter_table("generations") as batch:
        if "validation_run_id" not in generation_columns:
            batch.add_column(sa.Column("validation_run_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_generations_validation_run_id",
                "validation_runs",
                ["validation_run_id"],
                ["id"],
                ondelete="RESTRICT",
            )
        if "input_snapshot" not in generation_columns:
            batch.add_column(
                sa.Column("input_snapshot", sa.JSON(), nullable=False, server_default="{}")
            )
        if "input_hash" not in generation_columns:
            batch.add_column(sa.Column("input_hash", sa.String(length=64), nullable=True))
    if "ix_generations_validation_run_id" not in _indexes("generations"):
        op.create_index(
            "ix_generations_validation_run_id", "generations", ["validation_run_id"]
        )


def downgrade() -> None:
    if "ix_generations_validation_run_id" in _indexes("generations"):
        op.drop_index("ix_generations_validation_run_id", table_name="generations")
    generation_columns = _columns("generations")
    with op.batch_alter_table("generations") as batch:
        if "fk_generations_validation_run_id" in _foreign_keys("generations"):
            batch.drop_constraint("fk_generations_validation_run_id", type_="foreignkey")
        for name in ("input_hash", "input_snapshot", "validation_run_id"):
            if name in generation_columns:
                batch.drop_column(name)

    job_columns = _columns("jobs")
    with op.batch_alter_table("jobs") as batch:
        for name in ("heartbeat_at", "lease_owner"):
            if name in job_columns:
                batch.drop_column(name)

    if "ix_documents_active" in _indexes("documents"):
        op.drop_index("ix_documents_active", table_name="documents")
    document_columns = _columns("documents")
    with op.batch_alter_table("documents") as batch:
        for name in ("parse_revision", "active"):
            if name in document_columns:
                batch.drop_column(name)

    if "validation_runs" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("validation_runs")

    if "dossier_schema_version" in _columns("matters"):
        op.drop_column("matters", "dossier_schema_version")
