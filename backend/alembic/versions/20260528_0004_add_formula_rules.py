"""add formula rules

Revision ID: 20260528_0004
Revises: 20260528_0003
Create Date: 2026-05-28 13:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "20260528_0004"
down_revision = "20260528_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "formula_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("formula_text", sa.Text(), nullable=False),
        sa.Column("formula_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rule_type", sa.String(length=30), nullable=False, server_default="inferred"),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("raw_candidate_json", sa.JSON(), nullable=False),
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
    op.drop_table("formula_rules")
