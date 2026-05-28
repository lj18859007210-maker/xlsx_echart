"""Day 18 - IQR (Interquartile Range) statistical outlier detector.

Flags measure cells where the value falls outside
Q1 - 1.5*IQR or Q3 + 1.5*IQR bounds.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

IQR_MULTIPLIER = Decimal("1.5")
MIN_SAMPLE_SIZE = 4


def detect_iqr_outliers(
    aligned_grid: list[list],
    column_kinds: list[str],
    column_paths: list,
    *,
    multiplier: Decimal | None = None,
) -> list[dict[str, object]]:
    """Detect statistical outliers in measure columns using the IQR method."""
    m = multiplier if multiplier is not None else IQR_MULTIPLIER
    issues: list[dict[str, object]] = []

    for col_idx, kind in enumerate(column_kinds):
        if kind != "measure":
            continue

        metric_name = _column_name(column_paths, col_idx)

        values: list[Decimal] = []
        row_values: list[tuple[int, Decimal]] = []
        for row_idx in range(1, len(aligned_grid)):
            val = _to_decimal_safe(aligned_grid[row_idx][col_idx])
            if val is not None:
                values.append(val)
                row_values.append((row_idx, val))

        if len(values) < MIN_SAMPLE_SIZE:
            continue

        q1, q3 = _quartiles(values)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower = q1 - m * iqr
        upper = q3 + m * iqr

        for row_idx, val in row_values:
            if val < lower or val > upper:
                if val > upper:
                    distance = (val - q3) / iqr
                    direction = "偏高"
                else:
                    distance = (q1 - val) / iqr
                    direction = "偏低"

                score = min(float(abs(distance)) / 3.0, 1.0)
                issues.append({
                    "row_index": row_idx,
                    "col_index": col_idx,
                    "issue_type": "iqr_outlier",
                    "severity": "warning",
                    "metric_name": metric_name,
                    "detection_source": "statistical",
                    "reason": (
                        f"{metric_name} 在第 {row_idx + 1} 行{direction}（{val}），"
                        f"超出 IQR 范围 [{_fmt(q1)} - {_fmt(iqr)}*{float(m):.1f}, "
                        f"{_fmt(q3)} + {_fmt(iqr)}*{float(m):.1f}] = "
                        f"[{_fmt(lower)}, {_fmt(upper)}]"
                    ),
                    "score": score,
                })

    return issues


def _quartiles(values: list[Decimal]) -> tuple[Decimal, Decimal]:
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return (
        _percentile(sorted_vals, n, Decimal("25")),
        _percentile(sorted_vals, n, Decimal("75")),
    )


def _percentile(
    sorted_vals: list[Decimal],
    n: int,
    p: Decimal,
) -> Decimal:
    if n == 1:
        return sorted_vals[0]

    fraction = p / Decimal("100")
    index = fraction * Decimal(str(n - 1))
    lower_idx = int(float(index))
    upper_idx = min(lower_idx + 1, n - 1)

    if lower_idx == upper_idx:
        return sorted_vals[lower_idx]

    weight = index - Decimal(str(lower_idx))
    return sorted_vals[lower_idx] * (Decimal("1") - weight) + sorted_vals[upper_idx] * weight


def _fmt(d: Decimal) -> str:
    s = str(d.normalize()) if d == d.normalize() else str(d)
    return s


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