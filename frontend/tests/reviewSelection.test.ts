import { describe, expect, it } from "vitest";

import { selectReviewSheet } from "../src/modules/review-grid/reviewSelection";

describe("reviewSelection", () => {
  it("clears the current selection when switching to another sheet", () => {
    expect(
      selectReviewSheet(
        {
          selectedSheetId: 11,
          selectionAnchor: { row: 0, col: 0 },
          selectionFocus: { row: 1, col: 1 },
        },
        12,
      ),
    ).toEqual({
      selectedSheetId: 12,
      selectionAnchor: null,
      selectionFocus: null,
    });
  });
});
