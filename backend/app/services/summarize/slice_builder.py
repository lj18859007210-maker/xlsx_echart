"""Day 19 - slice builder.

Extracts context rows around validation issues and anomalies,
with reason tags and header rows.
"""

from __future__ import annotations


def build_slices(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    sheet_name: str,
    validation_issues: list[dict[str, object]],
    anomaly_issues: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Build context slices around detected issues."""

    # Collect all interesting rows from both issue types
    target_rows: set[int] = set()

    for issue in validation_issues:
        target_rows.add(int(issue.get("row_index", 0)))
    for issue in anomaly_issues:
        target_rows.add(int(issue.get("row_index", 0)))

    if not target_rows:
        return []

    # Group consecutive rows into slice ranges with +/- 1 context
    sorted_rows = sorted(target_rows)
    ranges: list[tuple[int, int]] = []
    start = sorted_rows[0]
    end = sorted_rows[0]

    for r in sorted_rows[1:]:
        if r <= end + 2:  # merge if within context window
            end = r
        else:
            ranges.append((max(start - 1, 0), min(end + 1, len(aligned_grid) - 1)))
            start = r
            end = r
    ranges.append((max(start - 1, 0), min(end + 1, len(aligned_grid) - 1)))

    # Build slices
    slices: list[dict[str, object]] = []
    for slice_start, slice_end in ranges:
        header_row = aligned_grid[0] if aligned_grid else []

        # Collect issue annotations for this slice
        issue_cells: list[dict[str, object]] = []
        reason_tags: list[str] = []

        for issue in validation_issues:
            ri = int(issue.get("row_index", -1))
            if slice_start <= ri <= slice_end:
                issue_cells.append({
                    "row": ri,
                    "col": int(issue.get("col_index", 0)),
                    "expected": str(issue.get("expected_value", "")),
                    "actual": str(issue.get("actual_value", "")),
                    "severity": str(issue.get("severity", "")),
                })
                reason_tags.append(
                    f"\u516c\u5f0f\u6821\u9a8c\u4e0d\u4e00\u81f4"
                )

        for issue in anomaly_issues:
            ri = int(issue.get("row_index", -1))
            if slice_start <= ri <= slice_end:
                issue_cells.append({
                    "row": ri,
                    "col": int(issue.get("col_index", 0)),
                    "reason": str(issue.get("reason", "")),
                    "severity": str(issue.get("severity", "")),
                })
                reason_tags.append(str(issue.get("issue_type", "")))

        # Deduplicate tags
        unique_tags = list(dict.fromkeys(reason_tags))

        slices.append({
            "sheet_name": sheet_name,
            "reason_tags": unique_tags,
            "start_row": slice_start,
            "end_row": slice_end,
            "header": header_row,
            "rows": aligned_grid[slice_start:slice_end + 1],
            "issue_cells": issue_cells,
        })

    return slices


def build_semantic_schema(
    column_kinds: list[str],
    column_paths: list,
    sheet_name: str = "",
) -> dict[str, object]:
    """Extract semantic schema: dimensions, measures, time columns."""
    dimensions: list[str] = []
    measures: list[str] = []
    time_cols: list[str] = []

    for col_idx, kind in enumerate(column_kinds):
        name = _column_name(column_paths, col_idx)
        if kind == "dimension":
            dimensions.append(name)
        elif kind == "measure":
            measures.append(name)
        elif kind in ("time", "date", "year", "quarter", "month"):
            time_cols.append(name)

    return {
        "sheet_name": sheet_name,
        "dimensions": dimensions,
        "measures": measures,
        "time_columns": time_cols,
    }


def _column_name(column_paths: list, col_idx: int) -> str:
    if col_idx < len(column_paths) and isinstance(column_paths[col_idx], list):
        return str(column_paths[col_idx][-1]) if column_paths[col_idx] else f"col_{col_idx}"
    return f"col_{col_idx}"