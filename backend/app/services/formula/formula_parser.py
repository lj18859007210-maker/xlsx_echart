"""Formula DSL parser – converts text formulas into structured FormulaRule objects."""

from __future__ import annotations

import re
import uuid

from .formula_exceptions import FormulaParseError
from .formula_schema import FormulaRule, FormulaType

# ---------------------------------------------------------------------------
# Patterns — P0 fix: use [\w\u4e00-\u9fff] so operators and parentheses
# naturally terminate column/row references instead of being swallowed by \S+.
#
# Non-capturing groups (?:…) are used inside composite patterns so that
# ``re.findall`` returns full match strings rather than group tuples.
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"(?:col|row)_[\w\u4e00-\u9fff]+")

# YoY / MoM: (col_A - col_B) / col_B * 100
_YOY_MOM_RE = re.compile(
    r"^\(("
    + _TOKEN_RE.pattern
    + r")\s*([-+])\s*("
    + _TOKEN_RE.pattern
    + r")\)\s*/\s*\3\s*\*\s*\d+$",
)

# Share: col_A / sum(row_all:col_A) * 100
_SHARE_RE = re.compile(
    r"^(" + _TOKEN_RE.pattern + r")\s*/\s*sum\(\S+?\)\s*\*\s*\d+$",
)

# Row aggregation: sum(row_3:row_9:2)
# Group 1 = function, Group 2 = range_start, Group 3 = range_end, Group 4 = step
_ROW_AGG_RE = re.compile(
    r"^(sum|count|avg)\(("
    + _TOKEN_RE.pattern
    + r")(?:\s*:\s*("
    + _TOKEN_RE.pattern
    + r"))?(?::(\d+))?\)$",
)

_UNKNOWN_FUNC_RE = re.compile(r"^(\w+)\(")

_VALID_FUNCTIONS = {"sum", "count", "avg"}
_ARITHMETIC_OPS = {"+", "-", "*", "/"}


# ---------------------------------------------------------------------------
# Description helpers
# ---------------------------------------------------------------------------

_OP_NAMES = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide"}


def _build_description(formula_type: str, **kwargs: object) -> str:
    """Return a concise human-readable description for a parsed formula."""
    if formula_type == FormulaType.COLUMN_ARITHMETIC:
        op = kwargs.get("operator", "?")
        cols = kwargs.get("right", [])
        op_name = _OP_NAMES.get(str(op), str(op))
        return f"{op_name} {' and '.join(str(c) for c in cols)}"

    if formula_type == FormulaType.ROW_AGGREGATION:
        func = kwargs.get("function", "?")
        start = kwargs.get("range_start", "?")
        end = kwargs.get("range_end")
        step = kwargs.get("step", 1)
        desc = f"{func} from {start}"
        if end:
            desc += f" to {end}"
        if step and step != 1:
            desc += f" every {step} rows"
        return desc

    if formula_type in (FormulaType.YOY_CHANGE, FormulaType.MOM_CHANGE):
        label = "Year-over-year" if formula_type == FormulaType.YOY_CHANGE else "Month-over-month"
        new_p = kwargs.get("new_period", "?")
        old_p = kwargs.get("old_period", "?")
        return f"{label} change from {old_p} to {new_p}"

    if formula_type == FormulaType.SHARE_CALCULATION:
        target = kwargs.get("target_column", "?")
        return f"share of {target}"

    return ""


