from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.formula_rule_record import FormulaRuleRecordModel
    from app.db.models.sheet_record import SheetRecordModel
    from app.db.models.task_record import TaskRecordModel


class ValidationIssueRecordModel(Base):
    __tablename__ = "validation_issues"

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
    formula_rule_id: Mapped[int | None] = mapped_column(
        ForeignKey("formula_rules.id", ondelete="SET NULL"),
        nullable=True,
    )
    row_index: Mapped[int] = mapped_column(Integer, nullable=False)
    col_index: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_value: Mapped[str] = mapped_column(String(500), nullable=False)
    actual_value: Mapped[str] = mapped_column(String(500), nullable=False)
    formula_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    task: Mapped["TaskRecordModel"] = relationship(back_populates="validation_issues")
    sheet: Mapped["SheetRecordModel"] = relationship()
    formula_rule: Mapped["FormulaRuleRecordModel | None"] = relationship()