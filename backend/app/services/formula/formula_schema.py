"""Formula DSL Schema definitions."""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel


class FormulaType(str, Enum):
    """Types of formulas supported by the DSL."""
    COLUMN_ARITHMETIC = "column_arithmetic"
    ROW_AGGREGATION = "row_aggregation"
    YOY_CHANGE = "yoy_change"
    MOM_CHANGE = "mom_change"
    SHARE_CALCULATION = "share_calculation"


class FormulaRule(BaseModel):
    """Parsed formula rule structure."""
    formula_id: str = ""
    formula_text: str
    formula_type: FormulaType
    description: str = ""
    
    # For column arithmetic
    left: Optional[str] = None
    operator: Optional[str] = None
    right: Optional[List[str]] = None
    
    # For row aggregation
    function: Optional[str] = None
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    step: int = 1
    
    # For YoY/MoM
    new_period: Optional[str] = None
    old_period: Optional[str] = None
    
    # For share calculation
    target_column: Optional[str] = None
    
    # Metadata
    scope: dict = {}
    confidence: float = 1.0
    rule_type: str = "derived"
