import { describe, expect, it } from "vitest";

import type { ReviewSheetSnapshot } from "../src/types/review";
import {
  buildDraftSheet,
  mergeDraftSelection,
  splitDraftSelection,
} from "../src/modules/review-grid/draftEditing";
import {
  applyDraftSheetsToReview,
  buildStructureVersionSaveRequest,
} from "../src/modules/review-grid/structureVersionPayload";
import {
  deriveHeaderParsing,
  summarizeHeaderParsing,
} from "../src/modules/review-grid/headerSummary";

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
    base_aligned_grid: [
      ["Region", "Product"],
      ["100", "200"],
    ],
    base_aligned_cell_roles: [
      ["dimension", "dimension"],
      ["measure", "measure"],
    ],
    base_aligned_source_map: [
      ["A1", "B1"],
      ["A2", "B2"],
    ],
    cell_tags: [
      ["none", "none"],
      ["none", "none"],
    ],
    header_row_span: 1,
    column_paths: [["Region"], ["Product"]],
    column_kinds: ["dimension", "dimension"],
    dimension_columns: [0, 1],
    measure_columns: [],
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

  it("builds a save request from draft sheets with current tags and merge ranges", () => {
    const originalSheet = createSheetSnapshot();
    const draftSheet = buildDraftSheet(originalSheet);

    draftSheet.cellTags[0][0] = "header";
    draftSheet.cellTags[0][1] = "header";
    draftSheet.cellTags[1][0] = "data";
    draftSheet.cellTags[1][1] = "data";

    const request = buildStructureVersionSaveRequest(
      {
        task_id: 7,
        status: "waiting_confirm",
        structure_version: 0,
        editable_structure_version: 2,
        sheets: [originalSheet],
      },
      {
        7: draftSheet,
      },
    );

    expect(request.base_structure_version).toBe(2);
    expect(request.sheets).toEqual([
      {
        sheet_id: 7,
        sheet_name: "Sheet A",
        sheet_index: 0,
        row_count: 2,
        col_count: 2,
        is_hidden: false,
        merge_ranges: [],
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
        cell_tags: [
          ["header", "header"],
          ["data", "data"],
        ],
      },
    ]);
  });

  it("applies draft sheets back onto the review payload after save", () => {
    const originalSheet = createSheetSnapshot();
    const draftSheet = buildDraftSheet(originalSheet);
    draftSheet.cellTags[0][0] = "header";
    draftSheet.cellTags[0][1] = "header";

    const updatedPayload = applyDraftSheetsToReview(
      {
        task_id: 7,
        status: "waiting_confirm",
        structure_version: 0,
        editable_structure_version: 0,
        sheets: [originalSheet],
      },
      {
        7: draftSheet,
      },
      1,
      "confirmed",
    );

    expect(updatedPayload.structure_version).toBe(1);
    expect(updatedPayload.editable_structure_version).toBe(1);
    expect(updatedPayload.status).toBe("confirmed");
    expect(updatedPayload.sheets[0].cell_tags).toEqual([
      ["header", "header"],
      ["none", "none"],
    ]);
    expect(updatedPayload.sheets[0].aligned_grid).toEqual(draftSheet.alignedGrid);
    expect(updatedPayload.sheets[0].header_row_span).toBe(1);
  });

  it("can split a persisted merge range after reloading the review payload", () => {
    const persistedSheet: ReviewSheetSnapshot = {
      ...createSheetSnapshot(),
      merge_ranges: ["A1:B1"],
      aligned_grid: [
        ["Region", null],
        ["100", "200"],
      ],
      aligned_cell_roles: [
        ["dimension", "dimension"],
        ["measure", "measure"],
      ],
      aligned_source_map: [
        ["A1", "A1"],
        ["A2", "B2"],
      ],
    };

    const reloadedDraft = buildDraftSheet(persistedSheet);
    const splitSheet = splitDraftSelection(reloadedDraft, persistedSheet, {
      startRow: 0,
      endRow: 0,
      startCol: 0,
      endCol: 1,
    });

    expect(splitSheet.alignedGrid).toEqual(persistedSheet.base_aligned_grid);
    expect(splitSheet.alignedSourceMap).toEqual(persistedSheet.base_aligned_source_map);
    expect(splitSheet.alignedRoles).toEqual(persistedSheet.base_aligned_cell_roles);
    expect(splitSheet.mergeRanges).toEqual([]);
  });

  it("summarizes header parsing metadata for the review sidebar", () => {
    const summary = summarizeHeaderParsing({
      ...createSheetSnapshot(),
      header_row_span: 2,
      column_paths: [["Region"], ["Q1", "Revenue"]],
      column_kinds: ["dimension", "measure"],
      dimension_columns: [0],
      measure_columns: [1],
    });

    expect(summary).toEqual({
      headerRowSpan: 2,
      dimensionCount: 1,
      measureCount: 1,
      previewPaths: ["Region", "Q1 > Revenue"],
    });
  });

  it("derives fresh header parsing metadata after local draft changes", () => {
    const draftSheet = buildDraftSheet(createSheetSnapshot());
    draftSheet.alignedGrid = [
      ["Q1", "Q1"],
      ["Revenue", "Cost"],
    ];
    draftSheet.alignedRoles = [
      ["dimension", "dimension"],
      ["measure", "measure"],
    ];

    expect(deriveHeaderParsing(draftSheet.alignedGrid, draftSheet.alignedRoles)).toEqual({
      header_row_span: 1,
      column_paths: [["Q1"], ["Q1"]],
      column_kinds: ["dimension", "dimension"],
      dimension_columns: [0, 1],
      measure_columns: [],
    });
  });
});
