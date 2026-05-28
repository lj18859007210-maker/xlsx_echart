from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.sheet_record import SheetRecordModel
    from app.db.models.task_record import TaskRecordModel


class AnomalyIssueRecordModel(Base):
    __tablename__ = "anomaly_issues"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sheet_id: Mapped[int] = mapped_column(
        ForeignKey("sheets.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    col_index: Mapped[int] = mapped_column(Integer, nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    detection_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="business_rule",
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecordModel"] = relationship(back_populates="anomaly_issues")
    sheet: Mapped["SheetRecordModel"] = relationship()