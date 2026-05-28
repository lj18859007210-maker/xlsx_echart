"""Day 17 — negative/zero value anomaly detector.

Flags measure cells where value <= 0, which is anomalous for
revenue, profit, and similar positive-expectation metrics.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

DEFAULT_NEGATIVE_THRESHOLD = Decimal("0")


def detect_negative_zero_anomalies(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    *,
    threshold: Decimal | None = None,
) -> list[dict[str, object]]:
    """Flag measure cells with value <= threshold (default 0)."""
    t = threshold if threshold is not None else DEFAULT_NEGATIVE_THRESHOLD
    issues: list[dict[str, object]] = []

    if len(aligned_grid) < 2:
        return issues

    for col_idx, kind in enumerate(column_kinds):
        if kind != "measure":
            continue

        metric_name = _column_name(column_paths, col_idx)

        for row_idx in range(1, len(aligned_grid)):
            val = _to_decimal_safe(aligned_grid[row_idx][col_idx])
            if val is None:
                continue

            if val <= t:
                tag = "负值" if val < 0 else "零值"
                issues.append({
                    "row_index": row_idx,
                    "col_index": col_idx,
                    "issue_type": "negative_or_zero",
                    "severity": "error" if val < 0 else "warning",
                    "metric_name": metric_name,
                    "detection_source": "business_rule",
                    "reason": f"{metric_name} 在第 {row_idx + 1} 行为{tag}（{val}）",
                    "score": 1.0 if val < 0 else 0.5,
                })

    return issues


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