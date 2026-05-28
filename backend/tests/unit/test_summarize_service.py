"""Day 19 tests - summarization service."""

import json

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.anomaly_issue_record import AnomalyIssueRecordModel
from app.db.models.file_record import FileRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.summary_record import SummaryRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.models.validation_issue_record import ValidationIssueRecordModel
from app.services.summarize import summarize_service
from app.services.summarize.slice_builder import build_semantic_schema, build_slices
from app.services.summarize.summary_builder import build_statistical_summary
from app.services.summarize.token_estimator import estimate_tokens


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


def _create_task_with_issues(
    session_factory: sessionmaker[Session],
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
) -> int:
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name="test.xlsx", file_path="test.xlsx", file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()

        task_record = TaskRecordModel(file_id=file_record.id, status="validated")
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
                "sheets": [{
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
                }]
            },
            patch_summary_json={},
            is_confirmed=True,
        )
        session.add(sv)
        session.flush()

        # Add a validation issue
        session.add(
            ValidationIssueRecordModel(
                task_id=task_record.id,
                sheet_id=sheet_record.id,
                formula_rule_id=None,
                row_index=2,
                col_index=3,
                expected_value="20",
                actual_value="25",
                formula_text="col_Profit = col_Revenue - col_Cost",
                severity="error",
                issue_type="mismatch",
            ),
        )
        # Add an anomaly issue
        session.add(
            AnomalyIssueRecordModel(
                task_id=task_record.id,
                sheet_id=sheet_record.id,
                row_index=2,
                col_index=1,
                issue_type="growth_rate_anomaly",
                severity="warning",
                metric_name="Revenue",
                detection_source="business_rule",
                reason="Revenue anomaly",
                score=0.8,
            ),
        )
        session.commit()
        return task_record.id


class TestSummaryBuilder:
    def test_computes_measure_statistics(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", "200"],
            ["Q3", "150"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        result = build_statistical_summary(grid, kinds, paths, "P&L")
        assert result["sheet_name"] == "P&L"
        cols = result["columns"]
        assert len(cols) == 2

        rev = cols[1]
        assert rev["name"] == "Revenue"
        assert rev["kind"] == "measure"
        assert rev["count"] == 3
        assert rev["mean"] == 150.0
        assert rev["median"] == 150.0
        assert rev["min"] == 100.0
        assert rev["max"] == 200.0
        assert rev["volatility"] > 0
        assert rev["missing_rate"] == 0.0
        assert rev["trend"] == "up"

    def test_handles_missing_values(self):
        grid = [
            ["Region", "Revenue"],
            ["Q1", "100"],
            ["Q2", ""],
            ["Q3", "300"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]

        result = build_statistical_summary(grid, kinds, paths)
        rev = result["columns"][1]
        assert rev["count"] == 2
        assert rev["missing_rate"] == pytest.approx(0.3333, 0.01)


class TestSliceBuilder:
    def test_builds_slices_around_issues(self):
        grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["Q1", "100", "80", "20"],
            ["Q2", "90", "70", "25"],
            ["Q3", "110", "85", "25"],
        ]
        kinds = ["dimension", "measure", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]

        val_issues = [{
            "sheet_id": 1, "row_index": 2, "col_index": 3,
            "expected_value": "20", "actual_value": "25",
            "formula_text": "Profit = Rev - Cost",
            "severity": "error", "issue_type": "mismatch",
        }]
        anom_issues = [{
            "sheet_id": 1, "row_index": 2, "col_index": 1,
            "issue_type": "growth_rate_anomaly", "severity": "warning",
            "reason": "Revenue anomaly", "metric_name": "Revenue",
        }]

        slices = build_slices(grid, kinds, paths, "P&L", val_issues, anom_issues)
        assert len(slices) == 1
        s = slices[0]
        assert s["sheet_name"] == "P&L"
        assert s["start_row"] == 1  # row 2 with +/-1 context = rows 1-3
        assert s["end_row"] == 3
        assert len(s["header"]) == 4
        assert len(s["rows"]) == 3
        assert len(s["issue_cells"]) == 2
        assert "reason_tags" in s
        assert len(s["reason_tags"]) >= 1

    def test_build_semantic_schema(self):
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"]]

        schema = build_semantic_schema(kinds, paths, "P&L")
        assert schema["sheet_name"] == "P&L"
        assert schema["dimensions"] == ["Region"]
        assert schema["measures"] == ["Revenue", "Cost"]
        assert schema["time_columns"] == []


class TestTokenEstimator:
    def test_estimates_tokens(self):
        data = {"key": "value", "list": [1, 2, 3]}
        tokens = estimate_tokens(data)
        assert tokens > 0
        raw = json.dumps(data)
        assert tokens == max(1, int(len(raw) / 3.5))

    def test_estimates_chinese_text(self):
        data = {"summary": "\u8fd9\u662f\u4e00\u6bb5\u4e2d\u6587\u6587\u672c\u3002" * 10}
        tokens = estimate_tokens(data)
        assert tokens > 5


class TestSummarizeService:
    def test_summarize_produces_context_package(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["Q1", "100", "80", "20"],
            ["Q2", "200", "70", "25"],
            ["Q3", "150", "85", "25"],
        ]
        kinds = ["dimension", "measure", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]
        task_id = _create_task_with_issues(session_factory, grid, kinds, paths)

        with session_factory() as session:
            result = summarize_service.summarize_task(task_id, session)

        assert result["task_id"] == task_id
        assert "statistical_summary" in result
        assert len(result["statistical_summary"]) == 1
        assert "validation_issues_summary" in result
        assert result["validation_issues_summary"]["total"] == 1
        assert "anomaly_summary" in result
        assert result["anomaly_summary"]["total"] == 1
        assert "slices" in result
        assert len(result["slices"]) >= 1
        assert "semantic_schema" in result
        assert "token_estimate" in result
        assert result["token_estimate"] > 0
        assert "token_budget" in result
        assert "trimmed" in result

    def test_summary_is_persisted(self, tmp_path):
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
        task_id = _create_task_with_issues(session_factory, grid, kinds, paths)

        with session_factory() as session:
            summarize_service.summarize_task(task_id, session)

        with session_factory() as session:
            record = session.scalar(
                select(SummaryRecordModel).where(
                    SummaryRecordModel.task_id == task_id,
                ),
            )
            assert record is not None
            assert record.token_estimate > 0

    def test_get_summary_returns_persisted(self, tmp_path):
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
        task_id = _create_task_with_issues(session_factory, grid, kinds, paths)

        with session_factory() as session:
            summarize_service.summarize_task(task_id, session)

        with session_factory() as session:
            result = summarize_service.get_summary(task_id, session)

        assert result is not None
        assert result["task_id"] == task_id
        assert result["token_estimate"] > 0

    def test_get_summary_returns_none_for_no_data(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        with session_factory() as session:
            result = summarize_service.get_summary(999, session)
        assert result is None