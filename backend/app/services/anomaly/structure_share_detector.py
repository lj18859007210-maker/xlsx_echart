"""Day 17 — structure share anomaly detector.

Flags rows where a measure column's share of the row total
changes by more than a configurable threshold between periods.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

DEFAULT_SHARE_CHANGE_THRESHOLD = Decimal("0.20")


def detect_structure_share_anomalies(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    *,
    threshold: Decimal | None = None,
) -> list[dict[str, object]]:
    """Detect anomalous structure share changes across measure columns.

    For each row, computes share of each measure column as fraction of
    the row's measure-column total. Compares shares across adjacent rows
    and flags changes exceeding threshold.
    """
    t = threshold if threshold is not None else DEFAULT_SHARE_CHANGE_THRESHOLD
    issues: list[dict[str, object]] = []

    if len(aligned_grid) < 3:
        return issues

    measure_cols = [i for i, k in enumerate(column_kinds) if k == "measure"]
    if len(measure_cols) < 2:
        return issues

    prev_shares: dict[int, Decimal] = {}

    for row_idx in range(1, len(aligned_grid)):
        row = aligned_grid[row_idx]
        if not isinstance(row, list):
            prev_shares.clear()
            continue

        # Compute current row's measure values
        cur_values: dict[int, Decimal] = {}
        total = Decimal("0")
        for col_idx in measure_cols:
            val = _to_decimal_safe(row[col_idx])
            if val is not None:
                cur_values[col_idx] = val
                total += val

        if total == 0:
            prev_shares = {}
            continue

        # Compare shares against previous row
        if prev_shares:
            for col_idx in measure_cols:
                cur_val = cur_values.get(col_idx)
                prev_val = prev_shares.get(col_idx)
                if cur_val is None or prev_val is None:
                    continue

                cur_share = cur_val / total
                prev_total = sum(Decimal(str(v)) for v in prev_shares.values())
                if prev_total == 0:
                    continue
                prev_share = prev_val / prev_total
                change = cur_share - prev_share

                if abs(change) > t:
                    metric_name = _column_name(column_paths, col_idx)
                    direction = "上升" if change > 0 else "下降"
                    pct = float(abs(change) * 100)
                    issues.append({
                        "row_index": row_idx,
                        "col_index": col_idx,
                        "issue_type": "structure_share_anomaly",
                        "severity": "warning",
                        "metric_name": metric_name,
                        "detection_source": "business_rule",
                        "reason": (
                            f"{metric_name} 在第 {row_idx + 1} 行占比{direction} {pct:.1f}pp，"
                            f"超过阈值 {float(t) * 100:.0f}pp"
                        ),
                        "score": min(float(abs(change)), 1.0),
                    })

        prev_shares = cur_values

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