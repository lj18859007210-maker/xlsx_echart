from decimal import Decimal, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models.cell_record import CellRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
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


def _empty_cell_tags(row_count: int, col_count: int) -> list[list[str]]:
    return [["none" for _ in range(col_count)] for _ in range(row_count)]


def _infer_header_row_span(
    aligned_grid: list[list[str | None]],
    aligned_roles: list[list[str]],
) -> int:
    if not aligned_roles or not aligned_grid:
        return 0

    filled_header_grid: list[list[str | None]] = []
    for row in aligned_grid:
        filled_row: list[str | None] = []
        last_value: str | None = None
        for candidate in row:
            if candidate is None or candidate == "":
                filled_row.append(last_value)
            else:
                filled_row.append(candidate)
                last_value = candidate
        filled_header_grid.append(filled_row)

    header_row_span = 1
    for row_index in range(1, len(aligned_roles)):
        previous_values = filled_header_grid[row_index - 1]
        previous_row = aligned_roles[row_index - 1]
        current_row = aligned_roles[row_index]
        should_extend = False

        start_col = 0
        while start_col < len(previous_row):
            end_col = start_col
            while end_col + 1 < len(previous_row):
                same_role = previous_row[end_col + 1] == previous_row[start_col]
                same_value_group = previous_values[end_col + 1] == previous_values[start_col]
                if not same_value_group:
                    break
                end_col += 1

            if end_col > start_col:
                group_role = previous_row[start_col]
                if group_role != "empty":
                    current_group_roles = current_row[start_col : end_col + 1]
                    if any(role == group_role for role in current_group_roles):
                        should_extend = True
                        break

            start_col = end_col + 1

        if not should_extend:
            break

        header_row_span += 1

    return header_row_span


def _build_column_paths(
    aligned_grid: list[list[str | None]],
    aligned_roles: list[list[str]],
    header_row_span: int,
) -> tuple[list[list[str]], list[str], list[int], list[int]]:
    column_paths: list[list[str]] = []
    column_kinds: list[str] = []
    dimension_columns: list[int] = []
    measure_columns: list[int] = []

    if not aligned_grid:
        return column_paths, column_kinds, dimension_columns, measure_columns

    col_count = len(aligned_grid[0])
    header_grid: list[list[str | None]] = []
    for row_index in range(header_row_span):
        header_row: list[str | None] = []
        last_value: str | None = None
        for col_index in range(col_count):
            candidate = aligned_grid[row_index][col_index]
            if candidate is None or candidate == "":
                header_row.append(last_value)
            else:
                header_row.append(candidate)
                last_value = candidate
        header_grid.append(header_row)

    for col_index in range(col_count):
        path: list[str] = []
        for row_index in range(header_row_span):
            candidate = header_grid[row_index][col_index]
            if candidate is None or candidate == "":
                continue
            if not path or path[-1] != candidate:
                path.append(candidate)

        role = "unknown"
        for row_index in range(header_row_span - 1, -1, -1):
            candidate_role = aligned_roles[row_index][col_index]
            if candidate_role != "empty":
                role = candidate_role
                break

        column_paths.append(path)
        column_kinds.append(role)
        if role == "dimension":
            dimension_columns.append(col_index)
        elif role == "measure":
            measure_columns.append(col_index)

    return column_paths, column_kinds, dimension_columns, measure_columns


def _build_sheet_payload(sheet: SheetRecordModel) -> dict[str, object]:
    grid_snapshot, address_map = _build_grid_snapshot(sheet)
    aligned_grid, aligned_roles, aligned_source_map = _build_aligned_snapshot(sheet)
    merge_ranges = sorted({cell.merge_range for cell in sheet.cells if cell.merge_range is not None})
    return _with_header_parsing(
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
        "base_aligned_grid": aligned_grid,
        "base_aligned_cell_roles": aligned_roles,
        "base_aligned_source_map": aligned_source_map,
        "cell_tags": _empty_cell_tags(sheet.row_count, sheet.col_count),
        }
    )


def _with_header_parsing(sheet_payload: dict[str, object]) -> dict[str, object]:
    aligned_grid = sheet_payload["aligned_grid"]
    aligned_roles = sheet_payload["aligned_cell_roles"]
    header_row_span = _infer_header_row_span(aligned_grid, aligned_roles)
    column_paths, column_kinds, dimension_columns, measure_columns = _build_column_paths(
        aligned_grid,
        aligned_roles,
        header_row_span,
    )

    return {
        **sheet_payload,
        "header_row_span": header_row_span,
        "column_paths": column_paths,
        "column_kinds": column_kinds,
        "dimension_columns": dimension_columns,
        "measure_columns": measure_columns,
    }


def _preferred_structure_version(task: TaskRecordModel) -> StructureVersionRecordModel | None:
    if not task.structure_versions:
        return None

    confirmed_versions = [version for version in task.structure_versions if version.is_confirmed]
    if confirmed_versions:
        return max(confirmed_versions, key=lambda item: item.version_number)

    return max(task.structure_versions, key=lambda item: item.version_number)


def _latest_structure_version(task: TaskRecordModel) -> StructureVersionRecordModel | None:
    if not task.structure_versions:
        return None

    return max(task.structure_versions, key=lambda item: item.version_number)


