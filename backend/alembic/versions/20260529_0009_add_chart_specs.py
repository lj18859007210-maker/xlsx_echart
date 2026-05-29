"""add chart specs

Revision ID: 20260529_0009
Revises: 20260528_0008
Create Date: 2026-05-29 12:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import sqlite

revision = "20260529_0009"
down_revision = "20260528_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chart_specs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "task_id",
            sa.Integer(),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chart_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("chart_type", sa.String(50), nullable=False, server_default=sa.text("''")),
        sa.Column("title", sa.String(200), nullable=False, server_default=sa.text("''")),
        sa.Column("x_field", sa.String(200), nullable=False, server_default=sa.text("''")),
        sa.Column("y_fields_json", sqlite.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("series_json", sqlite.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("highlights_json", sqlite.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source_cells_json", sqlite.JSON, nullable=False, server_default=sa.text("'[]'")),
        sa.Column("reason", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("chart_specs")