def _build_scope(formula_type: str, **kwargs: object) -> dict[str, object]:
    """Return a structured scope dict describing which data the formula touches."""
    scope: dict[str, object] = {"formula_type": formula_type}

    if formula_type == FormulaType.COLUMN_ARITHMETIC:
        left = kwargs.get("left")
        right = kwargs.get("right")
        if left:
            scope["target"] = left
        if right:
            scope["sources"] = right

    elif formula_type == FormulaType.ROW_AGGREGATION:
        start = kwargs.get("range_start")
        end = kwargs.get("range_end")
        if start:
            scope["range_start"] = start
        if end:
            scope["range_end"] = end

    elif formula_type in (FormulaType.YOY_CHANGE, FormulaType.MOM_CHANGE):
        new_p = kwargs.get("new_period")
        old_p = kwargs.get("old_period")
        if new_p:
            scope["new_period"] = new_p
        if old_p:
            scope["old_period"] = old_p

    elif formula_type == FormulaType.SHARE_CALCULATION:
        target = kwargs.get("target_column")
        if target:
            scope["target_column"] = target

    return scope


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class FormulaParser:
    """Parse a single DSL formula string into a :class:`FormulaRule`."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, text: str) -> FormulaRule:
        text = self._preprocess(text)

        if not text:
            raise FormulaParseError("Formula cannot be empty", formula_text=text)

        if "=" not in text:
            if self._looks_like_formula(text):
                raise FormulaParseError("Missing '=' in formula", formula_text=text)
            raise FormulaParseError("Invalid formula", formula_text=text)

        left, right = text.split("=", 1)
        left = left.strip()
        right = right.strip()

        if not left or not right:
            raise FormulaParseError("Missing '=' in formula", formula_text=text)

        # --- YoY / MoM (before column arithmetic – RHS also looks arithmetic)
        yoy_mom = self._try_parse_yoy_mom(left, right, text)
        if yoy_mom is not None:
            return yoy_mom

        # --- Share calculation
        share = self._try_parse_share(left, right, text)
        if share is not None:
            return share

        # --- Column arithmetic
        col_arith = self._try_parse_column_arithmetic(left, right, text)
        if col_arith is not None:
            return col_arith

        # --- Row aggregation
        row_agg = self._try_parse_row_aggregation(left, right, text)
        if row_agg is not None:
            return row_agg

        raise FormulaParseError(f"Invalid formula: {text}", formula_text=text)

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------

    @staticmethod
    def _preprocess(text: str) -> str:
        """Strip comments (``# …``) and surrounding whitespace."""
        text = text.strip()
        comment_pos = text.find("#")
        if comment_pos != -1:
            text = text[:comment_pos].strip()
        return text

    # ------------------------------------------------------------------
    # Type-specific parsers
    # ------------------------------------------------------------------

    def _try_parse_yoy_mom(
        self, left: str, right: str, text: str,
    ) -> FormulaRule | None:
        match = _YOY_MOM_RE.match(right)
        if match is None:
            return None

        new_period = match.group(1)
        old_period = match.group(3)
        formula_type = (
            FormulaType.YOY_CHANGE if left.startswith("yoy") else FormulaType.MOM_CHANGE
        )
        return self._build_rule(
            formula_type=formula_type,
            formula_text=text,
            left=left,
            new_period=new_period,
            old_period=old_period,
            description=_build_description(
                formula_type, new_period=new_period, old_period=old_period,
            ),
            scope=_build_scope(
                formula_type, new_period=new_period, old_period=old_period,
            ),
        )

    def _try_parse_share(
        self, left: str, right: str, text: str,
    ) -> FormulaRule | None:
        match = _SHARE_RE.match(right)
        if match is None:
            return None

        target_column = match.group(1)
        return self._build_rule(
            formula_type=FormulaType.SHARE_CALCULATION,
            formula_text=text,
            left=left,
            target_column=target_column,
            description=_build_description(
                FormulaType.SHARE_CALCULATION, target_column=target_column,
            ),
            scope=_build_scope(
                FormulaType.SHARE_CALCULATION, target_column=target_column,
            ),
        )

    def _try_parse_column_arithmetic(
        self, left: str, right: str, text: str,
    ) -> FormulaRule | None:
        col_refs = _TOKEN_RE.findall(right)
        if len(col_refs) < 2:
            return None

        operator = self._find_arithmetic_operator(right, col_refs)
        if operator is None:
            return None

        return self._build_rule(
            formula_type=FormulaType.COLUMN_ARITHMETIC,
            formula_text=text,
            left=left,
            operator=operator,
            right=col_refs,
            description=_build_description(
                FormulaType.COLUMN_ARITHMETIC, operator=operator, right=col_refs,
            ),
            scope=_build_scope(
                FormulaType.COLUMN_ARITHMETIC, left=left, right=col_refs,
            ),
        )

    def _try_parse_row_aggregation(
        self, left: str, right: str, text: str,
    ) -> FormulaRule | None:
        match = _ROW_AGG_RE.match(right)
        if match is None:
            func_match = _UNKNOWN_FUNC_RE.match(right)
            if func_match and func_match.group(1) not in _VALID_FUNCTIONS:
                raise FormulaParseError(
                    f"Unknown function: {func_match.group(1)}",
                    formula_text=text,
                )
            return None

        function = match.group(1)
        range_start = match.group(2)
        range_end: str | None = match.group(3) if match.group(3) else None
        step = int(match.group(4)) if match.group(4) else 1

        return self._build_rule(
            formula_type=FormulaType.ROW_AGGREGATION,
            formula_text=text,
            left=left,
            function=function,
            range_start=range_start,
            range_end=range_end,
            step=step,
            description=_build_description(
                FormulaType.ROW_AGGREGATION,
                function=function,
                range_start=range_start,
                range_end=range_end,
                step=step,
            ),
            scope=_build_scope(
                FormulaType.ROW_AGGREGATION,
                range_start=range_start,
                range_end=range_end,
            ),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_rule(**kwargs: object) -> FormulaRule:
        return FormulaRule(
            formula_id=str(uuid.uuid4()),
            **kwargs,  # type: ignore[arg-type]
        )

    @staticmethod
    def _looks_like_formula(text: str) -> bool:
        if "col_" in text or "row_" in text:
            return True
        return any(op in text for op in _ARITHMETIC_OPS)

    @staticmethod
    def _find_arithmetic_operator(right: str, columns: list[str]) -> str | None:
        """Return the first arithmetic operator whose left operand is a column ref."""
        for idx, char in enumerate(right):
            if char in _ARITHMETIC_OPS:
                left_chunk = right[:idx].rstrip()
                if any(left_chunk.endswith(c) for c in columns):
                    return char
        return None