def _apply_structure_version(
    sheets_payload: list[dict[str, object]],
    structure_version: StructureVersionRecordModel,
) -> list[dict[str, object]]:
    snapshot_sheets = structure_version.snapshot_json["sheets"]
    snapshot_by_sheet_id = {sheet["sheet_id"]: sheet for sheet in snapshot_sheets}
    updated_payload: list[dict[str, object]] = []

    for sheet_payload in sheets_payload:
        snapshot_sheet = snapshot_by_sheet_id.get(sheet_payload["sheet_id"])
        if snapshot_sheet is None:
            updated_payload.append(sheet_payload)
            continue

        updated_payload.append(
            _with_header_parsing(
                {
                    **sheet_payload,
                    "merge_ranges": snapshot_sheet["merge_ranges"],
                    "aligned_grid": snapshot_sheet["aligned_grid"],
                    "aligned_cell_roles": snapshot_sheet["aligned_cell_roles"],
                    "aligned_source_map": snapshot_sheet["aligned_source_map"],
                    "cell_tags": snapshot_sheet["cell_tags"],
                }
            )
        )

    return updated_payload


def _count_changed_cells(
    base_sheet: dict[str, object],
    new_sheet: dict[str, object],
) -> int:
    changed_cell_count = 0
    row_count = int(new_sheet["row_count"])
    col_count = int(new_sheet["col_count"])

    base_grid = base_sheet["aligned_grid"]
    base_roles = base_sheet["aligned_cell_roles"]
    base_source_map = base_sheet["aligned_source_map"]
    base_tags = base_sheet["cell_tags"]

    new_grid = new_sheet["aligned_grid"]
    new_roles = new_sheet["aligned_cell_roles"]
    new_source_map = new_sheet["aligned_source_map"]
    new_tags = new_sheet["cell_tags"]

    for row_index in range(row_count):
        for col_index in range(col_count):
            if (
                base_grid[row_index][col_index] != new_grid[row_index][col_index]
                or base_roles[row_index][col_index] != new_roles[row_index][col_index]
                or base_source_map[row_index][col_index] != new_source_map[row_index][col_index]
                or base_tags[row_index][col_index] != new_tags[row_index][col_index]
            ):
                changed_cell_count += 1

    return changed_cell_count


def _build_patch_summary(
    base_sheets: list[dict[str, object]],
    new_sheets: list[dict[str, object]],
) -> dict[str, object]:
    base_by_sheet_id = {sheet["sheet_id"]: sheet for sheet in base_sheets}
    changed_sheet_ids: list[int] = []
    changed_cell_count = 0

    for new_sheet in new_sheets:
        base_sheet = base_by_sheet_id.get(new_sheet["sheet_id"])
        if base_sheet is None:
            changed_sheet_ids.append(int(new_sheet["sheet_id"]))
            changed_cell_count += int(new_sheet["row_count"]) * int(new_sheet["col_count"])
            continue

        sheet_changed_cells = _count_changed_cells(base_sheet, new_sheet)
        if base_sheet["merge_ranges"] != new_sheet["merge_ranges"] or sheet_changed_cells > 0:
            changed_sheet_ids.append(int(new_sheet["sheet_id"]))
            changed_cell_count += sheet_changed_cells

    return {
        "sheet_count": len(new_sheets),
        "changed_sheet_ids": changed_sheet_ids,
        "changed_cell_count": changed_cell_count,
    }


def _validate_structure_version_payload(
    parsed_sheets: list[dict[str, object]],
    request_sheets: list[dict[str, object]],
) -> None:
    parsed_by_sheet_id = {int(sheet["sheet_id"]): sheet for sheet in parsed_sheets}
    request_sheet_ids = {int(sheet["sheet_id"]) for sheet in request_sheets}

    if request_sheet_ids != set(parsed_by_sheet_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Structure version sheets do not match parsed task sheets",
        )

    for request_sheet in request_sheets:
        parsed_sheet = parsed_by_sheet_id[int(request_sheet["sheet_id"])]
        row_count = int(request_sheet["row_count"])
        col_count = int(request_sheet["col_count"])
        if row_count != int(parsed_sheet["row_count"]) or col_count != int(parsed_sheet["col_count"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Structure version dimensions do not match parsed task sheets",
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
        _build_sheet_payload(sheet) for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]
    preferred_structure_version = _preferred_structure_version(task)
    latest_structure_version = _latest_structure_version(task)
    structure_version_number = 0
    editable_structure_version = 0
    if preferred_structure_version is not None:
        sheets_payload = _apply_structure_version(sheets_payload, preferred_structure_version)
        structure_version_number = preferred_structure_version.version_number
    if latest_structure_version is not None:
        editable_structure_version = latest_structure_version.version_number

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
    latest_structure_version = _latest_structure_version(task)
    current_editable_version = latest_structure_version.version_number if latest_structure_version else 0
    base_sheets = [
        _build_sheet_payload(sheet) for sheet in sorted(task.sheets, key=lambda item: item.sheet_index)
    ]
    if latest_structure_version is not None:
        base_sheets = _apply_structure_version(base_sheets, latest_structure_version)

    if current_editable_version != base_structure_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Structure version is out of date",
        )

    _validate_structure_version_payload(base_sheets, request_sheets)

    next_version_number = base_structure_version + 1
    patch_summary = _build_patch_summary(base_sheets, request_sheets)
    structure_version = StructureVersionRecordModel(
        task_id=task.id,
        version_number=next_version_number,
        snapshot_json={"sheets": request_sheets},
        patch_summary_json=patch_summary,
        is_confirmed=False,
    )
    db.add(structure_version)
    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": next_version_number,
        "patch_summary": patch_summary,
    }


def confirm_structure_version(task_id: int, structure_version: int, db: Session) -> dict[str, object]:
    task = _load_task(task_id, db)
    target_version = next(
        (
            version
            for version in task.structure_versions
            if version.version_number == structure_version
        ),
        None,
    )
    if target_version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Structure version not found",
        )

    for version in task.structure_versions:
        version.is_confirmed = version.version_number == structure_version

    task.status = "confirmed"
    db.commit()

    return {
        "task_id": task.id,
        "status": task.status,
        "structure_version": structure_version,
        "confirmed_structure_version": structure_version,
    }
