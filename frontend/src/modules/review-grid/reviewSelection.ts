import type { GridPoint } from "../../types/review";

export type ReviewSelectionState = {
  selectedSheetId: number | null;
  selectionAnchor: GridPoint | null;
  selectionFocus: GridPoint | null;
};

export function selectReviewSheet(
  state: ReviewSelectionState,
  nextSheetId: number,
): ReviewSelectionState {
  return {
    ...state,
    selectedSheetId: nextSheetId,
    selectionAnchor: null,
    selectionFocus: null,
  };
}
