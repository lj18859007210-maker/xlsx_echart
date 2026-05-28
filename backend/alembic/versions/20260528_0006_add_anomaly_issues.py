"""add anomaly issues

Revision ID: 20260528_0006
Revises: 20260528_0005
Create Date: 2026-05-28 17:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260528_0006"
down_revision = "20260528_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anomaly_issues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("metric_name", sa.String(length=200), nullable=False),
        sa.Column("detection_source", sa.String(length=30), nullable=False, server_default="business_rule"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("anomaly_issues")