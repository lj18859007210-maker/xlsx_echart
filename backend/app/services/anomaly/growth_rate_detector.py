"""Day 17 — growth rate anomaly detector.

Flags cells where period-over-period growth exceeds a configurable threshold.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

DEFAULT_GROWTH_RATE_THRESHOLD = Decimal("0.50")


def detect_growth_rate_anomalies(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    *,
    threshold: Decimal | None = None,
) -> list[dict[str, object]]:
    """Detect anomalous growth rates across measure columns.

    For each measure column, compares row[i+1] against row[i].
    Flags when |growth| > threshold (default 50%).
    """
    t = threshold if threshold is not None else DEFAULT_GROWTH_RATE_THRESHOLD
    issues: list[dict[str, object]] = []

    if len(aligned_grid) < 3:
        return issues

    for col_idx, kind in enumerate(column_kinds):
        if kind != "measure":
            continue

        metric_name = _column_name(column_paths, col_idx)

        prev_val = _to_decimal_safe(aligned_grid[1][col_idx])
        if prev_val is None:
            continue

        for row_idx in range(2, len(aligned_grid)):
            cur_val = _to_decimal_safe(aligned_grid[row_idx][col_idx])
            if cur_val is None:
                # Non-numeric cell — find next valid baseline
                prev_val = _find_next_valid(aligned_grid, row_idx + 1, col_idx)
                continue

            if prev_val == 0:
                prev_val = cur_val
                continue

            growth = (cur_val - prev_val) / abs(prev_val)
            if abs(growth) > t:
                direction = "\u589e\u957f" if growth > 0 else "\u4e0b\u964d"
                pct = float(abs(growth) * 100)
                issues.append({
                    "row_index": row_idx,
                    "col_index": col_idx,
                    "issue_type": "growth_rate_anomaly",
                    "severity": "warning",
                    "metric_name": metric_name,
                    "detection_source": "business_rule",
                    "reason": (
                        f"{metric_name} \u5728\u7b2c {row_idx + 1} \u884c{direction} {pct:.1f}%\uff0c"
                        f"\u8d85\u8fc7\u9608\u503c {float(t) * 100:.0f}%"
                    ),
                    "score": min(float(abs(growth)), 1.0),
                })

            prev_val = cur_val

    return issues


def _find_next_valid(
    grid: list[list],
    start_row: int,
    col_idx: int,
) -> Decimal | None:
    """Find the next valid numeric value starting from start_row."""
    for r in range(start_row, len(grid)):
        val = _to_decimal_safe(grid[r][col_idx])
        if val is not None:
            return val
    return None


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