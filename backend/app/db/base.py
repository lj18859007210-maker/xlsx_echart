from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for ORM models."""


# Import models so metadata is populated for migrations and tests.
from app.db.models import cell_record, file_record, sheet_record, task_record  # noqa: E402,F401
