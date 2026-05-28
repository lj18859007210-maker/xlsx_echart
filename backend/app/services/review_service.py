from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.cell_record import CellRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel


def _build_grid_snapshot(sheet: SheetRecordModel) -> tuple[list[list[str | None]], list[list[str]]]:
    grid_snapshot: list[list[str | None]] = [
        [None for _ in range(sheet.col_count)] for _ in range(sheet.row_count)
    ]
    address_map: list[list[str]] = [
        ["" for _ in range(sheet.col_count)] for _ in range(sheet.row_count)
    ]

    for cell in sorted(sheet.cells, key=lambda item: (item.row_index, item.col_index)):
        grid_snapshot[cell.row_index - 1][cell.col_index - 1] = cell.raw_value
        address_map[cell.row_index - 1][cell.col_index - 1] = cell.address

    return grid_snapshot, address_map


def _looks_numeric(value: str | None) -> bool:
    if value is None:
        return False

    try:
        Decimal(value.replace(",", ""))
        return True
    except (InvalidOperation, AttributeError):
        return False


def _classify_cell(cell: CellRecordModel, top_left_value: str | None = None) -> str:
    candidate_value = cell.raw_value if top_left_value is None else top_left_value

    if candidate_value is None or candidate_value == "":
        return "empty"

    if cell.value_type in {"n", "f"} or _looks_numeric(candidate_value):
        return "measure"

    if cell.value_type in {"s", "inlineStr"}:
        return "dimension"

    return "unknown"


def _cells_by_address(sheet: SheetRecordModel) -> dict[str, CellRecordModel]:
    return {cell.address: cell for cell in sheet.cells}


def _build_aligned_snapshot(
    sheet: SheetRecordModel,
) -> tuple[list[list[str | None]], list[list[str]], list[list[str | None]]]:
    aligned_grid: list[list[str | None]] = [
        [None for _ in range(sheet.col_count)] for _ in range(sheet.row_count)
    ]
    aligned_roles: list[list[str]] = [
        ["unknown" for _ in range(sheet.col_count)] for _ in range(sheet.row_count)
    ]
    aligned_source_map: list[list[str | None]] = [
        [None for _ in range(sheet.col_count)] for _ in range(sheet.row_count)
    ]

    cells = sorted(sheet.cells, key=lambda item: (item.row_index, item.col_index))
    cell_lookup = _cells_by_address(sheet)
    processed_addresses: set[str] = set()

    for cell in cells:
        if cell.address in processed_addresses:
            continue

        if cell.merge_range:
            merge_addresses = [
                candidate.address
                for candidate in cells
                if candidate.merge_range == cell.merge_range
            ]
            top_left_cell = cell_lookup.get(cell.merge_range.split(":")[0], cell)
            role = _classify_cell(top_left_cell, top_left_cell.raw_value)

            for merge_address in merge_addresses:
                merge_cell = cell_lookup[merge_address]
                row_index = merge_cell.row_index - 1
                col_index = merge_cell.col_index - 1

                if role == "dimension":
                    aligned_grid[row_index][col_index] = top_left_cell.raw_value
                    aligned_source_map[row_index][col_index] = top_left_cell.address
                elif role == "measure":
                    if merge_cell.address == top_left_cell.address:
                        aligned_grid[row_index][col_index] = top_left_cell.raw_value
                        aligned_source_map[row_index][col_index] = top_left_cell.address
                    else:
                        aligned_grid[row_index][col_index] = None
                        aligned_source_map[row_index][col_index] = merge_cell.address
                else:
                    aligned_grid[row_index][col_index] = merge_cell.raw_value
                    aligned_source_map[row_index][col_index] = merge_cell.address

                aligned_roles[row_index][col_index] = role
                processed_addresses.add(merge_cell.address)
            continue

        row_index = cell.row_index - 1
        col_index = cell.col_index - 1
        role = _classify_cell(cell)
        aligned_grid[row_index][col_index] = cell.raw_value
        aligned_roles[row_index][col_index] = role
        aligned_source_map[row_index][col_index] = cell.address
        processed_addresses.add(cell.address)

    return aligned_grid, aligned_roles, aligned_source_map


def build_task_review(task_id: int, db: Session) -> dict[str, object]:
    task = db.scalar(
        select(TaskRecordModel)
        .where(TaskRecordModel.id == task_id)
        .options(selectinload(TaskRecordModel.sheets).selectinload(SheetRecordModel.cells))
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    sheets_payload: list[dict[str, object]] = []
    for sheet in sorted(task.sheets, key=lambda item: item.sheet_index):
        grid_snapshot, address_map = _build_grid_snapshot(sheet)
        aligned_grid, aligned_roles, aligned_source_map = _build_aligned_snapshot(sheet)
        merge_ranges = sorted({cell.merge_range for cell in sheet.cells if cell.merge_range is not None})

        sheets_payload.append(
            {
                "sheet_id": sheet.id,
                "sheet_name": sheet.sheet_name,
                "sheet_index": sheet.sheet_index,
                "row_count": sheet.row_count,
                "col_count": sheet.col_count,
                "is_hidden": sheet.is_hidden,
                "merge_ranges": merge_ranges,
                "raw_cells": [
                    {
                        "address": cell.address,
                        "row_index": cell.row_index,
                        "col_index": cell.col_index,
                        "raw_value": cell.raw_value,
                        "normalized_value": cell.normalized_value,
                        "value_type": cell.value_type,
                        "is_merged": cell.is_merged,
                        "merge_range": cell.merge_range,
                    }
                    for cell in sorted(sheet.cells, key=lambda item: (item.row_index, item.col_index))
                ],
                "grid_snapshot": grid_snapshot,
                "address_map": address_map,
                "aligned_grid": aligned_grid,
                "aligned_cell_roles": aligned_roles,
                "aligned_source_map": aligned_source_map,
            }
        )

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": 0,
        "sheets": sheets_payload,
    }
