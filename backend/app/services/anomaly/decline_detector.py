"""Day 17 — consecutive decline detector.

Flags when a measure column has N consecutive period-over-period declines.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

DEFAULT_CONSECUTIVE_N = 3


def detect_consecutive_declines(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    *,
    min_consecutive: int | None = None,
) -> list[dict[str, object]]:
    """Detect N consecutive period-over-period declines in measure columns."""
    n = min_consecutive if min_consecutive is not None else DEFAULT_CONSECUTIVE_N
    issues: list[dict[str, object]] = []

    if len(aligned_grid) < n + 1:
        return issues

    for col_idx, kind in enumerate(column_kinds):
        if kind != "measure":
            continue

        metric_name = _column_name(column_paths, col_idx)

        decline_start: int | None = None
        streak = 0
        prev_val: Decimal | None = None

        for row_idx in range(1, len(aligned_grid)):
            cur_val = _to_decimal_safe(aligned_grid[row_idx][col_idx])
            if cur_val is None:
                # Reset on non-numeric
                if streak >= n and decline_start is not None:
                    issues.append(_make_issue(
                        metric_name, decline_start, row_idx - 1, col_idx, streak,
                    ))
                decline_start = None
                streak = 0
                prev_val = None
                continue

            if prev_val is not None and cur_val < prev_val:
                if decline_start is None:
                    decline_start = row_idx - 1
                streak += 1
            else:
                if streak >= n and decline_start is not None:
                    issues.append(_make_issue(
                        metric_name, decline_start, row_idx - 1, col_idx, streak,
                    ))
                decline_start = None
                streak = 0

            prev_val = cur_val

        # Check streak at end of column
        if streak >= n and decline_start is not None:
            issues.append(_make_issue(
                metric_name, decline_start, len(aligned_grid) - 1, col_idx, streak,
            ))

    return issues


def _make_issue(
    metric_name: str,
    start_row: int,
    end_row: int,
    col_idx: int,
    streak: int,
) -> dict[str, object]:
    return {
        "row_index": end_row,
        "col_index": col_idx,
        "issue_type": "consecutive_decline",
        "severity": "warning",
        "metric_name": metric_name,
        "detection_source": "business_rule",
        "reason": (
            f"{metric_name} 在第 {start_row + 1} 行至第 {end_row + 1} 行连续 {streak} 期下滑"
        ),
        "score": min(streak / 5.0, 1.0),
    }


def _to_decimal_safe(value: object) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _column_name(column_paths: list, col_idx: int) -> str:
    if col_idx < len(column_paths) and isinstance(column_paths[col_idx], list):
        return str(column_paths[col_idx][-1]) if column_paths[col_idx] else f"col_{col_idx}"
    return f"col_{col_idx}"