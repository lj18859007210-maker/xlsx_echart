"""Review service – thin orchestrator that delegates to grid_builder and structure_version_service."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel

from .grid_builder import build_sheet_payload, build_sheet_payload_paged
from .structure_version_service import (
    apply_snapshot,
    apply_structure_version,
    confirm_structure_version as _confirm_structure_version,
    latest_structure_version,
    preferred_structure_version,
    save_structure_version as _save_structure_version,
)


def _load_task(task_id: int, db: Session) -> TaskRecordModel:
    task = db.scalar(
        select(TaskRecordModel)
        .where(TaskRecordModel.id == task_id)
        .options(
            selectinload(TaskRecordModel.sheets).selectinload(SheetRecordModel.cells),
            selectinload(TaskRecordModel.structure_versions),
        )
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task


def build_task_review(task_id: int, db: Session) -> dict[str, object]:
    task = _load_task(task_id, db)

    sheets_payload = [
        build_sheet_payload(sheet)
        for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]
    preferred_sv = preferred_structure_version(task)
    latest_sv = latest_structure_version(task)
    structure_version_number = 0
    editable_structure_version = 0
    if preferred_sv is not None:
        sheets_payload = apply_snapshot(sheets_payload, preferred_sv, db)
        structure_version_number = preferred_sv.version_number
    if latest_sv is not None:
        editable_structure_version = latest_sv.version_number

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": structure_version_number,
        "editable_structure_version": editable_structure_version,
        "sheets": sheets_payload,
    }


def save_structure_version(
    task_id: int,
    base_structure_version: int,
    request_sheets: list[dict[str, object]],
    db: Session,
) -> dict[str, object]:
    task = _load_task(task_id, db)
    return _save_structure_version(task, base_structure_version, request_sheets, db)


def confirm_structure_version(
    task_id: int,
    structure_version: int,
    db: Session,
) -> dict[str, object]:
    task = _load_task(task_id, db)
    return _confirm_structure_version(task, structure_version, db)


def build_task_review_paged(
    task_id: int,
    sheet_id: int,
    offset: int,
    limit: int,
    db: Session,
) -> dict[str, object]:
    """Build a paginated review payload for a single sheet in a task."""
    task = _load_task(task_id, db)

    sheet = next((s for s in task.sheets if s.id == sheet_id), None)
    if sheet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sheet not found in task",
        )

    sheet_payload = build_sheet_payload_paged(sheet, offset, limit)

    preferred_sv = preferred_structure_version(task)
    if preferred_sv is not None:
        snapshot_sheets = preferred_sv.snapshot_json.get("sheets", [])
        snapshot_by_id = {int(s["sheet_id"]): s for s in snapshot_sheets}
        sv_sheet = snapshot_by_id.get(sheet_id)
        if sv_sheet is not None:
            sheet_payload["merge_ranges"] = sv_sheet.get("merge_ranges", [])
            full_aligned = sv_sheet.get("aligned_grid", [])
            full_roles = sv_sheet.get("aligned_cell_roles", [])
            full_source = sv_sheet.get("aligned_source_map", [])
            full_tags = sv_sheet.get("cell_tags", [])
            if isinstance(full_aligned, list) and isinstance(full_roles, list):
                start = max(0, offset)
                end = min(sheet.row_count, start + limit)
                sheet_payload["rows"] = full_aligned[start:end]
                sheet_payload["roles"] = full_roles[start:end] if full_roles else sheet_payload["roles"]
                sheet_payload["source_map"] = full_source[start:end] if full_source else sheet_payload["source_map"]
                sheet_payload["tags"] = full_tags[start:end] if full_tags else sheet_payload["tags"]

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": preferred_sv.version_number if preferred_sv else 0,
        "editable_structure_version": (
            latest_structure_version(task).version_number
            if latest_structure_version(task)
            else 0
        ),
        "sheet": sheet_payload,
    }




