"""add validation issues

Revision ID: 20260528_0005
Revises: 20260528_0004
Create Date: 2026-05-28 16:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260528_0005"
down_revision = "20260528_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "validation_issues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("formula_rule_id", sa.Integer(), nullable=True),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("expected_value", sa.String(length=500), nullable=False),
        sa.Column("actual_value", sa.String(length=500), nullable=False),
        sa.Column("formula_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("issue_type", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["formula_rule_id"],
            ["formula_rules.id"],
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("validation_issues")