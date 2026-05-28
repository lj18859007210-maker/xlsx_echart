from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, event
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

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    return testing_session, override_get_db


def _build_sample_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "经营分析"
    sheet["A1"] = "Header"
    sheet.merge_cells("A1:B1")
    sheet["A2"] = 100
    sheet["B2"] = 200
    workbook.save(path)
    workbook.close()


def _build_dual_track_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "双轨"
    sheet["A1"] = "区域"
    sheet.merge_cells("A1:A2")
    sheet["B1"] = 500
    sheet.merge_cells("B1:C1")
    sheet["B2"] = 100
    sheet["C2"] = 200
    workbook.save(path)
    workbook.close()


def _create_uploaded_task(session_factory: sessionmaker[Session], workbook_path: Path) -> int:
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name=workbook_path.name,
            file_path=str(workbook_path),
            file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()
        task_record = TaskRecordModel(file_id=file_record.id, status="uploaded")
        session.add(task_record)
        session.commit()
        session.refresh(task_record)
        return task_record.id


def test_review_returns_task_level_sheet_snapshots(tmp_path) -> None:
    session_factory, override_get_db = _override_db_session(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    app.dependency_overrides[get_db] = override_get_db
    settings.upload_dir = str(tmp_path / "uploads")
    client = TestClient(app)

    workbook_path = tmp_path / "source.xlsx"
    _build_sample_workbook(workbook_path)
    task_id = _create_uploaded_task(session_factory, workbook_path)

    parse_response = client.post(f"/api/tasks/{task_id}/parse")
    assert parse_response.status_code == 200

    response = client.get(f"/api/tasks/{task_id}/review")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task_id
    assert payload["status"] == "waiting_confirm"
    assert payload["structure_version"] == 0
    assert len(payload["sheets"]) == 1

    sheet = payload["sheets"][0]
    assert sheet["sheet_name"] == "经营分析"
    assert sheet["row_count"] == 2
    assert sheet["col_count"] == 2
    assert sheet["merge_ranges"] == ["A1:B1"]
    assert sheet["grid_snapshot"] == [["Header", None], ["100", "200"]]
    assert sheet["address_map"] == [["A1", "B1"], ["A2", "B2"]]
    assert sheet["aligned_grid"] == [["Header", "Header"], ["100", "200"]]
    assert sheet["aligned_cell_roles"] == [["dimension", "dimension"], ["measure", "measure"]]
    assert sheet["aligned_source_map"] == [["A1", "A1"], ["A2", "B2"]]
    assert sheet["raw_cells"][0]["address"] == "A1"
    assert sheet["raw_cells"][0]["merge_range"] == "A1:B1"


def test_review_returns_404_for_missing_task(tmp_path) -> None:
    _, override_get_db = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/api/tasks/999/review")
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_review_builds_dual_track_alignment_for_dimension_and_measure_merges(tmp_path) -> None:
    session_factory, override_get_db = _override_db_session(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    workbook_path = tmp_path / "dual-track.xlsx"
    _build_dual_track_workbook(workbook_path)
    task_id = _create_uploaded_task(session_factory, workbook_path)

    parse_response = client.post(f"/api/tasks/{task_id}/parse")
    assert parse_response.status_code == 200

    response = client.get(f"/api/tasks/{task_id}/review")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    sheet = payload["sheets"][0]

    assert sheet["grid_snapshot"] == [["区域", "500", None], [None, "100", "200"]]
    assert sheet["aligned_grid"] == [["区域", "500", None], ["区域", "100", "200"]]
    assert sheet["aligned_cell_roles"] == [
        ["dimension", "measure", "measure"],
        ["dimension", "measure", "measure"],
    ]
    assert sheet["aligned_source_map"] == [["A1", "B1", "C1"], ["A1", "B2", "C2"]]
