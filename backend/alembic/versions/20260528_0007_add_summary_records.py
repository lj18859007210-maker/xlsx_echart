"""add summary records

Revision ID: 20260528_0007
Revises: 20260528_0006
Create Date: 2026-05-28 18:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260528_0007"
down_revision = "20260528_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "summary_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("slice_json", sa.JSON(), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_budget", sa.Integer(), nullable=False, server_default="4000"),
        sa.Column("trimmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("summary_records")