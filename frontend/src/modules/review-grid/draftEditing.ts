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

function columnLabel(index: number) {
  let value = index + 1;
  let label = "";

  while (value > 0) {
    const remainder = (value - 1) % 26;
    label = String.fromCharCode(65 + remainder) + label;
    value = Math.floor((value - 1) / 26);
  }

  return label;
}

function selectionToRange(selection: DraftSelectionRange) {
  return `${columnLabel(selection.startCol)}${selection.startRow + 1}:${columnLabel(selection.endCol)}${selection.endRow + 1}`;
}

function rangeToSelection(range: string): DraftSelectionRange | null {
  const match = /^([A-Z]+)(\d+):([A-Z]+)(\d+)$/i.exec(range);
  if (!match) {
    return null;
  }

  const [, startColLabel, startRowLabel, endColLabel, endRowLabel] = match;
  const toColumnIndex = (label: string) =>
    label
      .toUpperCase()
      .split("")
      .reduce((value, char) => value * 26 + (char.charCodeAt(0) - 64), 0) - 1;

  return {
    startRow: Number(startRowLabel) - 1,
    endRow: Number(endRowLabel) - 1,
    startCol: toColumnIndex(startColLabel),
    endCol: toColumnIndex(endColLabel),
  };
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
    cellTags: cloneMatrix(sheet.cell_tags) as DraftCellTag[][],
    mergeRanges: [...sheet.merge_ranges],
    mergeBlocks: sheet.merge_ranges
      .map((range) => {
        const selection = rangeToSelection(range);
        if (!selection) {
          return null;
        }

        return {
          id: createMergeId(),
          range,
          ...selection,
        };
      })
      .filter((block): block is DraftReviewSheet["mergeBlocks"][number] => block !== null),
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
        range: selectionToRange(selection),
        ...selection,
      },
    ],
    mergeRanges: [...sheet.mergeRanges, selectionToRange(selection)],
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
      alignedGrid[row][col] =
        originalSheet.base_aligned_grid[row][col] ?? alignedGrid[row][col];
      alignedSourceMap[row][col] =
        originalSheet.base_aligned_source_map[row][col] ?? alignedSourceMap[row][col];
      alignedRoles[row][col] =
        originalSheet.base_aligned_cell_roles[row][col] ?? alignedRoles[row][col];
      cellTags[row][col] = "none";
    }
  }

  return {
    ...sheet,
    alignedGrid,
    alignedSourceMap,
    alignedRoles,
    cellTags,
    mergeRanges: sheet.mergeRanges.filter((range) => range !== mergeBlock.range),
    mergeBlocks: sheet.mergeBlocks.filter((block) => block.id !== mergeBlock.id),
  };
}
