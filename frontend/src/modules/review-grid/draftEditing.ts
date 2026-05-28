import type {
  DraftCellTag,
  DraftReviewSheet,
  DraftSelectionRange,
  ReviewSheetSnapshot,
} from "../../types/review";

function cloneMatrix<T>(matrix: T[][]) {
  return matrix.map((row) => [...row]);
}

function createMergeId() {
  return `merge_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function rangesOverlap(
  left: DraftSelectionRange,
  right: DraftSelectionRange,
) {
  return !(
    left.endRow < right.startRow ||
    left.startRow > right.endRow ||
    left.endCol < right.startCol ||
    left.startCol > right.endCol
  );
}

export function buildDraftSheet(sheet: ReviewSheetSnapshot): DraftReviewSheet {
  return {
    sheetId: sheet.sheet_id,
    sheetName: sheet.sheet_name,
    rowCount: sheet.row_count,
    colCount: sheet.col_count,
    alignedGrid: cloneMatrix(sheet.aligned_grid),
    alignedSourceMap: cloneMatrix(sheet.aligned_source_map),
    alignedRoles: cloneMatrix(sheet.aligned_cell_roles),
    cellTags: sheet.aligned_grid.map((row) => row.map(() => "none" as DraftCellTag)),
    mergeBlocks: [],
  };
}

export function mergeDraftSelection(
  sheet: DraftReviewSheet,
  selection: DraftSelectionRange,
): DraftReviewSheet {
  if (sheet.mergeBlocks.some((block) => rangesOverlap(block, selection))) {
    return sheet;
  }

  const alignedGrid = cloneMatrix(sheet.alignedGrid);
  const alignedRoles = cloneMatrix(sheet.alignedRoles);
  const alignedSourceMap = cloneMatrix(sheet.alignedSourceMap);
  const topLeftValue = alignedGrid[selection.startRow][selection.startCol];
  const topLeftRole = alignedRoles[selection.startRow][selection.startCol];
  const topLeftSource = alignedSourceMap[selection.startRow][selection.startCol];

  for (let row = selection.startRow; row <= selection.endRow; row += 1) {
    for (let col = selection.startCol; col <= selection.endCol; col += 1) {
      alignedRoles[row][col] = topLeftRole;
      if (row === selection.startRow && col === selection.startCol) {
        continue;
      }
      alignedGrid[row][col] = null;
      alignedSourceMap[row][col] = topLeftSource;
    }
  }

  alignedGrid[selection.startRow][selection.startCol] = topLeftValue;

  return {
    ...sheet,
    alignedGrid,
    alignedRoles,
    alignedSourceMap,
    mergeBlocks: [
      ...sheet.mergeBlocks,
      {
        id: createMergeId(),
        ...selection,
      },
    ],
  };
}

export function splitDraftSelection(
  sheet: DraftReviewSheet,
  originalSheet: ReviewSheetSnapshot,
  selection: DraftSelectionRange,
): DraftReviewSheet {
  const mergeBlock = sheet.mergeBlocks.find(
    (block) =>
      selection.startRow >= block.startRow &&
      selection.endRow <= block.endRow &&
      selection.startCol >= block.startCol &&
      selection.endCol <= block.endCol,
  );

  if (!mergeBlock) {
    return sheet;
  }

  const alignedGrid = cloneMatrix(sheet.alignedGrid);
  const alignedSourceMap = cloneMatrix(sheet.alignedSourceMap);
  const alignedRoles = cloneMatrix(sheet.alignedRoles);
  const cellTags = cloneMatrix(sheet.cellTags);

  for (let row = mergeBlock.startRow; row <= mergeBlock.endRow; row += 1) {
    for (let col = mergeBlock.startCol; col <= mergeBlock.endCol; col += 1) {
      alignedGrid[row][col] = originalSheet.aligned_grid[row][col] ?? alignedGrid[row][col];
      alignedSourceMap[row][col] =
        originalSheet.aligned_source_map[row][col] ?? alignedSourceMap[row][col];
      alignedRoles[row][col] =
        originalSheet.aligned_cell_roles[row][col] ?? alignedRoles[row][col];
      cellTags[row][col] = "none";
    }
  }

  return {
    ...sheet,
    alignedGrid,
    alignedSourceMap,
    alignedRoles,
    cellTags,
    mergeBlocks: sheet.mergeBlocks.filter((block) => block.id !== mergeBlock.id),
  };
}
