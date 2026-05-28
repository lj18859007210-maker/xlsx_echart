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


class TaskReviewResponse(BaseModel):
    task_id: int
    status: str
    structure_version: int
    sheets: list[ReviewSheetSnapshot]
