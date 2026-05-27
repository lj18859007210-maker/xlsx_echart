"""add cells and sheet metadata

Revision ID: 20260527_0002
Revises: 20260527_0001
Create Date: 2026-05-27 20:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260527_0002"
down_revision = "20260527_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sheets", sa.Column("sheet_index", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("sheets", sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "cells",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=20), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("value_type", sa.String(length=50), nullable=False),
        sa.Column("is_merged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("merge_range", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("cells")
    op.drop_column("sheets", "is_hidden")
    op.drop_column("sheets", "sheet_index")
