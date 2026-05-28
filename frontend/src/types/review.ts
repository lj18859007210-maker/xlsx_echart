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
};

export type TaskReviewResponse = {
  task_id: number;
  status: string;
  structure_version: number;
  sheets: ReviewSheetSnapshot[];
};

export type DraftCellTag = "none" | "header" | "data";

export type DraftMergeBlock = {
  id: string;
  startRow: number;
  endRow: number;
  startCol: number;
  endCol: number;
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
