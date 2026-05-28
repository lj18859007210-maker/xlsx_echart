"""Semantic validation for parsed formula rules."""

from __future__ import annotations

from .formula_schema import FormulaRule, FormulaType


class FormulaValidator:
    """Check a :class:`FormulaRule` for semantic problems.

    Parameters
    ----------
    available_columns:
        Column path strings recognised by the header parser.
    available_rows:
        Row identifiers recognised in the current sheet.
    """

    def __init__(
        self,
        available_columns: list[str] | None = None,
        available_rows: list[str] | None = None,
    ) -> None:
        self.available_columns = set(available_columns or [])
        self.available_rows = set(available_rows or [])

    def validate(self, rule: FormulaRule) -> list[str]:
        """Return a list of human-readable issue descriptions (empty = OK)."""
        issues: list[str] = []

        if not rule.formula_text:
            issues.append("Formula text is empty")

        if rule.confidence < 0.0 or rule.confidence > 1.0:
            issues.append(f"Confidence {rule.confidence} is outside [0.0, 1.0]")

        type_issues = self._validate_by_type(rule)
        issues.extend(type_issues)

        return issues

    # ------------------------------------------------------------------
    # Type-specific checks
    # ------------------------------------------------------------------

    def _validate_by_type(self, rule: FormulaRule) -> list[str]:
        ft = rule.formula_type

        if ft == FormulaType.COLUMN_ARITHMETIC:
            return self._validate_column_arithmetic(rule)

        if ft == FormulaType.ROW_AGGREGATION:
            return self._validate_row_aggregation(rule)

        if ft in (FormulaType.YOY_CHANGE, FormulaType.MOM_CHANGE):
            return self._validate_yoy_mom(rule)

        if ft == FormulaType.SHARE_CALCULATION:
            return self._validate_share(rule)

        return [f"Unknown formula type: {ft}"]

    def _validate_column_arithmetic(self, rule: FormulaRule) -> list[str]:
        issues: list[str] = []

        if not rule.operator:
            issues.append("Column arithmetic formula has no operator")
        elif rule.operator not in {"+", "-", "*", "/"}:
            issues.append(f"Unknown operator: {rule.operator}")

        if not rule.right or len(rule.right) < 2:
            issues.append("Column arithmetic needs at least two source columns")

        if rule.operator == "/":
            issues.extend(self._check_division_risk(rule.right))

        if self.available_columns and rule.right:
            for col in rule.right:
                if col not in self.available_columns:
                    issues.append(f"Unknown column reference: {col}")

        return issues

    def _validate_row_aggregation(self, rule: FormulaRule) -> list[str]:
        issues: list[str] = []

        if not rule.function:
            issues.append("Row aggregation has no function name")
        elif rule.function not in {"sum", "count", "avg"}:
            issues.append(f"Unknown aggregation function: {rule.function}")

        if not rule.range_start:
            issues.append("Row aggregation has no range start")

        if rule.step < 1:
            issues.append(f"Step must be >= 1, got {rule.step}")

        if self.available_rows and rule.range_start:
            if rule.range_start not in self.available_rows:
                issues.append(f"Unknown row reference: {rule.range_start}")
        if self.available_rows and rule.range_end:
            if rule.range_end not in self.available_rows:
                issues.append(f"Unknown row reference: {rule.range_end}")

        return issues

    def _validate_yoy_mom(self, rule: FormulaRule) -> list[str]:
        issues: list[str] = []

        if not rule.new_period:
            issues.append("YoY/MoM formula has no new_period")
        if not rule.old_period:
            issues.append("YoY/MoM formula has no old_period")

        if rule.new_period == rule.old_period:
            issues.append("new_period and old_period are identical")

        if self.available_columns and rule.new_period:
            if rule.new_period not in self.available_columns:
                issues.append(f"Unknown column reference: {rule.new_period}")
        if self.available_columns and rule.old_period:
            if rule.old_period not in self.available_columns:
                issues.append(f"Unknown column reference: {rule.old_period}")

        return issues

    def _validate_share(self, rule: FormulaRule) -> list[str]:
        issues: list[str] = []

        if not rule.target_column:
            issues.append("Share formula has no target_column")

        if self.available_columns and rule.target_column:
            if rule.target_column not in self.available_columns:
                issues.append(f"Unknown column reference: {rule.target_column}")

        return issues

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_division_risk(columns: list[str] | None) -> list[str]:
        """Warn when the divisor column might contain zeros.

        Without actual data we can only flag the *structural* risk; the
        caller should combine this with data-level checks.
        """
        if not columns or len(columns) < 2:
            return []
        divisor = columns[-1]
        return [f"Division by column '{divisor}' – verify no zero values"]
