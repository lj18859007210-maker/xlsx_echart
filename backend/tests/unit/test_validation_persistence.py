"""Day 16 tests — validation issue persistence."""

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.models.validation_issue_record import ValidationIssueRecordModel
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
    """Create a confirmed task with structure version and formula rules.

    Data: Profit = Revenue - Cost
    Row 1 (East):  100 - 80 = 20 (correct)
    Row 2 (West):  90 - 70 = 20 but actual is 25 (mismatch!)
    """
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


class TestValidationPersistence:
    """Day 16: validation issues persisted to DB."""

    def test_persist_issues_on_validate(self, tmp_path):
        """Validate writes issues to validation_issues table."""
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id, _ = _create_validated_task(session_factory)

        with session_factory() as session:
            result = validation_service.validate_task_formulas(task_id, session)

        assert result["total_issues"] == 1

        # Verify issues are persisted in DB
        with session_factory() as session:
            records = list(
                session.scalars(
                    select(ValidationIssueRecordModel).where(
                        ValidationIssueRecordModel.task_id == task_id,
                    ),
                ),
            )
            assert len(records) == 1
            r = records[0]
            assert r.task_id == task_id
            assert r.sheet_id == 1
            assert r.formula_rule_id is not None
            assert r.row_index == 2  # West row (0-indexed)
            assert r.col_index == 3  # Profit column
            assert r.expected_value == "20"
            assert r.actual_value == "25"
            assert r.formula_text == "col_Profit = col_Revenue - col_Cost"
            assert r.severity == "error"
            assert r.issue_type == "mismatch"

    def test_revalidate_clears_old_issues(self, tmp_path):
        """Second validate call deletes old issues before inserting new ones."""
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id, _ = _create_validated_task(session_factory)

        # First validate
        with session_factory() as session:
            validation_service.validate_task_formulas(task_id, session)

        # Second validate
        with session_factory() as session:
            validation_service.validate_task_formulas(task_id, session)

        # Should still have 1 issue (not 2) — idempotent
        with session_factory() as session:
            count = session.scalar(
                select(func.count()).select_from(
                    select(ValidationIssueRecordModel)
                    .where(ValidationIssueRecordModel.task_id == task_id)
                    .subquery(),
                ),
            )
            assert count == 1  # noqa: E712

    def test_validate_updates_task_status(self, tmp_path):
        """Validate transitions task status to 'validated'."""
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id, _ = _create_validated_task(session_factory)

        with session_factory() as session:
            validation_service.validate_task_formulas(task_id, session)

        with session_factory() as session:
            task = session.scalar(
                select(TaskRecordModel).where(TaskRecordModel.id == task_id),
            )
            assert task is not None
            assert task.status == "validated"

    def test_empty_validation_no_persistence_error(self, tmp_path):
        """No issues → no crash, no orphan records."""
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        # Create task without formula rules (no issues possible)
        with session_factory() as session:
            file_record = FileRecordModel(
                file_name="empty.xlsx",
                file_path="empty.xlsx",
                file_type=".xlsx",
            )
            session.add(file_record)
            session.flush()

            task_record = TaskRecordModel(
                file_id=file_record.id,
                status="formula_gap_acknowledged",
            )
            session.add(task_record)
            session.flush()

            sheet_record = SheetRecordModel(
                task_id=task_record.id,
                sheet_name="Sheet1",
                sheet_index=0,
                row_count=1,
                col_count=1,
                is_hidden=False,
            )
            session.add(sheet_record)
            session.flush()

            sv = StructureVersionRecordModel(
                task_id=task_record.id,
                version_number=1,
                snapshot_json={
                    "sheets": [
                        {
                            "sheet_id": sheet_record.id,
                            "sheet_name": "Sheet1",
                            "sheet_index": 0,
                            "row_count": 1,
                            "col_count": 1,
                            "is_hidden": False,
                            "merge_ranges": [],
                            "aligned_grid": [["A"]],
                            "aligned_cell_roles": [["dimension"]],
                            "aligned_source_map": [],
                            "cell_tags": [],
                            "column_paths": [["A"]],
                            "column_kinds": ["dimension"],
                        }
                    ]
                },
                patch_summary_json={},
                is_confirmed=True,
            )
            session.add(sv)
            session.commit()
            task_id = task_record.id

        with session_factory() as session:
            result = validation_service.validate_task_formulas(task_id, session)

        assert result["total_issues"] == 0
        assert result["issues"] == []

        # No DB records written
        with session_factory() as session:
            count = session.scalar(
                select(func.count()).select_from(
                    select(ValidationIssueRecordModel)
                    .where(ValidationIssueRecordModel.task_id == task_id)
                    .subquery(),
                ),
            )
            assert count == 0  # noqa: E712

    def test_get_validation_issues_returns_persisted(self, tmp_path):
        """get_validation_issues reads back what validate persisted."""
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id, _ = _create_validated_task(session_factory)

        with session_factory() as session:
            validation_service.validate_task_formulas(task_id, session)

        with session_factory() as session:
            issues = validation_service.get_validation_issues(task_id, session)

        assert len(issues) == 1
        issue = issues[0]
        assert issue["task_id"] == task_id
        assert issue["sheet_id"] == 1
        assert issue["formula_rule_id"] is not None
        assert issue["row_index"] == 2
        assert issue["col_index"] == 3
        assert issue["expected_value"] == "20"
        assert issue["actual_value"] == "25"
        assert issue["severity"] == "error"
        assert issue["issue_type"] == "mismatch"