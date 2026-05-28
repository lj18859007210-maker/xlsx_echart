from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.sheet_record import SheetRecordModel
    from app.db.models.task_record import TaskRecordModel


class FormulaRuleRecordModel(Base):
    __tablename__ = "formula_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    sheet_id: Mapped[int] = mapped_column(
        ForeignKey("sheets.id", ondelete="CASCADE"),
        nullable=False,
    )
    formula_text: Mapped[str] = mapped_column(Text, nullable=False)
    formula_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, default="inferred")
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_candidate_json: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecordModel"] = relationship(back_populates="formula_rules")
    sheet: Mapped["SheetRecordModel"] = relationship()
