import { describe, expect, it } from "vitest";

import type { ReviewSheetSnapshot } from "../src/types/review";
import {
  buildDraftSheet,
  mergeDraftSelection,
  splitDraftSelection,
} from "../src/modules/review-grid/draftEditing";

function createSheetSnapshot(): ReviewSheetSnapshot {
  return {
    sheet_id: 7,
    sheet_name: "Sheet A",
    sheet_index: 0,
    row_count: 2,
    col_count: 2,
    is_hidden: false,
    merge_ranges: [],
    raw_cells: [],
    grid_snapshot: [
      ["Region", "Product"],
      ["100", "200"],
    ],
    address_map: [
      ["A1", "B1"],
      ["A2", "B2"],
    ],
    aligned_grid: [
      ["Region", "Product"],
      ["100", "200"],
    ],
    aligned_cell_roles: [
      ["dimension", "dimension"],
      ["measure", "measure"],
    ],
    aligned_source_map: [
      ["A1", "B1"],
      ["A2", "B2"],
    ],
  };
}

describe("draftEditing", () => {
  it("restores original roles and tags when splitting a merged draft block", () => {
    const originalSheet = createSheetSnapshot();
    const mergedSheet = mergeDraftSelection(buildDraftSheet(originalSheet), {
      startRow: 0,
      endRow: 0,
      startCol: 0,
      endCol: 1,
    });

    mergedSheet.cellTags[0][0] = "header";
    mergedSheet.cellTags[0][1] = "header";
    mergedSheet.alignedRoles[0][0] = "measure";
    mergedSheet.alignedRoles[0][1] = "measure";

    const splitSheet = splitDraftSelection(mergedSheet, originalSheet, {
      startRow: 0,
      endRow: 0,
      startCol: 0,
      endCol: 1,
    });

    expect(splitSheet.alignedGrid).toEqual(originalSheet.aligned_grid);
    expect(splitSheet.alignedSourceMap).toEqual(originalSheet.aligned_source_map);
    expect(splitSheet.alignedRoles).toEqual(originalSheet.aligned_cell_roles);
    expect(splitSheet.cellTags).toEqual([
      ["none", "none"],
      ["none", "none"],
    ]);
    expect(splitSheet.mergeBlocks).toHaveLength(0);
  });

  it("rejects a merge selection that overlaps an existing local merge block", () => {
    const originalSheet = createSheetSnapshot();
    const firstMergedSheet = mergeDraftSelection(buildDraftSheet(originalSheet), {
      startRow: 0,
      endRow: 0,
      startCol: 0,
      endCol: 1,
    });

    const attemptedOverlap = mergeDraftSelection(firstMergedSheet, {
      startRow: 0,
      endRow: 1,
      startCol: 1,
      endCol: 1,
    });

    expect(attemptedOverlap.mergeBlocks).toHaveLength(1);
    expect(attemptedOverlap).toEqual(firstMergedSheet);
  });
});
