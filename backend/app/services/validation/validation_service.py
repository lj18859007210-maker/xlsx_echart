"""Day 15+16 validation orchestration service with persistence."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.models.validation_issue_record import ValidationIssueRecordModel
from app.services.formula.formula_quality_filter import filter_formula_rules
from app.services.structure_version_service import preferred_structure_version

from .aggregate_validator import validate_aggregates
from .execution_plan import build_execution_plans
from .row_validator import validate_rows


def validate_task_formulas(
    task_id: int,
    db: Session,
) -> dict[str, object]:
    """Validate a task's formula rules against confirmed sheet data.

    Day 16: persisted issues to validation_issues table after validation.
    """
    task = db.scalar(
        select(TaskRecordModel)
        .where(TaskRecordModel.id == task_id)
        .options(
            selectinload(TaskRecordModel.sheets).selectinload(SheetRecordModel.cells),
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status == "formula_gap_acknowledged":
        return _empty_result(task_id, task.status)

    if task.status not in ("confirmed", "validated", "analyzed", "chart_ready"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be confirmed before validation",
        )

    structure = preferred_structure_version(task)
    if structure is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No structure version available",
        )

    sheets_data = structure.snapshot_json.get("sheets", [])
    if not isinstance(sheets_data, list) or not sheets_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sheets in structure version",
        )

    records = list(
        db.scalars(
            select(FormulaRuleRecordModel).where(
                FormulaRuleRecordModel.task_id == task_id,
                FormulaRuleRecordModel.verification_passed == True,  # noqa: E712
            ),
        ),
    )

    raw_rules: list[dict[str, object]] = [
        {
            "id": r.id,
            "sheet_id": r.sheet_id,
            "formula_text": r.formula_text,
            "formula_type": r.formula_type,
            "confidence": r.confidence,
            "verification_score": r.verification_score,
        }
        for r in records
    ]

    passed_rules, _, _ = filter_formula_rules(raw_rules, quality_threshold=0.3)

    if not passed_rules:
        _persist_issues(task_id, [], db)
        _set_task_validated(task, db)
        return _empty_result(task_id, task.status)

    all_issues: list[dict[str, object]] = []

    for sheet_data in sheets_data:
        sheet_id = int(sheet_data.get("sheet_id", 0))
        aligned_grid = sheet_data.get("aligned_grid", [])
        if not isinstance(aligned_grid, list) or len(aligned_grid) < 2:
            continue

        column_paths = sheet_data.get("column_paths", [])
        column_map = _build_column_map(column_paths, aligned_grid)

        sheet_rules = [r for r in passed_rules if int(r["sheet_id"]) == sheet_id]
        if not sheet_rules:
            continue

        plans = build_execution_plans(sheet_rules, column_map)
        if not plans:
            continue

        row_issues = validate_rows(aligned_grid, plans)
        agg_issues = validate_aggregates(aligned_grid, plans)

        for issue in row_issues + agg_issues:
            issue["sheet_id"] = sheet_id
            issue["sheet_name"] = str(sheet_data.get("sheet_name", ""))

        all_issues.extend(row_issues + agg_issues)

    error_count = sum(1 for i in all_issues if i["severity"] == "error")
    warning_count = sum(1 for i in all_issues if i["severity"] == "warning")

    # Day 16: persist issues to DB
    _persist_issues(task_id, all_issues, db)
    _set_task_validated(task, db)

    return {
        "task_id": task.id,
        "status": task.status,
        "total_issues": len(all_issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": all_issues,
    }


def get_validation_issues(
    task_id: int,
    db: Session,
) -> list[dict[str, object]]:
    """Read persisted validation issues for a task."""
    records = list(
        db.scalars(
            select(ValidationIssueRecordModel).where(
                ValidationIssueRecordModel.task_id == task_id,
            ).order_by(
                ValidationIssueRecordModel.sheet_id,
                ValidationIssueRecordModel.row_index,
                ValidationIssueRecordModel.col_index,
            ),
        ),
    )
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "sheet_id": r.sheet_id,
            "formula_rule_id": r.formula_rule_id,
            "row_index": r.row_index,
            "col_index": r.col_index,
            "expected_value": r.expected_value,
            "actual_value": r.actual_value,
            "formula_text": r.formula_text,
            "severity": r.severity,
            "issue_type": r.issue_type,
        }
        for r in records
    ]


def _persist_issues(
    task_id: int,
    issues: list[dict[str, object]],
    db: Session,
) -> None:
    """Delete old issues for the task and insert new ones (idempotent)."""
    db.execute(
        delete(ValidationIssueRecordModel).where(
            ValidationIssueRecordModel.task_id == task_id,
        ),
    )
    for issue in issues:
        rule_id_raw = issue.get("rule_id")
        db.add(
            ValidationIssueRecordModel(
                task_id=task_id,
                sheet_id=int(issue["sheet_id"]),
                formula_rule_id=int(rule_id_raw) if rule_id_raw is not None else None,
                row_index=int(issue["row_index"]),
                col_index=int(issue["col_index"]),
                expected_value=str(issue["expected_value"]),
                actual_value=str(issue["actual_value"]),
                formula_text=str(issue["formula_text"]),
                severity=str(issue["severity"]),
                issue_type=str(issue["issue_type"]),
            ),
        )
    db.commit()


def _set_task_validated(task: TaskRecordModel, db: Session) -> None:
    """Transition task status to 'validated' if currently in an earlier state."""
    if task.status in ("confirmed",):
        task.status = "validated"
        db.commit()


def _build_column_map(
    column_paths: list,
    aligned_grid: list[list],
) -> dict[str, int]:
    """Build col_ prefixed column name to grid index mapping."""
    column_map: dict[str, int] = {}
    if isinstance(column_paths, list):
        for index, path in enumerate(column_paths):
            if isinstance(path, list) and path:
                column_map[f"col_{path[-1]}"] = index
    if aligned_grid and isinstance(aligned_grid[0], list):
        for index, value in enumerate(aligned_grid[0]):
            if value not in (None, ""):
                column_map.setdefault(f"col_{value}", index)
    return column_map


def _empty_result(task_id: int, status: str) -> dict[str, object]:
    return {
        "task_id": task_id,
        "status": status,
        "total_issues": 0,
        "error_count": 0,
        "warning_count": 0,
        "issues": [],
    }