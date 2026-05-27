from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.session import get_db
from app.main import app


def _override_db_session(database_url: str) -> tuple[sessionmaker[Session], object]:
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    return testing_session, override_get_db


def test_upload_rejects_non_xlsx_files(tmp_path) -> None:
    _, override_get_db = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    app.dependency_overrides[get_db] = override_get_db
    settings.upload_dir = str(tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/api/files/upload",
        files={"file": ("report.csv", b"col1,col2", "text/csv")},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .xlsx files are supported"


def test_upload_rejects_empty_xlsx_files(tmp_path) -> None:
    _, override_get_db = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    app.dependency_overrides[get_db] = override_get_db
    settings.upload_dir = str(tmp_path / "uploads")
    client = TestClient(app)

    response = client.post(
        "/api/files/upload",
        files={"file": ("empty.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty"


def test_upload_persists_file_and_task_records(tmp_path) -> None:
    session_factory, override_get_db = _override_db_session(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    upload_dir = tmp_path / "uploads"
    app.dependency_overrides[get_db] = override_get_db
    settings.upload_dir = str(upload_dir)
    client = TestClient(app)

    response = client.post(
        "/api/files/upload",
        files={
            "file": (
                "finance.xlsx",
                b"fake-xlsx-content",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert isinstance(payload["file_id"], int)
    assert isinstance(payload["task_id"], int)

    saved_files = list(upload_dir.iterdir())
    assert len(saved_files) == 1
    assert saved_files[0].suffix == ".xlsx"
    assert saved_files[0].read_bytes() == b"fake-xlsx-content"

    with session_factory() as session:
        file_record = session.scalar(select(FileRecordModel))
        task_record = session.scalar(select(TaskRecordModel))

    assert file_record is not None
    assert file_record.file_name == "finance.xlsx"
    assert file_record.file_type == ".xlsx"
    assert file_record.file_path == str(saved_files[0])

    assert task_record is not None
    assert task_record.file_id == file_record.id
    assert task_record.status == "uploaded"
