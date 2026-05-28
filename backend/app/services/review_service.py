"""Review service – thin orchestrator that delegates to grid_builder and structure_version_service."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel

from .grid_builder import build_sheet_payload
from .structure_version_service import (
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
        sheets_payload = apply_structure_version(sheets_payload, preferred_sv)
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
