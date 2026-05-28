
from app.services.validation.execution_plan import (
    PlanKind,
    build_execution_plan,
    build_execution_plans,
)


def test_build_column_arithmetic_plan():
    rule = {
        "formula_text": "col_Profit = col_Revenue - col_Cost",
        "formula_type": "column_arithmetic",
    }
    column_map = {"col_Profit": 3, "col_Revenue": 1, "col_Cost": 2}

    plan = build_execution_plan(rule, column_map)

    assert plan is not None
    assert plan.kind == PlanKind.ROW_WISE
    assert plan.target_column_index == 3
    assert plan.operator == "-"
    assert plan.operand_indices == [1, 2]
    assert plan.aggregate_func is None
    assert plan.formula_text == rule["formula_text"]


def test_build_column_arithmetic_plan_returns_none_for_unknown_column():
    rule = {
        "formula_text": "col_Profit = col_Revenue - col_Cost",
        "formula_type": "column_arithmetic",
    }
    column_map = {"col_Revenue": 1, "col_Cost": 2}

    plan = build_execution_plan(rule, column_map)
    assert plan is None


def test_build_row_aggregation_sum_plan():
    rule = {
        "formula_text": "row_Total = sum(row_1:row_2)",
        "formula_type": "row_aggregation",
    }
    column_map = {"Total": 2}

    plan = build_execution_plan(rule, column_map)

    assert plan is not None
    assert plan.kind == PlanKind.AGGREGATE
    assert plan.target_column_index == 2
    assert plan.aggregate_func == "sum"
    assert plan.operator is None
    assert plan.row_start == 1
    assert plan.row_end == 2


def test_build_yoy_plan_returns_none():
    rule = {
        "formula_text": "col_Revenue_yoy = yoy(col_Revenue, col_Revenue_prev)",
        "formula_type": "yoy_change",
    }
    column_map = {"col_Revenue_yoy": 1, "col_Revenue": 0, "col_Revenue_prev": 0}

    plan = build_execution_plan(rule, column_map)
    assert plan is None


def test_build_execution_plans_filters_nones():
    rules = [
        {
            "formula_text": "col_Profit = col_Revenue - col_Cost",
            "formula_type": "column_arithmetic",
        },
        {
            "formula_text": "col_Revenue_yoy = yoy(col_Revenue)",
            "formula_type": "yoy_change",
        },
    ]
    column_map = {"col_Profit": 2, "col_Revenue": 0, "col_Cost": 1}

    plans = build_execution_plans(rules, column_map)
    assert len(plans) == 1
    assert plans[0].kind == PlanKind.ROW_WISE
