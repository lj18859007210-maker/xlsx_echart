"""Day 21 chart type selection rule engine — deterministic, no LLM."""

from __future__ import annotations

# Keywords that hint at a time-series dimension
_TIME_DIM_KEYWORDS: frozenset[str] = frozenset({
    "月", "年", "季", "日", "周", "时",
    "month", "year", "quarter", "day", "week", "date",
    "时间", "日期", "月份", "年份", "季度",
})

# Keywords that hint the data is about "composition" or "structure"
_COMPOSITION_KEYWORDS: frozenset[str] = frozenset({
    "占比", "份额", "比例", "构成", "share", "ratio", "proportion",
    "百分比", "结构",
})

# Keywords that hint the data is about "ranking"
_RANKING_KEYWORDS: frozenset[str] = frozenset({
    "排名", "排行", "名次", "rank", "ranking", "order",
})


def _looks_like_time_dim(col_name: str) -> bool:
    name_lower = col_name.lower().strip()
    for kw in _TIME_DIM_KEYWORDS:
        if kw in name_lower:
            return True
    return False


def _looks_like_composition(col_names: list[str]) -> bool:
    for col_name in col_names:
        name_lower = str(col_name).lower().strip()
        for kw in _COMPOSITION_KEYWORDS:
            if kw in name_lower:
                return True
    return False


def _looks_like_ranking(col_names: list[str]) -> bool:
    for col_name in col_names:
        name_lower = str(col_name).lower().strip()
        for kw in _RANKING_KEYWORDS:
            if kw in name_lower:
                return True
    return False


def select_chart_types(
    column_kinds: list[str],
    column_paths: list[list[str]],
    aligned_grid: list[list[object]],
    chart_hints: list[dict[str, object]] | None = None,
) -> tuple[list[dict[str, object]], str]:
    """Return (list of recommended chart specs, no_chart_reason)."""

    if not aligned_grid or len(aligned_grid) < 2:
        return [], "数据为空或不足2行，无法生成图表"

    # Classify columns
    dim_cols: list[int] = []
    measure_cols: list[int] = []
    time_dim_cols: list[int] = []

    col_names: list[str] = []
    for idx, kind in enumerate(column_kinds):
        name = ""
        if idx < len(column_paths) and column_paths[idx]:
            name = str(column_paths[idx][-1]) if column_paths[idx] else ""
        col_names.append(name)

        if kind == "dimension":
            dim_cols.append(idx)
            if _looks_like_time_dim(name):
                time_dim_cols.append(idx)
        elif kind == "measure":
            measure_cols.append(idx)

    data_rows = aligned_grid[1:]
    if len(data_rows) < 1:
        return [], "无有效数据行，无法生成图表"

    results: list[dict[str, object]] = []

    # P1: chart_hints as suggestions (validated)
    if chart_hints:
        for hint in chart_hints:
            hint_type = str(hint.get("chart_type", "")).lower()
            if hint_type in {"bar", "line", "pie", "scatter",
                             "grouped_bar", "stacked_bar", "horizontal_bar"}:
                results.append({
                    "chart_type": hint_type,
                    "title": str(hint.get("title", "")),
                    "metrics": list(hint.get("metrics", []) or []),
                    "dimension": str(hint.get("dimension", "")),
                    "source": "llm_hint",
                })

    # P2: Auto-infer
    auto_results, no_reason = _auto_infer(
        dim_cols, time_dim_cols, measure_cols,
        len(data_rows), col_names,
    )
    results.extend(auto_results)

    if not results:
        return [], no_reason

    return results, ""


def _auto_infer(
    dim_cols: list[int],
    time_dim_cols: list[int],
    measure_cols: list[int],
    row_count: int,
    col_names: list[str],
) -> tuple[list[dict[str, object]], str]:
    """Auto-infer chart types based on data structure.

    Priority order (first match wins):
    1. scatter (2+ measures, no dim)
    2. time-dim line
    3. composition → stacked_bar
    4. ranking → horizontal_bar
    5. pie (short series)
    6. line (long series)
    7. grouped_bar (2+ dims, 2+ measures)
    8. bar (fallback)
    """
    results: list[dict[str, object]] = []
    has_time = len(time_dim_cols) > 0
    dim_count = len(dim_cols)
    measure_count = len(measure_cols)

    if measure_count == 0:
        return [], "缺少度量列（measure），无法生成图表"

    # 1. Scatter: 2+ measures, no dimension
    if dim_count == 0 and measure_count >= 2:
        results.append({
            "chart_type": "scatter", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    if dim_count == 0:
        return [], "缺少维度列（dimension），至少需要一个分类维度才能生成图表"

    # 2. Time-series line
    if has_time and measure_count >= 1:
        results.append({
            "chart_type": "line", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 3. Composition / structure → stacked bar (before pie!)
    if dim_count >= 1 and measure_count >= 2 and _looks_like_composition(col_names):
        results.append({
            "chart_type": "stacked_bar", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 4. Ranking → horizontal bar (before pie!)
    if dim_count >= 1 and measure_count == 1 and _looks_like_ranking(col_names):
        results.append({
            "chart_type": "horizontal_bar", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 5. Pie: 1 dim + 1 measure, short series
    if dim_count == 1 and measure_count == 1 and row_count <= 6:
        results.append({
            "chart_type": "pie", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 6. Long series → line
    if dim_count == 1 and row_count > 6:
        results.append({
            "chart_type": "line", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 7. Grouped bar: 2+ dims + 2+ measures
    if dim_count >= 2 and measure_count >= 2:
        results.append({
            "chart_type": "grouped_bar", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    # 8. Default: bar
    if dim_count >= 1 and measure_count >= 1:
        results.append({
            "chart_type": "bar", "title": "",
            "metrics": [], "dimension": "", "source": "auto_infer",
        })
        return results, ""

    return [], "数据结构不满足任何图表类型的生成条件"