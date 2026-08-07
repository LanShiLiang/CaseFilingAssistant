"""补齐范围、金额、最终声明和制品审计字段。

Revision ID: 0003_reliable_review_gates
Revises: 0002_architecture_hardening
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_reliable_review_gates"
down_revision = "0002_architecture_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    matter_columns = {column["name"] for column in inspector.get_columns("matters")}
    if "scope_signals" not in matter_columns:
        op.add_column(
            "matters",
            sa.Column(
                "scope_signals", sa.JSON(), nullable=False, server_default=sa.text("'[]'")
            ),
        )
    if "amount_computation" not in matter_columns:
        op.add_column(
            "matters",
            sa.Column(
                "amount_computation", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
            ),
        )
    op.execute(
        sa.text(
            "UPDATE matters SET dossier_schema_version = 'dossier_v2' "
            "WHERE dossier_schema_version = 'dossier_v1'"
        )
    )

    generation_columns = {
        column["name"] for column in inspector.get_columns("generations")
    }
    additions = [
        sa.Column(
            "export_attestation", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        sa.Column("final_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("package_size_bytes", sa.Integer(), nullable=True),
        sa.Column("preview_sha256", sa.String(length=64), nullable=True),
        sa.Column("preview_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "artifact_manifest", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
    ]
    for column in additions:
        if column.name not in generation_columns:
            op.add_column("generations", column)


def downgrade() -> None:
    with op.batch_alter_table("generations") as batch:
        for name in (
            "artifact_manifest",
            "preview_size_bytes",
            "preview_sha256",
            "package_size_bytes",
            "final_confirmed_at",
            "export_attestation",
        ):
            batch.drop_column(name)

    op.execute(
        sa.text(
            "UPDATE matters SET dossier_schema_version = 'dossier_v1' "
            "WHERE dossier_schema_version = 'dossier_v2'"
        )
    )
    with op.batch_alter_table("matters") as batch:
        batch.drop_column("amount_computation")
        batch.drop_column("scope_signals")
