from app.services.validation.aggregate_validator import validate_aggregates
from app.services.validation.execution_plan import ExecutionPlan, PlanKind


def _plan(
    target_col: int,
    agg_func: str,
    row_start: int,
    row_end: int,
    step: int = 1,
    text: str = "row_X = sum(row_A:row_B)",
) -> ExecutionPlan:
    return ExecutionPlan(
        kind=PlanKind.AGGREGATE,
        target_column_index=target_col,
        aggregate_func=agg_func,
        row_start=row_start,
        row_end=row_end,
        step=step,
        formula_text=text,
    )


def test_sum_validator_matches_total():
    aligned_grid = [
        ["Category", "Amount"],
        ["A", "100"],
        ["B", "200"],
        ["Total", "300"],
    ]
    plans = [_plan(target_col=1, agg_func="sum", row_start=1, row_end=2)]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 0


def test_sum_validator_finds_mismatch():
    aligned_grid = [
        ["Category", "Amount"],
        ["A", "100"],
        ["B", "200"],
        ["Total", "500"],
    ]
    plans = [
        _plan(
            target_col=1,
            agg_func="sum",
            row_start=1,
            row_end=2,
            text="row_Total = sum(row_A:row_B)",
        )
    ]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 1
    assert issues[0]["expected_value"] == "300"
    assert issues[0]["actual_value"] == "500"
    assert issues[0]["severity"] == "error"
    assert issues[0]["issue_type"] == "aggregate_mismatch"


def test_avg_validator_matches():
    aligned_grid = [
        ["Month", "Value"],
        ["Jan", "100"],
        ["Feb", "200"],
        ["Avg", "150"],
    ]
    plans = [_plan(target_col=1, agg_func="avg", row_start=1, row_end=2)]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 0


def test_count_validator():
    aligned_grid = [
        ["Item", "Count"],
        ["A", "10"],
        ["B", "20"],
        ["N", "2"],
    ]
    plans = [_plan(target_col=1, agg_func="count", row_start=1, row_end=2)]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 0


def test_aggregate_skips_non_numeric():
    aligned_grid = [
        ["Item", "Value"],
        ["A", "N/A"],
        ["B", "200"],
        ["Total", "200"],
    ]
    plans = [_plan(target_col=1, agg_func="sum", row_start=1, row_end=2)]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 0


def test_sum_with_step():
    aligned_grid = [
        ["Item", "Value"],
        ["Q1-A", "100"],
        ["Q1-B", "200"],
        ["Q2-A", "50"],
        ["Q2-B", "60"],
        ["Total", "410"],
    ]
    plans = [_plan(target_col=1, agg_func="sum", row_start=1, row_end=4, step=1)]
    issues = validate_aggregates(aligned_grid, plans)
    assert len(issues) == 0
