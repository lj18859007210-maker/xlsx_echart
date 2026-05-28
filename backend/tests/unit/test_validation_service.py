import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.validation import validation_service


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


def _create_validated_task(
    session_factory: sessionmaker[Session],
) -> tuple[int, list[list]]:
    """Create a confirmed task with structure version and formula rules."""
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name="validate.xlsx",
            file_path="validate.xlsx",
            file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()

        task_record = TaskRecordModel(file_id=file_record.id, status="confirmed")
        session.add(task_record)
        session.flush()

        sheet_record = SheetRecordModel(
            task_id=task_record.id,
            sheet_name="P&L",
            sheet_index=0,
            row_count=3,
            col_count=4,
            is_hidden=False,
        )
        session.add(sheet_record)
        session.flush()

        aligned_grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "25"],
        ]

        sv = StructureVersionRecordModel(
            task_id=task_record.id,
            version_number=1,
            snapshot_json={
                "sheets": [
                    {
                        "sheet_id": sheet_record.id,
                        "sheet_name": "P&L",
                        "sheet_index": 0,
                        "row_count": 3,
                        "col_count": 4,
                        "is_hidden": False,
                        "merge_ranges": [],
                        "aligned_grid": aligned_grid,
                        "aligned_cell_roles": [
                            ["dimension", "measure", "measure", "measure"],
                            ["dimension", "measure", "measure", "measure"],
                            ["dimension", "measure", "measure", "measure"],
                        ],
                        "aligned_source_map": [],
                        "cell_tags": [],
                        "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
                        "column_kinds": ["dimension", "measure", "measure", "measure"],
                    }
                ]
            },
            patch_summary_json={},
            is_confirmed=True,
        )
        session.add(sv)
        session.flush()

        # Add formula rule: Profit = Revenue - Cost
        session.add(
            FormulaRuleRecordModel(
                task_id=task_record.id,
                sheet_id=sheet_record.id,
                formula_text="col_Profit = col_Revenue - col_Cost",
                formula_type="column_arithmetic",
                description="profit = revenue - cost",
                confidence=0.9,
                verification_passed=True,
                verification_score=0.9,
                prompt_version="day13_v1",
                model_name="mock/day13",
            )
        )
        session.commit()
        return task_record.id, aligned_grid


def test_validate_finds_row_mismatch(tmp_path):
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id, _ = _create_validated_task(session_factory)

    with session_factory() as session:
        result = validation_service.validate_task_formulas(task_id, session)

    assert result["total_issues"] == 1
    assert result["error_count"] == 1
    assert result["warning_count"] == 0
    issue = result["issues"][0]
    assert issue["sheet_id"] == 1
    assert issue["sheet_name"] == "P&L"
    assert issue["severity"] == "error"
    assert issue["issue_type"] == "mismatch"
    assert issue["expected_value"] == "20"
    assert issue["actual_value"] == "25"


def test_validate_skips_gap_acknowledged_task(tmp_path):
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id, _ = _create_validated_task(session_factory)

    with session_factory() as session:
        task = session.scalar(select(TaskRecordModel).where(TaskRecordModel.id == task_id))
        assert task is not None
        task.status = "formula_gap_acknowledged"
        session.commit()

    with session_factory() as session:
        result = validation_service.validate_task_formulas(task_id, session)

    assert result["total_issues"] == 0
    assert result["issues"] == []


def test_validate_requires_confirmed_task(tmp_path):
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name="t.xlsx",
            file_path="t.xlsx",
            file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()
        task_record = TaskRecordModel(file_id=file_record.id, status="uploaded")
        session.add(task_record)
        session.commit()
        task_id = task_record.id

    with session_factory() as session:
        with pytest.raises(validation_service.HTTPException, match="409"):
            validation_service.validate_task_formulas(task_id, session)


