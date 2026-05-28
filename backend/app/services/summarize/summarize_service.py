"""Day 19 - summarization orchestration service."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.anomaly_issue_record import AnomalyIssueRecordModel
from app.db.models.summary_record import SummaryRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.models.validation_issue_record import ValidationIssueRecordModel
from app.services.structure_version_service import preferred_structure_version

from .slice_builder import build_semantic_schema, build_slices
from .summary_builder import build_statistical_summary
from .token_estimator import DEFAULT_TOKEN_BUDGET, estimate_tokens

# Summarize is valid after validation or formula-gap-acknowledged
_SUMMARIZE_ALLOWED_STATUSES = frozenset({
    "validated",
    "formula_gap_acknowledged",
    "analyzed",
    "chart_ready",
})


def summarize_task(
    task_id: int,
    db: Session,
) -> dict[str, object]:
    """Generate a compressed context package for AI analysis."""
    task = db.scalar(
        select(TaskRecordModel).where(TaskRecordModel.id == task_id),
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status not in _SUMMARIZE_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be validated before summarization",
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

    # Load issues
    validation_issues = _load_validation_issues(task_id, db)
    anomaly_issues = _load_anomaly_issues(task_id, db)

    # Build per-sheet components
    summaries: list[dict[str, object]] = []
    schemas: list[dict[str, object]] = []
    all_slices: list[dict[str, object]] = []

    for sheet_data in sheets_data:
        sheet_id = int(sheet_data.get("sheet_id", 0))
        sheet_name = str(sheet_data.get("sheet_name", ""))
        aligned_grid = sheet_data.get("aligned_grid", [])
        column_paths = sheet_data.get("column_paths", [])
        column_kinds = sheet_data.get("column_kinds", [])

        if not isinstance(aligned_grid, list) or len(aligned_grid) < 1:
            continue

        summaries.append(
            build_statistical_summary(aligned_grid, column_kinds, column_paths, sheet_name),
        )
        schemas.append(
            build_semantic_schema(column_kinds, column_paths, sheet_name),
        )

        sheet_val_issues = [i for i in validation_issues if i.get("sheet_id") == sheet_id]
        sheet_anom_issues = [i for i in anomaly_issues if i.get("sheet_id") == sheet_id]
        all_slices.extend(
            build_slices(
                aligned_grid,
                column_kinds,
                column_paths,
                sheet_name,
                sheet_val_issues,
                sheet_anom_issues,
            ),
        )

    # Build context package
    validation_summary = _summarize_issues(validation_issues, "validation")
    anomaly_summary = _summarize_issues(anomaly_issues, "anomaly")

    context_package = {
        "task_id": task_id,
        "statistical_summary": summaries,
        "validation_issues_summary": validation_summary,
        "anomaly_summary": anomaly_summary,
        "slices": all_slices,
        "semantic_schema": schemas,
    }

    # Token estimation + trimming
    token_estimate = estimate_tokens(context_package)
    trimmed = False

    if token_estimate > DEFAULT_TOKEN_BUDGET and len(all_slices) > 0:
        all_slices.sort(
            key=lambda s: 0 if any(
                c.get("severity") == "error" for c in s.get("issue_cells", [])
            ) else 1,
        )
        while token_estimate > DEFAULT_TOKEN_BUDGET and len(all_slices) > 0:
            all_slices.pop()
            context_package["slices"] = all_slices
            token_estimate = estimate_tokens(context_package)
        trimmed = True

    _persist_summary(task_id, context_package, all_slices, token_estimate, trimmed, db)

    return {
        "task_id": task_id,
        "statistical_summary": summaries,
        "validation_issues_summary": validation_summary,
        "anomaly_summary": anomaly_summary,
        "slices": all_slices,
        "semantic_schema": schemas,
        "token_estimate": token_estimate,
        "token_budget": DEFAULT_TOKEN_BUDGET,
        "trimmed": trimmed,
    }


def get_summary(task_id: int, db: Session) -> dict[str, object] | None:
    """Read persisted summary for a task."""
    record = db.scalar(
        select(SummaryRecordModel)
        .where(SummaryRecordModel.task_id == task_id)
        .order_by(SummaryRecordModel.id.desc())
        .limit(1),
    )
    if record is None:
        return None
    return {
        "task_id": task_id,
        "statistical_summary": record.summary_json.get("statistical_summary", []),
        "validation_issues_summary": record.summary_json.get("validation_issues_summary", {}),
        "anomaly_summary": record.summary_json.get("anomaly_summary", {}),
        "slices": record.slice_json,
        "semantic_schema": record.summary_json.get("semantic_schema", []),
        "token_estimate": record.token_estimate,
        "token_budget": record.token_budget,
        "trimmed": record.trimmed,
    }


def _load_validation_issues(task_id: int, db: Session) -> list[dict[str, object]]:
    records = list(
        db.scalars(
            select(ValidationIssueRecordModel).where(
                ValidationIssueRecordModel.task_id == task_id,
            ),
        ),
    )
    return [
        {
            "sheet_id": r.sheet_id,
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


def _load_anomaly_issues(task_id: int, db: Session) -> list[dict[str, object]]:
    records = list(
        db.scalars(
            select(AnomalyIssueRecordModel).where(
                AnomalyIssueRecordModel.task_id == task_id,
            ),
        ),
    )
    return [
        {
            "sheet_id": r.sheet_id,
            "row_index": r.row_index,
            "col_index": r.col_index,
            "issue_type": r.issue_type,
            "severity": r.severity,
            "reason": r.reason,
            "metric_name": r.metric_name,
            "detection_source": r.detection_source,
            "score": r.score,
        }
        for r in records
    ]


def _summarize_issues(
    issues: list[dict[str, object]],
    kind: str,
) -> dict[str, object]:
    """Aggregate issue counts by severity and type."""
    by_severity: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for issue in issues:
        sev = str(issue.get("severity", "unknown"))
        itype = str(issue.get("issue_type", "unknown"))
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_type[itype] = by_type.get(itype, 0) + 1

    top = sorted(issues, key=lambda i: i.get("severity") == "error", reverse=True)[:5]
    return {
        "total": len(issues),
        "by_severity": by_severity,
        "by_type": by_type,
        "top_issues": top,
    }


def _persist_summary(
    task_id: int,
    context_package: dict[str, object],
    slices: list[dict[str, object]],
    token_estimate: int,
    trimmed: bool,
    db: Session,
) -> None:
    db.execute(
        delete(SummaryRecordModel).where(
            SummaryRecordModel.task_id == task_id,
        ),
    )
    db.add(
        SummaryRecordModel(
            task_id=task_id,
            summary_json=context_package,
            slice_json=slices,
            token_estimate=token_estimate,
            token_budget=DEFAULT_TOKEN_BUDGET,
            trimmed=trimmed,
        ),
    )
    db.commit()