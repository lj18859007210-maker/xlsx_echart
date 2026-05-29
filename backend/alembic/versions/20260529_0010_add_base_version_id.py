"""Day 29 - add base_version_id column for compressed structure version diffs.

Revision ID: 20260529_0010
Revises: 20260529_0009
Create Date: 2026-05-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260529_0010"
down_revision: Union[str, None] = "20260529_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("structure_versions") as batch_op:
        batch_op.add_column(
            sa.Column("base_version_id", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    with op.batch_alter_table("structure_versions") as batch_op:
        batch_op.drop_column("base_version_id")
