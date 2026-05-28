# Day 15 校验引擎主逻辑 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建确定性校验引擎，将 Day 13/14 产出的公式规则转化为可执行的计算计划，对确认后的表格数据逐行逐列进行精确校验，输出带坐标定位的误差清单。所有计算由 Python 确定性地完成，不引入 LLM。

**Architecture:** 三层执行模型：DSL 解析 → 执行计划构建 → 逐行/聚合双模式校验。校验引擎只读不写——输入公式规则 + 对齐网格数据，输出校验结果字典，不修改数据库。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Python `decimal.Decimal`

---

## File Structure

**Validation engine (new package)**
- Create: `backend/app/services/validation/__init__.py`
- Create: `backend/app/services/validation/execution_plan.py`
  DSL 公式 → 执行计划（抽象操作列表）。
- Create: `backend/app/services/validation/row_validator.py`
  逐行校验：列算术公式在每一行求值，比对实际值。
- Create: `backend/app/services/validation/aggregate_validator.py`
  汇总校验：SUM/AVG/COUNT 公式对指定行范围求值，比对实际值。
- Create: `backend/app/services/validation/validation_service.py`
  编排服务：读取规则 → 构建执行计划 → 执行校验 → 汇总结果。

**Schemas**
- Create: `backend/app/schemas/validation_schema.py`
  `ValidationIssue`（单条校验问题）、`ValidationResult`（任务级校验结果）。

**API**
- Modify: `backend/app/api/routes/tasks.py`
  新增 `POST /{task_id}/validate`。

**Testing**
- Create: `backend/tests/unit/test_execution_plan.py`
- Create: `backend/tests/unit/test_row_validator.py`
- Create: `backend/tests/unit/test_aggregate_validator.py`
- Create: `backend/tests/unit/test_validation_service.py`

**Documentation**
- Modify: `README.md`


### Task 1: 执行计划构建器

**Files:**
- Create: `backend/app/services/validation/__init__.py`
- Create: `backend/app/services/validation/execution_plan.py`
- Create: `backend/tests/unit/test_execution_plan.py`

- [ ] **Step 1: 写失败的测试**

```python
def test_build_column_arithmetic_plan():
    rule = {"formula_text": "col_Profit = col_Revenue - col_Cost", "formula_type": "column_arithmetic"}
    plan = build_execution_plan(rule, column_map={"Profit": 3, "Revenue": 1, "Cost": 2})
    
    assert plan.kind == "row_wise"
    assert plan.target_column_index == 3
    assert plan.operator == "-"
    assert plan.operand_indices == [1, 2]
```

- [ ] **Step 2: 实现执行计划**

`ExecutionPlan` 数据结构：
```python
class PlanKind:
    ROW_WISE = "row_wise"
    AGGREGATE = "aggregate"

class ExecutionPlan:
    kind: str                          # row_wise | aggregate
    target_column_index: int           # 目标列在 aligned_grid 中的索引
    operator: str | None               # + - * / 或 None（聚合）
    operand_indices: list[int]         # 运算数列的索引
    aggregate_func: str | None         # sum | avg | count
    row_start: int | None              # 聚合起始行（含表头偏移）
    row_end: int | None                # 聚合结束行
    step: int                          # 步长（聚合用）
    formula_text: str                  # 原始公式文本
```

核心逻辑：
- `column_arithmetic`: 解析 `col_X = col_Y op col_Z` → 提取列名 → 映射到 grid 索引
- `row_aggregation`: 解析 `row_X = sum(row_Y:row_Z)` → 映射行范围
- 不支持的公式类型（yoy/mom/share）→ 跳过（返回 None）

- [ ] **Step 3: 测试通过**


### Task 2: 逐行校验器

**Files:**
- Create: `backend/app/services/validation/row_validator.py`
- Create: `backend/tests/unit/test_row_validator.py`

- [ ] **Step 1: 写测试**

```python
def test_row_validator_finds_exact_mismatch():
    aligned_grid = [
        ["Region", "Revenue", "Cost", "Profit"],
        ["East", "100", "80", "20"],     # Profit 正确: 100-80=20
        ["West", "90", "70", "25"],      # Profit 错误: 90-70=20, 但显示 25
    ]
    plan = ExecutionPlan(kind="row_wise", target_column_index=3, 
                         operator="-", operand_indices=[1, 2], ...)
    issues = validate_rows(aligned_grid, [plan])
    
    assert len(issues) == 1
    assert issues[0]["row_index"] == 2
    assert issues[0]["col_index"] == 3
    assert issues[0]["expected_value"] == "20"
    assert issues[0]["actual_value"] == "25"
```

- [ ] **Step 2: 实现**

```python
def validate_rows(
    aligned_grid: list[list],
    plans: list[ExecutionPlan],
) -> list[dict[str, object]]:
```

对每个 `row_wise` 执行计划：
- 遍历数据行（跳过表头行）
- 提取操作数列的 Decimal 值
- 执行运算（+ - * /）
- 与目标列实际值比对
- 不一致 → 生成 `ValidationIssue`

- [ ] **Step 3: 边界处理**
  - 空值/非数值 → 跳过该行（不报错）
  - 除零 → 标记为 `division_by_zero`
  - 列索引越界 → 标记为 `invalid_column`

- [ ] **Step 4: 测试通过**


### Task 3: 汇总校验器

**Files:**
- Create: `backend/app/services/validation/aggregate_validator.py`
- Create: `backend/tests/unit/test_aggregate_validator.py`

- [ ] **Step 1: 写测试**

