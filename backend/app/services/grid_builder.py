import re
"""Grid construction, cell classification, and header parsing for review payloads."""

from decimal import Decimal, InvalidOperation

from app.db.models.cell_record import CellRecordModel
from app.db.models.sheet_record import SheetRecordModel


def looks_numeric(value: str | None) -> bool:
    """Return True when *value* can be interpreted as a numeric string."""
    if value is None:
        return False

    try:
        Decimal(value.replace(",", ""))
        return True
    except (InvalidOperation, AttributeError):
        return False


def classify_cell(cell: CellRecordModel, top_left_value: str | None = None) -> str:
    """Classify a cell as ``dimension``, ``measure``, ``empty``, or ``unknown``."""
    candidate_value = cell.raw_value if top_left_value is None else top_left_value

    if candidate_value is None or candidate_value == "":
        return "empty"

    if cell.value_type in {"n", "f"} or looks_numeric(candidate_value):
        return "measure"

    if cell.value_type in {"s", "inlineStr"}:
        return "dimension"

    return "unknown"


def cells_by_address(sheet: SheetRecordModel) -> dict[str, CellRecordModel]:
    """Build an address-keyed lookup for every cell in *sheet*."""
    return {cell.address: cell for cell in sheet.cells}


def build_grid_snapshot(
    sheet: SheetRecordModel,
) -> tuple[list[list[str | None]], list[list[str]]]:
    """Return ``(grid_snapshot, address_map)`` from the raw cell rows."""
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


def build_aligned_snapshot(
    sheet: SheetRecordModel,
) -> tuple[list[list[str | None]], list[list[str]], list[list[str | None]]]:
    """Return ``(aligned_grid, aligned_roles, aligned_source_map)``.

    Merged cells are expanded according to their classified role: dimension
    merges propagate the top-left value, measure merges keep the value only in
    the top-left cell, and unknown merges preserve each cell's own value.
    """
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
    cell_lookup = cells_by_address(sheet)
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
            role = classify_cell(top_left_cell, top_left_cell.raw_value)

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
        role = classify_cell(cell)
        aligned_grid[row_index][col_index] = cell.raw_value
        aligned_roles[row_index][col_index] = role
        aligned_source_map[row_index][col_index] = cell.address
        processed_addresses.add(cell.address)

    return aligned_grid, aligned_roles, aligned_source_map


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

def infer_header_row_span(
    aligned_grid: list[list[str | None]],
    aligned_roles: list[list[str]],
) -> int:
    """Heuristically determine how many leading rows belong to the header.

    The algorithm forward-fills empty cells, then checks whether the next row
    continues the same dimension/measure grouping pattern.
    """
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



def _infer_kind_from_data(
    aligned_grid: list[list[str | None]],
    col_index: int,
    header_row_span: int,
) -> str | None:
    """Infer column kind from data values (numeric detection)."""
    numeric_count = 0
    total_count = 0
    numeric_pattern = re.compile(r'^-?\d+(\.\d+)?$')
    for row_index in range(header_row_span, len(aligned_grid)):
        val = aligned_grid[row_index][col_index]
        if val is None or str(val).strip() == '':
            continue
        total_count += 1
        if numeric_pattern.match(str(val).strip()):
            numeric_count += 1
    if total_count > 0 and numeric_count / total_count >= 0.6:
        return 'measure'
    return None

def build_column_paths(
    aligned_grid: list[list[str | None]],
    aligned_roles: list[list[str]],
    header_row_span: int,
) -> tuple[list[list[str]], list[str], list[int], list[int]]:
    """Build per-column path arrays and classify each column as dimension/measure."""
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

        # Data-driven override: if role is "dimension" but column values are numeric, treat as "measure"
        if role == "dimension":
            inferred = _infer_kind_from_data(aligned_grid, col_index, header_row_span)
            if inferred == "measure":
                role = "measure"

        column_paths.append(path)
        column_kinds.append(role)
        if role == "dimension":
            dimension_columns.append(col_index)
        elif role == "measure":
            measure_columns.append(col_index)

    return column_paths, column_kinds, dimension_columns, measure_columns


def with_header_parsing(sheet_payload: dict[str, object]) -> dict[str, object]:
    """Augment a sheet payload dict with header parsing metadata."""
    aligned_grid = sheet_payload["aligned_grid"]
    aligned_roles = sheet_payload["aligned_cell_roles"]
    header_row_span = infer_header_row_span(aligned_grid, aligned_roles)
    column_paths, column_kinds, dimension_columns, measure_columns = build_column_paths(
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


def empty_cell_tags(row_count: int, col_count: int) -> list[list[str]]:
    """Return a ``row_count × col_count`` matrix filled with ``"none"``."""
    return [["none" for _ in range(col_count)] for _ in range(row_count)]


def build_sheet_payload(sheet: SheetRecordModel) -> dict[str, object]:
    """Build the full review payload dict for a single sheet."""
    grid_snapshot, address_map = build_grid_snapshot(sheet)
    aligned_grid, aligned_roles, aligned_source_map = build_aligned_snapshot(sheet)
    merge_ranges = sorted({cell.merge_range for cell in sheet.cells if cell.merge_range is not None})
    return with_header_parsing(
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
            "cell_tags": empty_cell_tags(sheet.row_count, sheet.col_count),
        }
    )
