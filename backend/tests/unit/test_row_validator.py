from app.services.validation.execution_plan import ExecutionPlan, PlanKind
from app.services.validation.row_validator import validate_rows


def _plan(
    target_col: int,
    op: str,
    left: int,
    right: int,
    text: str = "col_C = col_A op col_B",
) -> ExecutionPlan:
    return ExecutionPlan(
        kind=PlanKind.ROW_WISE,
        target_column_index=target_col,
        operator=op,
        operand_indices=[left, right],
        formula_text=text,
    )


def test_row_validator_finds_exact_mismatch():
    aligned_grid = [
        ["Region", "Revenue", "Cost", "Profit"],
        ["East", "100", "80", "20"],
        ["West", "90", "70", "25"],
    ]
    plans = [
        _plan(
            target_col=3,
            op="-",
            left=1,
            right=2,
            text="col_Profit = col_Revenue - col_Cost",
        )
    ]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 1
    assert issues[0]["row_index"] == 2
    assert issues[0]["col_index"] == 3
    assert issues[0]["expected_value"] == "20"
    assert issues[0]["actual_value"] == "25"
    assert issues[0]["severity"] == "error"
    assert issues[0]["issue_type"] == "mismatch"


def test_row_validator_no_issues_when_all_match():
    aligned_grid = [
        ["Region", "Revenue", "Cost", "Profit"],
        ["East", "100", "80", "20"],
        ["West", "90", "70", "20"],
    ]
    plans = [_plan(target_col=3, op="-", left=1, right=2)]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 0


def test_row_validator_skips_non_numeric_cells():
    aligned_grid = [
        ["Region", "Revenue", "Cost", "Profit"],
        ["East", "N/A", "80", "20"],
        ["West", "90", "N/A", "20"],
    ]
    plans = [_plan(target_col=3, op="-", left=1, right=2)]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 0


def test_row_validator_flags_division_by_zero():
    aligned_grid = [
        ["Item", "A", "B", "Ratio"],
        ["X", "100", "0", "10"],
    ]
    plans = [
        _plan(target_col=3, op="/", left=1, right=2, text="col_Ratio = col_A / col_B")
    ]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "division_by_zero"
    assert issues[0]["severity"] == "warning"


def test_row_validator_supports_addition():
    aligned_grid = [
        ["Item", "A", "B", "Total"],
        ["X", "100", "200", "300"],
        ["Y", "50", "60", "200"],
    ]
    plans = [
        _plan(target_col=3, op="+", left=1, right=2, text="col_Total = col_A + col_B")
    ]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 1
    assert issues[0]["row_index"] == 2
    assert issues[0]["expected_value"] == "110"
    assert issues[0]["actual_value"] == "200"


def test_row_validator_supports_multiplication():
    aligned_grid = [
        ["Item", "Price", "Qty", "Total"],
        ["X", "10", "5", "50"],
        ["Y", "10", "6", "70"],
    ]
    plans = [
        _plan(target_col=3, op="*", left=1, right=2, text="col_Total = col_Price * col_Qty")
    ]
    issues = validate_rows(aligned_grid, plans)
    assert len(issues) == 1
    assert issues[0]["expected_value"] == "60"
    assert issues[0]["actual_value"] == "70"
