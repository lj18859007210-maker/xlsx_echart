"""add insight records

Revision ID: 20260528_0008
Revises: 20260528_0007
Create Date: 2026-05-28 19:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260528_0008"
down_revision = "20260528_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insight_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("executive_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("key_findings_json", sa.JSON(), nullable=False),
        sa.Column("risks_json", sa.JSON(), nullable=False),
        sa.Column("recommendations_json", sa.JSON(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("chart_hints_json", sa.JSON(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("insight_records")