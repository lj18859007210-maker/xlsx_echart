import { useEffect, useMemo, useState } from "react";

import { summarizeHeaderParsing } from "./headerSummary";
import { mergeDraftSelection, splitDraftSelection } from "./draftEditing";
import type {
  DraftCellTag,
  DraftReviewSheet,
  DraftSelectionRange,
  GridPoint,
  ReviewSheetSnapshot,
} from "../../types/review";

function normalizeRange(anchor: GridPoint, focus: GridPoint) {
  return {
    startRow: Math.min(anchor.row, focus.row),
    endRow: Math.max(anchor.row, focus.row),
    startCol: Math.min(anchor.col, focus.col),
    endCol: Math.max(anchor.col, focus.col),
  };
}

export function useDraftEditing(opts: {
  selectedSheetId: number | null;
  selectedSheet: ReviewSheetSnapshot | null;
  draftSheets: Record<number, DraftReviewSheet>;
  setDraftSheets: React.Dispatch<React.SetStateAction<Record<number, DraftReviewSheet>>>;
}) {
  const { selectedSheetId, selectedSheet, draftSheets, setDraftSheets } = opts;

  const [selectionAnchor, setSelectionAnchor] = useState<GridPoint | null>(null);
  const [selectionFocus, setSelectionFocus] = useState<GridPoint | null>(null);

  // Clear selection when switching sheets.
  useEffect(() => {
    setSelectionAnchor(null);
    setSelectionFocus(null);
  }, [selectedSheetId]);

  const selectedRange = useMemo<DraftSelectionRange | null>(() => {
    if (!selectionAnchor || !selectionFocus) {
      return null;
    }

    return normalizeRange(selectionAnchor, selectionFocus);
  }, [selectionAnchor, selectionFocus]);

  const selectedDraftSheet = selectedSheetId ? draftSheets[selectedSheetId] ?? null : null;
  const visibleMergeRanges = selectedDraftSheet?.mergeRanges ?? selectedSheet?.merge_ranges ?? [];
  const headerSummary = selectedSheet ? summarizeHeaderParsing(selectedSheet) : null;

  // --- Helpers ---------------------------------------------------------------

  function updateDraftSheet(
    updater: (currentSheet: DraftReviewSheet) => DraftReviewSheet,
  ) {
    if (!selectedSheetId) {
      return;
    }

    setDraftSheets((current) => {
      const sheet = current[selectedSheetId];
      if (!sheet) {
        return current;
      }

      return {
        ...current,
        [selectedSheetId]: updater(sheet),
      };
    });
  }

  // --- Actions ---------------------------------------------------------------

  function handleCellSelect(point: GridPoint) {
    if (!selectionAnchor) {
      setSelectionAnchor(point);
      setSelectionFocus(point);
      return;
    }

    setSelectionFocus(point);
  }

  function resetSelection() {
    setSelectionAnchor(null);
    setSelectionFocus(null);
  }

  function mergeSelection() {
    if (!selectedRange) {
      return;
    }

    updateDraftSheet((sheet) => mergeDraftSelection(sheet, selectedRange));
  }

  function splitSelection() {
    if (!selectedRange || !selectedSheet) {
      return;
    }

    updateDraftSheet((sheet) => splitDraftSelection(sheet, selectedSheet, selectedRange));
  }

  function markSelection(tag: DraftCellTag) {
    if (!selectedRange || tag === "none") {
      return;
    }

    updateDraftSheet((sheet) => {
      const cellTags = sheet.cellTags.map((row) => [...row]);
      const alignedRoles = sheet.alignedRoles.map((row) => [...row]);

      for (let row = selectedRange.startRow; row <= selectedRange.endRow; row += 1) {
        for (let col = selectedRange.startCol; col <= selectedRange.endCol; col += 1) {
          cellTags[row][col] = tag;
          alignedRoles[row][col] = tag === "header" ? "dimension" : "measure";
        }
      }

      return {
        ...sheet,
        cellTags,
        alignedRoles,
      };
    });
  }

  return {
    selectionAnchor,
    setSelectionAnchor,
    selectionFocus,
    setSelectionFocus,
    selectedRange,
    selectedDraftSheet,
    visibleMergeRanges,
    headerSummary,
    handleCellSelect,
    resetSelection,
    mergeSelection,
    splitSelection,
    markSelection,
  };
}
