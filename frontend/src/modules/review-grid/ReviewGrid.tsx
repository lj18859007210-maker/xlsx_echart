import type { DraftCellTag, DraftReviewSheet, GridPoint, ReviewSheetSnapshot } from "../../types/review";

type ReviewGridProps = {
  sheet: ReviewSheetSnapshot;
  draftSheet?: DraftReviewSheet | null;
  mode: "raw" | "aligned";
  selectedRange?: {
    startRow: number;
    endRow: number;
    startCol: number;
    endCol: number;
  } | null;
  onCellSelect?: (point: GridPoint) => void;
};

function getCellTone(role: string, value: string | null, tag: DraftCellTag = "none") {
  if (tag === "header") {
    return "is-header";
  }

  if (tag === "data") {
    return "is-data";
  }

  if (modeledEmpty(role, value)) {
    return "is-empty";
  }

  if (role === "dimension") {
    return "is-dimension";
  }

  if (role === "measure") {
    return "is-measure";
  }

  return "is-unknown";
}

function modeledEmpty(role: string, value: string | null) {
  return role === "empty" || value === null || value === "";
}

function isSelected(
  selectedRange: ReviewGridProps["selectedRange"],
  rowIndex: number,
  colIndex: number,
) {
  if (!selectedRange) {
    return false;
  }

  return (
    rowIndex >= selectedRange.startRow &&
    rowIndex <= selectedRange.endRow &&
    colIndex >= selectedRange.startCol &&
    colIndex <= selectedRange.endCol
  );
}

export function ReviewGrid({
  sheet,
  draftSheet,
  mode,
  selectedRange,
  onCellSelect,
}: ReviewGridProps) {
  const values =
    mode === "raw" ? sheet.grid_snapshot : draftSheet?.alignedGrid ?? sheet.aligned_grid;
  const sourceMap =
    mode === "raw" ? sheet.address_map : draftSheet?.alignedSourceMap ?? sheet.aligned_source_map;
  const roles =
    mode === "raw"
      ? values.map((row) => row.map((value) => (value === null ? "empty" : "raw")))
      : draftSheet?.alignedRoles ?? sheet.aligned_cell_roles;
  const tags =
    mode === "raw"
      ? values.map((row) => row.map(() => "none" as DraftCellTag))
      : draftSheet?.cellTags ??
        values.map((row) => row.map(() => "none" as DraftCellTag));

  return (
    <div className="review-grid-shell">
      <div className="review-grid-header">
        <div>
          <p className="mini-label">网格视图</p>
          <h3>{mode === "raw" ? "Original Grid Snapshot" : "Aligned Logic Grid"}</h3>
        </div>
        <p className="review-grid-meta">
          {sheet.row_count} rows · {sheet.col_count} cols
        </p>
      </div>

      <div className="review-grid-scroll">
        <table className="review-grid-table">
          <tbody>
            {values.map((row, rowIndex) => (
              <tr key={`${sheet.sheet_id}-${rowIndex}`}>
                {row.map((value, colIndex) => {
                  const role = roles[rowIndex][colIndex] ?? "unknown";
                  const source = sourceMap[rowIndex][colIndex];
                  const tag = tags[rowIndex][colIndex] ?? "none";
                  return (
                    <td
                      key={`${rowIndex}-${colIndex}`}
                      className={`review-grid-cell ${getCellTone(role, value, tag)} ${
                        isSelected(selectedRange, rowIndex, colIndex) ? "is-selected" : ""
                      }`}
                      onClick={() => onCellSelect?.({ row: rowIndex, col: colIndex })}
                    >
                      <span className="cell-value">{value ?? "·"}</span>
                      <span className="cell-meta">
                        {mode === "aligned"
                          ? `${role}${tag !== "none" ? ` · ${tag}` : ""}`
                          : source || "empty"}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
