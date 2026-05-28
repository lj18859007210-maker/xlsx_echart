"""Day 21 chart recommendation orchestration service."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.chart_spec_record import ChartSpecRecordModel
from app.db.models.insight_record import InsightRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.structure_version_service import preferred_structure_version

from .chart_rule_selector import select_chart_types
from .chart_spec_builder import build_chart_spec

_CHART_ALLOWED_STATUSES = frozenset({
    "analyzed",
    "chart_ready",
})


def recommend_charts(
    task_id: int,
    db: Session,
) -> dict[str, object]:
    """Generate chart recommendations for a task — idempotent."""

    # 1. Validate task status
    task = db.scalar(
        select(TaskRecordModel).where(TaskRecordModel.id == task_id),
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found",
        )

    if task.status not in _CHART_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task must be analyzed first (or already chart_ready)",
        )

    # 2. Load structure version
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

    # 3. Load chart_hints from insight
    chart_hints: list[dict[str, object]] = _load_chart_hints(task_id, db)

    # 4. Generate charts per sheet
    all_charts: list[dict[str, object]] = []
    no_chart_reasons: list[str] = []

    for sheet_data in sheets_data:
        sheet_name = str(sheet_data.get("sheet_name", ""))
        aligned_grid = sheet_data.get("aligned_grid", [])
        column_kinds = sheet_data.get("column_kinds", [])
        column_paths = sheet_data.get("column_paths", [])

        if not isinstance(aligned_grid, list) or len(aligned_grid) < 2:
            no_chart_reasons.append(f"Sheet '{sheet_name}': 数据不足")
            continue
        if not isinstance(column_kinds, list) or not column_kinds:
            no_chart_reasons.append(f"Sheet '{sheet_name}': 缺少列类型信息")
            continue

        # Derive column names
        col_names: list[str] = []
        if aligned_grid and aligned_grid[0]:
            for cell in aligned_grid[0]:
                col_names.append(str(cell) if cell is not None else "")
        else:
            for path in column_paths:
                col_names.append(str(path[-1]) if path else "")

        # Select chart types
        rules, no_reason = select_chart_types(
            column_kinds=list(column_kinds),
            column_paths=list(column_paths),
            aligned_grid=aligned_grid,
            chart_hints=chart_hints,
        )

        if no_reason:
            no_chart_reasons.append(f"Sheet '{sheet_name}': {no_reason}")
            continue

        # Build ChartSpec for each rule
        for rule in rules:
            spec = build_chart_spec(
                chart_rule=rule,
                aligned_grid=aligned_grid,
                column_kinds=list(column_kinds),
                column_paths=list(column_paths),
                column_names=col_names,
                sheet_name=sheet_name,
            )
            all_charts.append(spec)

    # 5. Persist
    _persist_charts(task_id, all_charts, db)

    # 6. Update task status
    task.status = "chart_ready"
    db.commit()

    return {
        "task_id": task_id,
        "total": len(all_charts),
        "charts": all_charts,
        "no_chart_reasons": no_chart_reasons,
    }


def get_chart_specs(
    task_id: int,
    db: Session,
) -> dict[str, object] | None:
    """Read persisted chart specs for a task."""
    records = list(
        db.scalars(
            select(ChartSpecRecordModel)
            .where(ChartSpecRecordModel.task_id == task_id)
            .order_by(ChartSpecRecordModel.chart_index),
        ),
    )
    if not records:
        return None

    return {
        "task_id": task_id,
        "total": len(records),
        "charts": [
            {
                "chart_index": r.chart_index,
                "chart_type": r.chart_type,
                "title": r.title,
                "x_field": r.x_field,
                "y_fields": r.y_fields_json,
                "series": r.series_json,
                "highlights": r.highlights_json,
                "source_cells": r.source_cells_json,
                "filter_conditions": "",
                "reason": r.reason,
            }
            for r in records
        ],
    }


def _load_chart_hints(
    task_id: int,
    db: Session,
) -> list[dict[str, object]]:
    insight = db.scalar(
        select(InsightRecordModel)
        .where(InsightRecordModel.task_id == task_id)
        .order_by(InsightRecordModel.id.desc())
        .limit(1),
    )
    if insight is None:
        return []
    return insight.chart_hints_json if isinstance(insight.chart_hints_json, list) else []


def _persist_charts(
    task_id: int,
    charts: list[dict[str, object]],
    db: Session,
) -> None:
    db.execute(
        delete(ChartSpecRecordModel).where(
            ChartSpecRecordModel.task_id == task_id,
        ),
    )
    for idx, chart in enumerate(charts):
        db.add(
            ChartSpecRecordModel(
                task_id=task_id,
                chart_index=idx,
                chart_type=str(chart.get("chart_type", "")),
                title=str(chart.get("title", "")),
                x_field=str(chart.get("x_field", "")),
                y_fields_json=list(chart.get("y_fields", [])),
                series_json=list(chart.get("series", [])),
                highlights_json=list(chart.get("highlights", [])),
                source_cells_json=list(chart.get("source_cells", [])),
                reason=str(chart.get("reason", "")),
            ),
        )
    db.commit()