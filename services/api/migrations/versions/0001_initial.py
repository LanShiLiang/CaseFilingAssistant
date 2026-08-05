"""初始化可靠 MVP 数据结构。

Revision ID: 0001_initial
Revises:
"""

from alembic import op

from app import models  # noqa: F401
from app.database import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 初始版本从完整 metadata 建库；后续共享分支迁移必须逐表前向演进，不能改写本文件。
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
