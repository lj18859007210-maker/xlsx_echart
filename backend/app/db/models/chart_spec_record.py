"""Day 21 chart_specs ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.task_record import TaskRecordModel


class ChartSpecRecordModel(Base):
    __tablename__ = "chart_specs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chart_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chart_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    x_field: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    y_fields_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    series_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    highlights_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    source_cells_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecordModel"] = relationship()