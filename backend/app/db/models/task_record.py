from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.anomaly_issue_record import AnomalyIssueRecordModel
    from app.db.models.file_record import FileRecordModel
    from app.db.models.formula_rule_record import FormulaRuleRecordModel
    from app.db.models.sheet_record import SheetRecordModel
    from app.db.models.structure_version_record import StructureVersionRecordModel
    from app.db.models.validation_issue_record import ValidationIssueRecordModel


class TaskRecordModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        server_default=text("'uploaded'"),
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    file: Mapped["FileRecordModel"] = relationship(back_populates="tasks")
    sheets: Mapped[list["SheetRecordModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    structure_versions: Mapped[list["StructureVersionRecordModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="StructureVersionRecordModel.version_number",
    )
    formula_rules: Mapped[list["FormulaRuleRecordModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    validation_issues: Mapped[list["ValidationIssueRecordModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    anomaly_issues: Mapped[list["AnomalyIssueRecordModel"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )