from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.task_record import TaskRecordModel


class InsightRecordModel(Base):
    __tablename__ = "insight_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    key_findings_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    risks_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    recommendations_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    citations_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    chart_hints_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecordModel"] = relationship()