from pydantic import BaseModel


class RawCellItem(BaseModel):
    address: str
    row_index: int
    col_index: int
    raw_value: str | None
    normalized_value: str | None
    value_type: str
    is_merged: bool
    merge_range: str | None


class ReviewSheetSnapshot(BaseModel):
    sheet_id: int
    sheet_name: str
    sheet_index: int
    row_count: int
    col_count: int
    is_hidden: bool
    merge_ranges: list[str]
    raw_cells: list[RawCellItem]
    grid_snapshot: list[list[str | None]]
    address_map: list[list[str]]
    aligned_grid: list[list[str | None]]
    aligned_cell_roles: list[list[str]]
    aligned_source_map: list[list[str | None]]
    base_aligned_grid: list[list[str | None]]
    base_aligned_cell_roles: list[list[str]]
    base_aligned_source_map: list[list[str | None]]
    cell_tags: list[list[str]]
    header_row_span: int
    column_paths: list[list[str]]
    column_kinds: list[str]
    dimension_columns: list[int]
    measure_columns: list[int]


class TaskReviewResponse(BaseModel):
    task_id: int
    status: str
    structure_version: int
    editable_structure_version: int
    sheets: list[ReviewSheetSnapshot]


class StructureVersionSheetInput(BaseModel):
    sheet_id: int
    sheet_name: str
    sheet_index: int
    row_count: int
    col_count: int
    is_hidden: bool
    merge_ranges: list[str]
    aligned_grid: list[list[str | None]]
    aligned_cell_roles: list[list[str]]
    aligned_source_map: list[list[str | None]]
    cell_tags: list[list[str]]


class SaveStructureVersionRequest(BaseModel):
    base_structure_version: int
    sheets: list[StructureVersionSheetInput]


class StructureVersionSaveResponse(BaseModel):
    task_id: int
    status: str
    structure_version: int
    patch_summary: dict[str, object]


class ConfirmStructureVersionRequest(BaseModel):
    structure_version: int


class ConfirmStructureVersionResponse(BaseModel):
    task_id: int
    status: str
    structure_version: int
    confirmed_structure_version: int