```python
def test_sum_validator_matches_total():
    aligned_grid = [
        ["Category", "Amount"],
        ["A", "100"],
        ["B", "200"],
        ["Total", "300"],     # 正确: 100+200=300
    ]
    plan = ExecutionPlan(kind="aggregate", target_column_index=1,
                         aggregate_func="sum", row_start=1, row_end=2, step=1)
    issues = validate_aggregates(aligned_grid, [plan])
    assert len(issues) == 0

def test_sum_validator_finds_mismatch():
    aligned_grid = [
        ["Category", "Amount"],
        ["A", "100"],
        ["B", "200"],
        ["Total", "500"],     # 错误: 100+200=300, 但显示 500
    ]
    plan = ExecutionPlan(kind="aggregate", target_column_index=1,
                         aggregate_func="sum", row_start=1, row_end=2, step=1)
    issues = validate_aggregates(aligned_grid, [plan])
    assert len(issues) == 1
    assert issues[0]["expected_value"] == "300"
    assert issues[0]["actual_value"] == "500"
```

- [ ] **Step 2: 实现**

```python
def validate_aggregates(
    aligned_grid: list[list],
    plans: list[ExecutionPlan],
) -> list[dict[str, object]]:
```

支持 `sum`、`avg`、`count` 三种聚合函数。

- [ ] **Step 3: 测试通过**


### Task 4: 校验编排服务 + API + Schema

**Files:**
- Create: `backend/app/services/validation/validation_service.py`
- Create: `backend/app/schemas/validation_schema.py`
- Modify: `backend/app/api/routes/tasks.py`
- Create: `backend/tests/unit/test_validation_service.py`

- [ ] **Step 1: 新增 Schema**

```python
class ValidationIssue(BaseModel):
    sheet_id: int
    sheet_name: str
    row_index: int         # 数据行号（从 1 开始，表头占第 1 行）
    col_index: int         # 列号（从 1 开始）
    expected_value: str    # 公式计算值
    actual_value: str      # 表格现存值
    formula_text: str      # 触发本条问题的公式
    severity: str          # "error" | "warning"
    issue_type: str        # "mismatch" | "division_by_zero" | "invalid_column" | "aggregate_mismatch"

class ValidationResult(BaseModel):
    task_id: int
    status: str
    total_issues: int
    error_count: int
    warning_count: int
    issues: list[ValidationIssue]
```

- [ ] **Step 2: 实现编排服务**

```python
def validate_task_formulas(
    task_id: int,
    db: Session,
) -> dict[str, object]:
```

流程：
1. 查询 task → 验证状态为 `confirmed` 或后续状态
2. 读取 formula_rules（只取 `verification_passed=True` 的）
3. 调用 `filter_formula_rules` 获取 passed 规则
4. 获取 aligned_grid（从最新的 structure_version）
5. 构建 column_map
6. 对每条规则调用 `build_execution_plan`
7. 分类：row_wise → `validate_rows`，aggregate → `validate_aggregates`
8. 汇总 `ValidationResult`

**关键安全约束**：
- 如果 task 状态为 `formula_gap_acknowledged`：返回空结果（`total_issues=0`），不报错
- 如果没有 aligned_grid（无结构版本）：返回 400

- [ ] **Step 3: 新增 API 端点**

`POST /api/tasks/{task_id}/validate`：
```python
@router.post("/{task_id}/validate", response_model=ValidationResult)
def validate_task(task_id: int, db: Session = Depends(get_db)) -> ValidationResult:
    payload = validation_service.validate_task_formulas(task_id, db)
    return ValidationResult(**payload)
```

- [ ] **Step 4: 写集成测试**

```python
def test_validate_returns_issues_for_mismatched_formula(tmp_path):
    ...

def test_validate_skips_gap_acknowledged_task(tmp_path):
    ...

def test_validate_requires_confirmed_task(tmp_path):
    ...
```

- [ ] **Step 5: 测试通过**


### Task 5: 全链路验证

- [ ] **Step 1: 全部测试**

```bash
cd backend && python -m pytest tests -v
```

- [ ] **Step 2: Ruff lint**

```bash
cd backend && python -m ruff check app tests
```

- [ ] **Step 3: 更新 README**

```markdown
## Day 15 校验引擎

- `POST /api/tasks/{task_id}/validate` — 执行公式校验，返回误差清单
```

- [ ] **Step 4: 审查 Day 16 边界**

确认 Day 15 只做了：
- DSL 转执行计划
- 逐行校验 + 汇总校验
- 校验结果以 JSON 返回

**不包含**（留给 Day 16）：
- 校验结果落库（`ValidationIssueRecord`）
- 历史版本管理
- 增量校验（只校验变更行）

---

## Self-Review

### Spec coverage
- `DSL 转执行计划`: Task 1（`execution_plan.py`）
- `逐行校验`: Task 2（`row_validator.py`）
- `汇总校验`: Task 3（`aggregate_validator.py`）

### 与 Day 14 的衔接
- 使用 Day 14 的 `filter_formula_rules` 获取 passed 规则
- 使用 Day 13 的 `FormulaParser` 解析 DSL
- 使用 Day 12 的 `FormulaType` 判断公式类型
- 使用 Day 10 的 structure_version 中的 `aligned_grid`
- 尊重 `formula_gap_acknowledged` 状态

### 安全原则
- 纯 Python 计算，无 LLM 调用
- 使用 Decimal 避免浮点精度问题
- 非数值/空值跳行不报错
- 只有明确不一致才报 error
