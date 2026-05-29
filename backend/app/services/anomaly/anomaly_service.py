"""Day 17-18 anomaly detection orchestration service with IQR support."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.anomaly_issue_record import AnomalyIssueRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.structure_version_service import preferred_structure_version
from app.services.grid_builder import with_header_parsing

from .decline_detector import detect_consecutive_declines
from .growth_rate_detector import detect_growth_rate_anomalies
from .iqr_detector import detect_iqr_outliers
from .negative_zero_detector import detect_negative_zero_anomalies
from .structure_share_detector import detect_structure_share_anomalies

# Day 18: minimum sample size for statistical model
IQR_MIN_SAMPLE = 30


def detect_task_anomalies(
    task_id: int,
    db: Session,
) -> dict[str, object]:
    """Run anomaly detectors with automatic mode switching.

    Day 17: business rule detectors only.
    Day 18: adds IQR when per-column sample size >= 30.
    """
    task = db.scalar(
        select(TaskRecordModel).where(TaskRecordModel.id == task_id),
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status not in ("validated", "formula_gap_acknowledged"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be validated or formula-gap-acknowledged before anomaly detection",
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

    all_issues: list[dict[str, object]] = []
    any_statistical = False

    for sheet_data in sheets_data:
        sheet_id = int(sheet_data.get("sheet_id", 0))
        if "aligned_cell_roles" in sheet_data:
            sheet_data = with_header_parsing(sheet_data)
        aligned_grid = sheet_data.get("aligned_grid", [])
        column_paths = sheet_data.get("column_paths", [])
        column_kinds = sheet_data.get("column_kinds", [])

        if not isinstance(aligned_grid, list) or len(aligned_grid) < 2:
            continue

        # Always run business rule detectors
        detectors: list[tuple[str, object]] = [
            ("growth_rate", detect_growth_rate_anomalies),
            ("decline", detect_consecutive_declines),
            ("negative_zero", detect_negative_zero_anomalies),
            ("structure_share", detect_structure_share_anomalies),
        ]

        # Day 18: check per-column sample size for IQR
        measure_cols = [i for i, k in enumerate(column_kinds) if k == "measure"]
        max_sample = 0
        for col_idx in measure_cols:
            n = _count_valid_cells(aligned_grid, col_idx)
            if n > max_sample:
                max_sample = n

        if max_sample >= IQR_MIN_SAMPLE:
            detectors.append(("iqr", detect_iqr_outliers))
            any_statistical = True

        for _name, detector_fn in detectors:
            sheet_issues = detector_fn(aligned_grid, column_kinds, column_paths)
            for issue in sheet_issues:
                issue["sheet_id"] = sheet_id
                issue["cell_address"] = _format_cell_address(
                    int(issue.get("row_index", 0)),
                    int(issue.get("col_index", 0)),
                )
            all_issues.extend(sheet_issues)

    # Deduplicate
    deduped = _deduplicate_issues(all_issues)

    # Persist
    _persist_anomaly_issues(task_id, deduped, db)

    # Count by source
    rule_hits = sum(
        1 for i in deduped
        if i.get("detection_source") == "business_rule"
    )
    stat_hits = sum(
        1 for i in deduped
        if i.get("detection_source") == "statistical"
    )

    return {
        "task_id": task_id,
        "status": task.status,
        "detection_mode": "hybrid" if any_statistical else "business_rule",
        "anomaly_issue_count": len(deduped),
        "rule_hits": rule_hits,
        "stat_hits": stat_hits,
        "issues": deduped,
    }


def get_anomaly_issues(
    task_id: int,
    db: Session,
) -> list[dict[str, object]]:
    """Read persisted anomaly issues for a task."""
    records = list(
        db.scalars(
            select(AnomalyIssueRecordModel)
            .where(AnomalyIssueRecordModel.task_id == task_id)
            .order_by(
                AnomalyIssueRecordModel.sheet_id,
                AnomalyIssueRecordModel.row_index,
                AnomalyIssueRecordModel.col_index,
            ),
        ),
    )
    return [
        {
            "id": r.id,
            "task_id": r.task_id,
            "sheet_id": r.sheet_id,
            "row_index": r.row_index,
            "col_index": r.col_index,
            "cell_address": _format_cell_address(r.row_index, r.col_index),
            "issue_type": r.issue_type,
            "severity": r.severity,
            "metric_name": r.metric_name,
            "detection_source": r.detection_source,
            "reason": r.reason,
            "score": r.score,
        }
        for r in records
    ]


def _count_valid_cells(grid: list[list], col_idx: int) -> int:
    """Count rows with valid numeric values in a given column."""
    count = 0
    for row_idx in range(1, len(grid)):
        row = grid[row_idx]
        if not isinstance(row, list):
            continue
        try:
            val = row[col_idx]
            if val not in (None, ""):
                float(str(val).replace(",", ""))
                count += 1
        except (IndexError, ValueError, TypeError):
            continue
    return count


def _format_cell_address(row_index: int, col_index: int) -> str:
    col_letter = _column_letter(col_index)
    return f"{col_letter}{row_index + 1}"


def _column_letter(col_index: int) -> str:
    letters = ""
    n = col_index
    while n >= 0:
        letters = chr((n % 26) + 65) + letters
        n = n // 26 - 1
    return letters


def _deduplicate_issues(
    issues: list[dict[str, object]],
) -> list[dict[str, object]]:
    seen: dict[tuple, dict[str, object]] = {}
    for issue in issues:
        key = (
            issue.get("sheet_id"),
            issue.get("row_index"),
            issue.get("col_index"),
            issue.get("issue_type"),
        )
        existing = seen.get(key)
        if existing is None or issue.get("score", 0) > existing.get("score", 0):
            seen[key] = issue
    return list(seen.values())


def _persist_anomaly_issues(
    task_id: int,
    issues: list[dict[str, object]],
    db: Session,
) -> None:
    db.execute(
        delete(AnomalyIssueRecordModel).where(
            AnomalyIssueRecordModel.task_id == task_id,
        ),
    )
    for issue in issues:
        db.add(
            AnomalyIssueRecordModel(
                task_id=task_id,
                sheet_id=int(issue["sheet_id"]),
                row_index=int(issue["row_index"]),
                col_index=int(issue["col_index"]),
                issue_type=str(issue["issue_type"]),
                severity=str(issue["severity"]),
                metric_name=str(issue["metric_name"]),
                detection_source=str(issue.get("detection_source", "business_rule")),
                reason=str(issue["reason"]),
                score=float(issue.get("score", 0)),
            ),
        )
    db.commit()
