from pathlib import Path

from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.session import engine


def test_database_engine_uses_configured_sqlite_url() -> None:
    assert str(engine.url) == settings.database_url


def test_base_metadata_registers_core_tables() -> None:
    assert {"files", "tasks", "sheets"}.issubset(Base.metadata.tables.keys())


def test_core_models_define_expected_relationships() -> None:
    assert FileRecordModel.__tablename__ == "files"
    assert TaskRecordModel.__tablename__ == "tasks"
    assert SheetRecordModel.__tablename__ == "sheets"

    assert "tasks" in FileRecordModel.__mapper__.relationships.keys()
    assert "file" in TaskRecordModel.__mapper__.relationships.keys()
    assert "sheets" in TaskRecordModel.__mapper__.relationships.keys()
    assert "task" in SheetRecordModel.__mapper__.relationships.keys()


def test_sqlite_engine_enables_foreign_keys() -> None:
    with engine.connect() as connection:
        foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()

    assert foreign_keys == 1


def test_task_status_has_server_default() -> None:
    status_column = TaskRecordModel.__table__.c.status

    assert status_column.server_default is not None


def test_alembic_ini_does_not_hardcode_local_database_path() -> None:
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    contents = alembic_ini.read_text(encoding="utf-8")

    assert "D:/AAA-Project/head/xlsx_echart" not in contents
