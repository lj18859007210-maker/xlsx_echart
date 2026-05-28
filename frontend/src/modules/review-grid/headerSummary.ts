import type { ReviewSheetSnapshot } from "../../types/review";

function inferHeaderRowSpan(
  alignedGrid: Array<Array<string | null>>,
  alignedRoles: Array<Array<string>>,
) {
  if (alignedGrid.length === 0 || alignedRoles.length === 0) {
    return 0;
  }

  const filledHeaderGrid = alignedGrid.map((row) => {
    let lastValue: string | null = null;
    return row.map((candidate) => {
      if (candidate === null || candidate === "") {
        return lastValue;
      }
      lastValue = candidate;
      return candidate;
    });
  });

  let headerRowSpan = 1;
  for (let rowIndex = 1; rowIndex < alignedRoles.length; rowIndex += 1) {
    const previousValues = filledHeaderGrid[rowIndex - 1];
    const previousRow = alignedRoles[rowIndex - 1];
    const currentRow = alignedRoles[rowIndex];
    let shouldExtend = false;

    let startCol = 0;
    while (startCol < previousRow.length) {
      let endCol = startCol;
      while (endCol + 1 < previousRow.length) {
        const sameValueGroup = previousValues[endCol + 1] === previousValues[startCol];
        if (!sameValueGroup) {
          break;
        }
        endCol += 1;
      }

      if (endCol > startCol) {
        const groupRole = previousRow[startCol];
        if (groupRole !== "empty") {
          const currentGroupRoles = currentRow.slice(startCol, endCol + 1);
          if (currentGroupRoles.some((role) => role === groupRole)) {
            shouldExtend = true;
            break;
          }
        }
      }

      startCol = endCol + 1;
    }

    if (!shouldExtend) {
      break;
    }

    headerRowSpan += 1;
  }

  return headerRowSpan;
}

function buildColumnPaths(
  alignedGrid: Array<Array<string | null>>,
  alignedRoles: Array<Array<string>>,
  headerRowSpan: number,
) {
  if (alignedGrid.length === 0) {
    return {
      columnPaths: [] as Array<Array<string>>,
      columnKinds: [] as string[],
      dimensionColumns: [] as number[],
      measureColumns: [] as number[],
    };
  }

  const colCount = alignedGrid[0].length;
  const headerGrid = alignedGrid.slice(0, headerRowSpan).map((row) => {
    let lastValue: string | null = null;
    return row.map((candidate) => {
      if (candidate === null || candidate === "") {
        return lastValue;
      }
      lastValue = candidate;
      return candidate;
    });
  });

  const columnPaths: Array<Array<string>> = [];
  const columnKinds: string[] = [];
  const dimensionColumns: number[] = [];
  const measureColumns: number[] = [];

  for (let colIndex = 0; colIndex < colCount; colIndex += 1) {
    const path: string[] = [];
    for (let rowIndex = 0; rowIndex < headerRowSpan; rowIndex += 1) {
      const candidate = headerGrid[rowIndex][colIndex];
      if (candidate === null || candidate === "") {
        continue;
      }
      if (path[path.length - 1] !== candidate) {
        path.push(candidate);
      }
    }

    let role = "unknown";
    for (let rowIndex = headerRowSpan - 1; rowIndex >= 0; rowIndex -= 1) {
      const candidateRole = alignedRoles[rowIndex][colIndex];
      if (candidateRole !== "empty") {
        role = candidateRole;
        break;
      }
    }

    columnPaths.push(path);
    columnKinds.push(role);
    if (role === "dimension") {
      dimensionColumns.push(colIndex);
    } else if (role === "measure") {
      measureColumns.push(colIndex);
    }
  }

  return {
    columnPaths,
    columnKinds,
    dimensionColumns,
    measureColumns,
  };
}

export function deriveHeaderParsing(
  alignedGrid: Array<Array<string | null>>,
  alignedRoles: Array<Array<string>>,
) {
  const headerRowSpan = inferHeaderRowSpan(alignedGrid, alignedRoles);
  const { columnPaths, columnKinds, dimensionColumns, measureColumns } = buildColumnPaths(
    alignedGrid,
    alignedRoles,
    headerRowSpan,
  );

  return {
    header_row_span: headerRowSpan,
    column_paths: columnPaths,
    column_kinds: columnKinds,
    dimension_columns: dimensionColumns,
    measure_columns: measureColumns,
  };
}

export function summarizeHeaderParsing(sheet: ReviewSheetSnapshot) {
  return {
    headerRowSpan: sheet.header_row_span,
    dimensionCount: sheet.dimension_columns.length,
    measureCount: sheet.measure_columns.length,
    previewPaths: sheet.column_paths.slice(0, 3).map((path) => path.join(" > ")),
  };
}
