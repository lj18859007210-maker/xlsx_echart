import pytest

from app.services.formula import (
    FormulaParseError,
    FormulaParser,
    FormulaRule,
    FormulaType,
    FormulaValidator,
)


class TestFormulaParserColumnArithmetic:
    """Test column arithmetic formula parsing."""

    def test_parse_simple_column_subtraction(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A - col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.left == "col_C"
        assert result.operator == "-"
        assert result.right == ["col_A", "col_B"]
        assert result.formula_text == "col_C = col_A - col_B"

    def test_parse_simple_column_addition(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A + col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "+"
        assert result.right == ["col_A", "col_B"]

    def test_parse_column_multiplication(self):
        parser = FormulaParser()
        result = parser.parse("col_D = col_A * col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "*"

    def test_parse_column_division(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A / col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "/"

    def test_parse_chinese_column_names(self):
        parser = FormulaParser()
        result = parser.parse("col_\u8425\u4e1a\u5229\u6da6 = col_\u8425\u4e1a\u6536\u5165 - col_\u8425\u4e1a\u6210\u672c")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.left == "col_\u8425\u4e1a\u5229\u6da6"
        assert result.right == ["col_\u8425\u4e1a\u6536\u5165", "col_\u8425\u4e1a\u6210\u672c"]

    def test_parse_multi_column_expression(self):
        parser = FormulaParser()
        result = parser.parse("col_D = col_A + col_B + col_C")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "+"
        assert result.right == ["col_A", "col_B", "col_C"]

    def test_parse_no_space_operators(self):
        """P0: operators without surrounding spaces must parse correctly."""
        parser = FormulaParser()
        result = parser.parse("col_C=col_A+col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "+"
        assert result.right == ["col_A", "col_B"]

    def test_parse_no_space_multiplication(self):
        """P0: compact multiplication expression."""
        parser = FormulaParser()
        result = parser.parse("col_D=col_A*col_B")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "*"
        assert result.right == ["col_A", "col_B"]


class TestFormulaParserRowAggregation:
    """Test row aggregation formula parsing."""

    def test_parse_sum_aggregation(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = sum(row_3:row_9)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.left == "row_10"
        assert result.function == "sum"
        assert result.range_start == "row_3"
        assert result.range_end == "row_9"

    def test_parse_count_aggregation(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = count(row_3:row_9)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.function == "count"

    def test_parse_avg_aggregation(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = avg(row_3:row_9)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.function == "avg"

    def test_parse_sum_with_step(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = sum(row_3:row_9:2)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.step == 2

    def test_parse_chinese_row_names(self):
        parser = FormulaParser()
        result = parser.parse("row_\u603b\u8ba1 = sum(row_\u7b2c1\u9879:row_\u7b2c9\u9879)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.left == "row_\u603b\u8ba1"
        assert result.range_start == "row_\u7b2c1\u9879"
        assert result.range_end == "row_\u7b2c9\u9879"

    def test_parse_sum_no_end_range(self):
        """Row aggregation with only range_start (no colon)."""
        parser = FormulaParser()
        result = parser.parse("row_10 = sum(row_3)")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.range_start == "row_3"
        assert result.range_end is None


class TestFormulaParserYoYMoM:
    """Test YoY/MoM change formula parsing."""

    def test_parse_yoy_change(self):
        parser = FormulaParser()
        result = parser.parse("yoy_2024 = (col_2024 - col_2023) / col_2023 * 100")

        assert result.formula_type == FormulaType.YOY_CHANGE
        assert result.new_period == "col_2024"
        assert result.old_period == "col_2023"

    def test_parse_mom_change(self):
        parser = FormulaParser()
        result = parser.parse("mom_Q2 = (col_Q2 - col_Q1) / col_Q1 * 100")

        assert result.formula_type == FormulaType.MOM_CHANGE
        assert result.new_period == "col_Q2"
        assert result.old_period == "col_Q1"

    def test_parse_yoy_with_different_format(self):
        parser = FormulaParser()
        result = parser.parse("yoy_2024_2023 = (col_2024 - col_2023) / col_2023 * 100")

        assert result.formula_type == FormulaType.YOY_CHANGE


class TestFormulaParserShareCalculation:
    """Test share/percentage calculation parsing."""

    def test_parse_share_calculation(self):
        parser = FormulaParser()
        result = parser.parse("share_A = col_A / sum(row_all:col_A) * 100")

        assert result.formula_type == FormulaType.SHARE_CALCULATION
        assert result.target_column == "col_A"


class TestFormulaParserComments:
    """P3: test that trailing comments are stripped before parsing."""

    def test_comment_after_column_formula(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A + col_B # profit calc")

        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.right == ["col_A", "col_B"]

    def test_comment_after_row_aggregation(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = sum(row_3:row_9) # every other row")

        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.function == "sum"


class TestFormulaParserDescriptionAndScope:
    """P1: test that description and scope are populated."""

    def test_column_arithmetic_description(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A + col_B")

        assert result.description != ""
        assert "add" in result.description
        assert "col_A" in result.description
        assert "col_B" in result.description

    def test_column_arithmetic_scope(self):
        parser = FormulaParser()
        result = parser.parse("col_C = col_A - col_B")

        assert result.scope["target"] == "col_C"
        assert result.scope["sources"] == ["col_A", "col_B"]

    def test_row_aggregation_description(self):
        parser = FormulaParser()
        result = parser.parse("row_10 = sum(row_3:row_9)")

        assert "sum" in result.description
        assert "row_3" in result.description
        assert "row_9" in result.description

    def test_yoy_description(self):
        parser = FormulaParser()
        result = parser.parse("yoy_2024 = (col_2024 - col_2023) / col_2023 * 100")

        assert "Year-over-year" in result.description
        assert "col_2023" in result.description

    def test_share_description(self):
        parser = FormulaParser()
        result = parser.parse("share_A = col_A / sum(row_all:col_A) * 100")

        assert "share" in result.description
        assert "col_A" in result.description


class TestFormulaParserErrors:
    """Test error handling in formula parsing."""

    def test_invalid_formula_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(FormulaParseError, match="Invalid formula"):
            parser.parse("invalid formula")

    def test_empty_formula_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(FormulaParseError, match="Formula cannot be empty"):
            parser.parse("")

    def test_missing_equals_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(FormulaParseError, match="Missing '='"):
            parser.parse("col_A col_B + col_C")

    def test_unknown_function_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(FormulaParseError, match="Unknown function"):
            parser.parse("row_1 = unknown(row_2:row_3)")

    def test_error_carries_formula_text(self):
        parser = FormulaParser()
        with pytest.raises(FormulaParseError) as exc_info:
            parser.parse("invalid formula")
        assert exc_info.value.formula_text == "invalid formula"


class TestFormulaValidator:
    """P1: semantic validation tests."""

    def test_valid_column_arithmetic_passes(self):
        parser = FormulaParser()
        rule = parser.parse("col_C = col_A + col_B")
        validator = FormulaValidator(available_columns=["col_A", "col_B", "col_C"])

        issues = validator.validate(rule)
        assert issues == []

    def test_unknown_column_flagged(self):
        parser = FormulaParser()
        rule = parser.parse("col_C = col_A + col_B")
        validator = FormulaValidator(available_columns=["col_A", "col_C"])

        issues = validator.validate(rule)
        assert any("col_B" in i for i in issues)

    def test_division_risk_warned(self):
        parser = FormulaParser()
        rule = parser.parse("col_C = col_A / col_B")
        validator = FormulaValidator(available_columns=["col_A", "col_B", "col_C"])

        issues = validator.validate(rule)
        assert any("zero" in i.lower() or "Division" in i for i in issues)

    def test_unknown_aggregation_function_flagged(self):
        rule = FormulaRule(
            formula_text="row_1 = weird(row_2:row_3)",
            formula_type=FormulaType.ROW_AGGREGATION,
            function="weird",
            range_start="row_2",
            range_end="row_3",
        )
        validator = FormulaValidator()
        issues = validator.validate(rule)
        assert any("weird" in i for i in issues)

    def test_yoy_same_period_flagged(self):
        parser = FormulaParser()
        rule = parser.parse("yoy_2024 = (col_2024 - col_2024) / col_2024 * 100")
        validator = FormulaValidator()

        issues = validator.validate(rule)
        assert any("identical" in i.lower() for i in issues)

    def test_confidence_out_of_range_flagged(self):
        rule = FormulaRule(
            formula_text="col_C = col_A + col_B",
            formula_type=FormulaType.COLUMN_ARITHMETIC,
            confidence=1.5,
        )
        validator = FormulaValidator()
        issues = validator.validate(rule)
        assert any("Confidence" in i for i in issues)

    def test_valid_row_aggregation_passes(self):
        parser = FormulaParser()
        rule = parser.parse("row_10 = sum(row_3:row_9)")
        validator = FormulaValidator(
            available_rows=["row_3", "row_9", "row_10"],
        )
        issues = validator.validate(rule)
        assert issues == []
