export type RawCellItem = {
  address: string;
  row_index: number;
  col_index: number;
  raw_value: string | null;
  normalized_value: string | null;
  value_type: string;
  is_merged: boolean;
  merge_range: string | null;
};

export type ReviewSheetSnapshot = {
  sheet_id: number;
  sheet_name: string;
  sheet_index: number;
  row_count: number;
  col_count: number;
  is_hidden: boolean;
  merge_ranges: string[];
  raw_cells: RawCellItem[];
  grid_snapshot: Array<Array<string | null>>;
  address_map: Array<Array<string>>;
  aligned_grid: Array<Array<string | null>>;
  aligned_cell_roles: Array<Array<string>>;
  aligned_source_map: Array<Array<string | null>>;
  base_aligned_grid: Array<Array<string | null>>;
  base_aligned_cell_roles: Array<Array<string>>;
  base_aligned_source_map: Array<Array<string | null>>;
  cell_tags: Array<Array<string>>;
  header_row_span: number;
  column_paths: Array<Array<string>>;
  column_kinds: string[];
  dimension_columns: number[];
  measure_columns: number[];
};

export type TaskReviewResponse = {
  task_id: number;
  status: string;
  structure_version: number;
  editable_structure_version: number;
  sheets: ReviewSheetSnapshot[];
};

export type DraftCellTag = "none" | "header" | "data";

export type DraftMergeBlock = {
  id: string;
  startRow: number;
  endRow: number;
  startCol: number;
  endCol: number;
  range: string;
};

export type DraftReviewSheet = {
  sheetId: number;
  sheetName: string;
  rowCount: number;
  colCount: number;
  alignedGrid: Array<Array<string | null>>;
  alignedSourceMap: Array<Array<string | null>>;
  alignedRoles: Array<Array<string>>;
  cellTags: Array<Array<DraftCellTag>>;
  mergeRanges: string[];
  mergeBlocks: DraftMergeBlock[];
};

export type GridPoint = {
  row: number;
  col: number;
};

export type DraftSelectionRange = {
  startRow: number;
  endRow: number;
  startCol: number;
  endCol: number;
};

export type StructureVersionSheetPayload = {
  sheet_id: number;
  sheet_name: string;
  sheet_index: number;
  row_count: number;
  col_count: number;
  is_hidden: boolean;
  merge_ranges: string[];
  aligned_grid: Array<Array<string | null>>;
  aligned_cell_roles: Array<Array<string>>;
  aligned_source_map: Array<Array<string | null>>;
  cell_tags: Array<Array<string>>;
};

export type StructureVersionSaveRequest = {
  base_structure_version: number;
  sheets: StructureVersionSheetPayload[];
};

export type StructureVersionSaveResponse = {
  task_id: number;
  status: string;
  structure_version: number;
  patch_summary: {
    sheet_count: number;
    changed_sheet_ids: number[];
    changed_cell_count: number;
  };
};

export type ConfirmStructureVersionRequest = {
  structure_version: number;
};

export type ConfirmStructureVersionResponse = {
  task_id: number;
  status: string;
  structure_version: number;
  confirmed_structure_version: number;
};
