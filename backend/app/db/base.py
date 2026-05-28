from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""


# Import models so metadata is populated for migrations and tests.
from app.db.models import (  # noqa: E402,F401
    anomaly_issue_record,
    cell_record,
    file_record,
    formula_rule_record,
    insight_record,
    sheet_record,
    structure_version_record,
    summary_record,
    task_record,
    validation_issue_record,
)