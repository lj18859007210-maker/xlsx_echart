"""add structure versions

Revision ID: 20260528_0003
Revises: 20260527_0002
Create Date: 2026-05-28 10:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260528_0003"
down_revision = "20260527_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "structure_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("patch_summary_json", sa.JSON(), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("task_id", "version_number", name="uq_structure_versions_task_version"),
    )


def downgrade() -> None:
    op.drop_table("structure_versions")
