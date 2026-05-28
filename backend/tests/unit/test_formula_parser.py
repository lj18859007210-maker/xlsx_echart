import pytest
from app.services.formula.formula_parser import FormulaParser
from app.services.formula.formula_schema import FormulaRule, FormulaType


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
        result = parser.parse("col_营业利润 = col_营业收入 - col_营业成本")
        
        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.left == "col_营业利润"
        assert result.right == ["col_营业收入", "col_营业成本"]

    def test_parse_multi_column_expression(self):
        parser = FormulaParser()
        result = parser.parse("col_D = col_A + col_B + col_C")
        
        assert result.formula_type == FormulaType.COLUMN_ARITHMETIC
        assert result.operator == "+"
        assert result.right == ["col_A", "col_B", "col_C"]


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
        result = parser.parse("row_总计 = sum(row_第1项:row_第9项)")
        
        assert result.formula_type == FormulaType.ROW_AGGREGATION
        assert result.left == "row_总计"
        assert result.range_start == "row_第1项"
        assert result.range_end == "row_第9项"


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


class TestFormulaParserErrors:
    """Test error handling in formula parsing."""

    def test_invalid_formula_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(ValueError, match="Invalid formula"):
            parser.parse("invalid formula")

    def test_empty_formula_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(ValueError, match="Formula cannot be empty"):
            parser.parse("")

    def test_missing_equals_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(ValueError, match="Missing '='"):
            parser.parse("col_A col_B + col_C")

    def test_unknown_function_raises_error(self):
        parser = FormulaParser()
        with pytest.raises(ValueError, match="Unknown function"):
            parser.parse("row_1 = unknown(row_2:row_3)")
