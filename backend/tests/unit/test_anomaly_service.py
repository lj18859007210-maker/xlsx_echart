"""Day 17 tests - business rule anomaly detection."""

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.anomaly_issue_record import AnomalyIssueRecordModel
from app.db.models.file_record import FileRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.anomaly import anomaly_service
from app.services.anomaly.decline_detector import detect_consecutive_declines
from app.services.anomaly.growth_rate_detector import detect_growth_rate_anomalies
from app.services.anomaly.negative_zero_detector import detect_negative_zero_anomalies
from app.services.anomaly.structure_share_detector import detect_structure_share_anomalies


def _override_db_session(database_url: str) -> sessionmaker[Session]:
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
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _create_task(
    session_factory: sessionmaker[Session],
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    status: str = "validated",
) -> int:
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name="anomaly_test.xlsx",
            file_path="anomaly_test.xlsx",
            file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()

        task_record = TaskRecordModel(file_id=file_record.id, status=status)
        session.add(task_record)
        session.flush()

        sheet_record = SheetRecordModel(
            task_id=task_record.id,
            sheet_name="Sheet1",
            sheet_index=0,
            row_count=len(aligned_grid),
            col_count=len(aligned_grid[0]) if aligned_grid else 1,
            is_hidden=False,
        )
        session.add(sheet_record)
        session.flush()

        cell_roles = []
        for _row in aligned_grid:
            cell_roles.append(column_kinds[:])

        sv = StructureVersionRecordModel(
            task_id=task_record.id,
            version_number=1,
            snapshot_json={
                "sheets": [
                    {
                        "sheet_id": sheet_record.id,
                        "sheet_name": "Sheet1",
                        "sheet_index": 0,
                        "row_count": len(aligned_grid),
                        "col_count": len(aligned_grid[0]) if aligned_grid else 1,
                        "is_hidden": False,
                        "merge_ranges": [],
                        "aligned_grid": aligned_grid,
                        "aligned_cell_roles": cell_roles,
                        "aligned_source_map": [],
                        "cell_tags": [],
                        "column_paths": column_paths,
                        "column_kinds": column_kinds,
                    }
                ]
            },
            patch_summary_json={},
            is_confirmed=True,
        )
        session.add(sv)
        session.commit()
        return task_record.id


class TestGrowthRateDetector:
    def test_flags_growth_exceeding_threshold(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "200"],
            ["Q3", "210"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_growth_rate_anomalies(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["row_index"] == 2
        assert issues[0]["col_index"] == 1
        assert issues[0]["issue_type"] == "growth_rate_anomaly"
        assert issues[0]["metric_name"] == "Revenue"

    def test_flags_decline_exceeding_threshold(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "200"],
            ["Q2", "50"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_growth_rate_anomalies(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "growth_rate_anomaly"

    def test_skips_dimension_columns(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "200"],
        ]
        kinds = ["dimension", "dimension"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_growth_rate_anomalies(grid, kinds, paths)
        assert len(issues) == 0

    def test_skips_non_numeric_cells(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "N/A"],
            ["Q3", "200"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_growth_rate_anomalies(grid, kinds, paths)
        assert len(issues) == 0


class TestDeclineDetector:
    def test_flags_three_consecutive_declines(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "90"],
            ["Q3", "80"],
            ["Q4", "70"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_consecutive_declines(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "consecutive_decline"
        assert issues[0]["row_index"] == 4

    def test_no_flag_for_two_declines(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "90"],
            ["Q3", "80"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_consecutive_declines(grid, kinds, paths)
        assert len(issues) == 0

    def test_resets_on_interruption(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "90"],
            ["Q3", "95"],
            ["Q4", "85"],
            ["Q5", "75"],
            ["Q6", "65"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_consecutive_declines(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["row_index"] == 6


class TestNegativeZeroDetector:
    def test_flags_negative_value(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "-50"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_negative_zero_anomalies(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["issue_type"] == "negative_or_zero"
        assert issues[0]["severity"] == "error"

    def test_flags_zero_value(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "0"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_negative_zero_anomalies(grid, kinds, paths)
        assert len(issues) == 1
        assert issues[0]["severity"] == "warning"

    def test_skips_positive_values(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "50"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        issues = detect_negative_zero_anomalies(grid, kinds, paths)
        assert len(issues) == 0


class TestStructureShareDetector:
    def test_flags_large_share_change(self):
        grid = [
            ["Region", "ProductA", "ProductB"],
            ["Q1", "100", "100"],
            ["Q2", "100", "300"],
        ]
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["ProductA"], ["ProductB"]]

        issues = detect_structure_share_anomalies(grid, kinds, paths)
        assert len(issues) == 2

    def test_no_flag_for_small_share_change(self):
        grid = [
            ["Region", "ProductA", "ProductB"],
            ["Q1", "100", "100"],
            ["Q2", "110", "100"],
        ]
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["ProductA"], ["ProductB"]]

        issues = detect_structure_share_anomalies(grid, kinds, paths)
        assert len(issues) == 0


class TestAnomalyService:
    def test_orchestrates_all_detectors(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        grid = [
            ["Region", "Revenue", "Cost"],
            ["Q1", "100", "50"],
            ["Q2", "200", "45"],
            ["Q3", "-10", "40"],
        ]
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"]]
        task_id = _create_task(session_factory, grid, kinds, paths)

        with session_factory() as session:
            result = anomaly_service.detect_task_anomalies(task_id, session)

        assert result["detection_mode"] == "business_rule"
        assert result["anomaly_issue_count"] >= 2

        with session_factory() as session:
            records = list(
                session.scalars(
                    select(AnomalyIssueRecordModel).where(
                        AnomalyIssueRecordModel.task_id == task_id,
                    ),
                ),
            )
            assert len(records) == result["anomaly_issue_count"]

    def test_detect_anomalies_is_idempotent(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "200"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]
        task_id = _create_task(session_factory, grid, kinds, paths)

        with session_factory() as session:
            r1 = anomaly_service.detect_task_anomalies(task_id, session)

        with session_factory() as session:
            r2 = anomaly_service.detect_task_anomalies(task_id, session)

        assert r1["anomaly_issue_count"] == r2["anomaly_issue_count"]

    def test_get_anomaly_issues_returns_persisted(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "200"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]
        task_id = _create_task(session_factory, grid, kinds, paths)

        with session_factory() as session:
            anomaly_service.detect_task_anomalies(task_id, session)

        with session_factory() as session:
            issues = anomaly_service.get_anomaly_issues(task_id, session)

        assert len(issues) > 0
        assert issues[0]["task_id"] == task_id
        assert issues[0]["detection_source"] == "business_rule"

    def test_rejects_non_validated_task(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        grid = [["A"], ["1"]]
        kinds = ["dimension"]
        paths = [["A"]]
        task_id = _create_task(session_factory, grid, kinds, paths, status="uploaded")

        with session_factory() as session:
            with pytest.raises(anomaly_service.HTTPException, match="409"):
                anomaly_service.detect_task_anomalies(task_id, session)
