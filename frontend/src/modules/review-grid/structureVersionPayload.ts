import type {
  DraftReviewSheet,
  StructureVersionSaveRequest,
  TaskReviewResponse,
} from "../../types/review";
import { deriveHeaderParsing } from "./headerSummary";

export function buildStructureVersionSaveRequest(
  payload: TaskReviewResponse,
  draftSheets: Record<number, DraftReviewSheet>,
): StructureVersionSaveRequest {
  return {
    base_structure_version: payload.editable_structure_version,
    sheets: payload.sheets.map((sheet) => {
      const draftSheet = draftSheets[sheet.sheet_id];
      return {
        sheet_id: sheet.sheet_id,
        sheet_name: sheet.sheet_name,
        sheet_index: sheet.sheet_index,
        row_count: sheet.row_count,
        col_count: sheet.col_count,
        is_hidden: sheet.is_hidden,
        merge_ranges: draftSheet?.mergeRanges ?? sheet.merge_ranges,
        aligned_grid: draftSheet?.alignedGrid ?? sheet.aligned_grid,
        aligned_cell_roles: draftSheet?.alignedRoles ?? sheet.aligned_cell_roles,
        aligned_source_map: draftSheet?.alignedSourceMap ?? sheet.aligned_source_map,
        cell_tags: draftSheet?.cellTags ?? sheet.cell_tags,
      };
    }),
  };
}

export function applyDraftSheetsToReview(
  payload: TaskReviewResponse,
  draftSheets: Record<number, DraftReviewSheet>,
  structureVersion: number,
  status: string,
): TaskReviewResponse {
  return {
    ...payload,
    status,
    structure_version: structureVersion,
    editable_structure_version: structureVersion,
    sheets: payload.sheets.map((sheet) => {
      const draftSheet = draftSheets[sheet.sheet_id];
      if (!draftSheet) {
        return sheet;
      }

      const headerParsing = deriveHeaderParsing(draftSheet.alignedGrid, draftSheet.alignedRoles);

      return {
        ...sheet,
        merge_ranges: draftSheet.mergeRanges,
        aligned_grid: draftSheet.alignedGrid,
        aligned_cell_roles: draftSheet.alignedRoles,
        aligned_source_map: draftSheet.alignedSourceMap,
        cell_tags: draftSheet.cellTags,
        ...headerParsing,
      };
    }),
  };
}
