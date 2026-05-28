"""Formula DSL custom exceptions."""


class FormulaError(Exception):
    """Base exception for all formula-related errors."""

    def __init__(self, message: str, formula_text: str = "") -> None:
        self.formula_text = formula_text
        super().__init__(message)


class FormulaParseError(FormulaError):
    """Raised when a formula string cannot be tokenised or parsed."""


class FormulaValidationError(FormulaError):
    """Raised when a parsed formula fails semantic validation."""
