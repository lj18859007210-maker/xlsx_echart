# Day 12: Formula DSL Design Implementation Plan

> **Goal:** Design and implement a Formula DSL parser that can express column relationships, row aggregations, and YoY/MoM comparisons.

**Architecture:** The DSL uses a simple text-based syntax that maps to Python operations. The parser converts DSL strings into structured formula objects that the validation engine can execute.

**Tech Stack:** Python, Pydantic

---

## DSL Syntax Specification

### 1. Column Relationships (列间关系)

`
# Basic arithmetic between columns
col_C = col_A + col_B
col_C = col_A - col_B
col_C = col_A * col_B
col_C = col_A / col_B

# With column names (from header parsing)
col_营业利润 = col_营业收入 - col_营业成本
`

### 2. Row Aggregations (行间汇总)

`
# Sum of row range
row_10 = sum(row_3:row_9)

# Sum with step
row_10 = sum(row_3:row_9:2)  # every other row

# Count
row_10 = count(row_3:row_9)

# Average
row_10 = avg(row_3:row_9)
`

### 3. YoY/MoM Comparisons (同比环比)

`
# Year-over-Year percentage change
yoy_2024 = (col_2024 - col_2023) / col_2023 * 100

# Month-over-Month
mom_Q2 = (col_Q2 - col_Q1) / col_Q1 * 100
`

### 4. Percentage/Share (占比)

`
# Share of total
share_A = col_A / sum(row_all:col_A) * 100
`

---

## Formula Types

1. **column_arithmetic** - Basic arithmetic between columns
2. **row_aggregation** - Aggregation functions over row ranges
3. **yoy_change** - Year-over-year percentage change
4. **mom_change** - Month-over-month percentage change
5. **share_calculation** - Percentage/share calculation

---

## Output Schema

`python
class FormulaRule(BaseModel):
    formula_id: str
    formula_text: str  # Original DSL text
    formula_type: str  # column_arithmetic | row_aggregation | yoy_change | mom_change | share_calculation
    description: str
    scope: dict  # Which columns/rows this applies to
    confidence: float  # 0.0-1.0
    rule_type: str  # derived | inferred | manual
`

---

## Implementation Steps

### Task 1: Write Parser Tests
- Test column arithmetic parsing
- Test row aggregation parsing
- Test YoY/MoM parsing
- Test error cases

### Task 2: Implement Parser
- Lexer for tokenization
- Parser for AST generation
- Validator for semantic checks

### Task 3: Write Integration Tests
- Test full formula lifecycle
- Test edge cases

