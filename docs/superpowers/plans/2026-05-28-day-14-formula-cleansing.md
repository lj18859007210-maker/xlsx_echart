# Day 14 公式兜底与清洗 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 Day 13 公式推导管线基础上，增加后置质量过滤、空规则集降级路径、以及全链路结构化审计日志，确保进入 Day 15 校验引擎的公式规则集具备企业级可靠性。

**Architecture:** Day 14 不引入新的 LLM 调用，只做确定性后处理。分为三层：质量过滤器（剔除低分/重复/冲突规则）→ 降级路由（处理零规则场景）→ 审计日志（全链路可观测）。

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Python stdlib `logging`

---

## File Structure

**Quality filter**
- Create: `backend/app/services/formula/formula_quality_filter.py`
  质量过滤器：最低分数阈值、去重、冲突检测。
- Modify: `backend/app/services/formula/__init__.py`
  导出新服务。

**Degradation endpoint**
- Create: `backend/app/services/formula/formula_rule_reader.py`
  规则读取服务：返回任务级别的规则摘要，含质量元数据。
- Modify: `backend/app/api/routes/tasks.py`
  新增 `GET /{task_id}/formula-rules` 和 `POST /{task_id}/formula-rules/acknowledge-gap`。
- Modify: `backend/app/schemas/task_schema.py`
  新增 `FormulaRuleListResponse`、`AcknowledgeGapRequest`。

**Audit logging**
- Modify: `backend/app/services/formula/formula_inference_service.py`
  在关键节点补全结构化日志：各阶段耗时、置信度分布、拒绝原因分类。
- Create: `backend/app/services/formula/audit_logger.py`
  统一审计日志格式，输出 JSON Lines。

**Testing**
- Create: `backend/tests/unit/test_formula_quality_filter.py`
  质量过滤单元测试：阈值过滤、去重、冲突检测、空集降级。
- Modify: `backend/tests/unit/test_task_review.py`
  新增 API 测试：公式规则查询、空集确认。
- Modify: `backend/tests/unit/test_formula_inference_service.py`
  补充日志输出验证。
- Modify: `README.md`
  Day 14 质量阈值配置文档。

---

### Task 1: 公式质量过滤器

**Files:**
- Create: `backend/app/services/formula/formula_quality_filter.py`
- Modify: `backend/app/services/formula/__init__.py`
- Create: `backend/tests/unit/test_formula_quality_filter.py`

- [ ] **Step 1: 写失败的测试**

```python
def test_filter_rejects_rules_below_quality_threshold():
    rules = [
        {"id": 1, "verification_score": 0.05, "formula_text": "col_C = col_A + col_B", ...},
        {"id": 2, "verification_score": 0.85, "formula_text": "col_D = col_A - col_B", ...},
    ]
    passed, filtered = filter_formula_rules(rules, quality_threshold=0.3)
    assert len(passed) == 1
    assert len(filtered) == 1
    assert passed[0]["id"] == 2
```

- [ ] **Step 2: 运行测试确认失败**

- [ ] **Step 3: 实现质量过滤器**

```python
def filter_formula_rules(
    rules: list[dict[str, object]],
    quality_threshold: float = 0.3,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
```

三个过滤维度：
1. **最低分数阈值**：`verification_score < quality_threshold` → 剔除
2. **去重**：同 sheet 内完全相同的 `formula_text` → 保留 confidence 最高的
3. **冲突检测**：同 sheet + 同目标列（等式左侧不同）→ 两条都标记为 `conflict`，不进校验引擎

- [ ] **Step 4: 运行测试确认通过**

- [ ] **Step 5: 导出到 `__init__.py`**

---

### Task 2: 规则读取与空集降级

**Files:**
- Create: `backend/app/services/formula/formula_rule_reader.py`
- Modify: `backend/app/schemas/task_schema.py`
- Modify: `backend/app/api/routes/tasks.py`
- Modify: `backend/tests/unit/test_task_review.py`

- [ ] **Step 1: 新增 schema**

```python
class FormulaRuleItem(BaseModel):
    id: int
    sheet_id: int
    formula_text: str
    formula_type: str
    confidence: float
    verification_score: float
    quality_status: str  # "passed" | "filtered_low_score" | "filtered_duplicate" | "conflict"

class FormulaRuleListResponse(BaseModel):
    task_id: int
    status: str
    total_inferred: int
    passed: int
    filtered: int
    conflict: int
    has_gap: bool  # True 如果 passed == 0
    rules: list[FormulaRuleItem]

class AcknowledgeGapRequest(BaseModel):
    acknowledged: bool = True
```

- [ ] **Step 2: 创建规则读取服务**

```python
def read_task_formula_rules(
    task_id: int,
    db: Session,
    quality_threshold: float = 0.3,
) -> dict[str, object]:
```

从 `formula_rules` 表读取 → 调用 `filter_formula_rules` → 返回 `FormulaRuleListResponse`。

- [ ] **Step 3: 新增 API 端点**

`GET /api/tasks/{task_id}/formula-rules`：返回过滤后的规则列表和质量统计。

`POST /api/tasks/{task_id}/formula-rules/acknowledge-gap`：
当 `has_gap == True` 时，用户确认「已知晓该任务无可用公式，跳过校验阶段」→ task status 标记为 `formula_gap_acknowledged`。

- [ ] **Step 4: 写 API 测试**

```python
def test_formula_rules_endpoint_returns_filtered_rules(tmp_path):
    ...

def test_formula_rules_has_gap_when_no_passing_rules(tmp_path):
    ...

def test_acknowledge_gap_marks_task(tmp_path):
    ...
```

- [ ] **Step 5: 运行测试确认通过**

---

### Task 3: 结构化审计日志

**Files:**
- Create: `backend/app/services/formula/audit_logger.py`
- Modify: `backend/app/services/formula/formula_inference_service.py`
- Modify: `backend/tests/unit/test_formula_inference_service.py`

- [ ] **Step 1: 创建审计日志器**

```python
# audit_logger.py
import json
import logging
import time
from typing import Any

logger = logging.getLogger("formula_audit")

def log_inference_start(task_id: int, sheet_count: int, model_name: str) -> int:
    """返回 start_ts 用于后续耗时计算"""
    ...

def log_inference_complete(
    task_id: int, start_ts: float, accepted: int, rejected: int,
    confidences: list[float], rejection_reasons: dict[str, int],
) -> None:
    """输出 JSON Lines 格式审计日志"""
    ...
```

日志 JSON 格式：
```json
{
  "event": "formula_inference_complete",
  "task_id": 42,
  "duration_ms": 1234,
  "accepted": 3,
  "rejected": 7,
  "confidence_p50": 0.82,
  "confidence_p90": 0.95,
  "rejection_reasons": {
    "parse_error": 2,
    "validation_failed": 3,
    "verification_zero": 2
  }
}
```

- [ ] **Step 2: 在编排服务中埋点**

在 `infer_task_formulas` 中：
- 开始处调用 `log_inference_start`
- 完成处统计 `confidences` 和 `rejection_reasons`，调用 `log_inference_complete`

- [ ] **Step 3: 添加日志验证测试**

```python
def test_audit_logger_emits_structured_json(caplog):
    ...
```

---

### Task 4: 全链路验证

- [ ] **Step 1: 运行全部测试**

```bash
cd backend && python -m pytest tests -v
```
Expected: PASS（新增模块不影响已有 75 个测试）

- [ ] **Step 2: Ruff lint**

```bash
cd backend && python -m ruff check app tests
```
Expected: 新增代码无 lint 错误

- [ ] **Step 3: 更新 README**

```markdown
## Day 14 公式兜底与清洗

环境变量（新增）：
- `FORMULA_QUALITY_THRESHOLD` - 公式质量最低分数阈值，默认 0.3

本地验证：
```bash
cd backend
python -m pytest tests/unit/test_formula_quality_filter.py -v
python -m pytest tests/unit/test_task_review.py -k formula_rules -v
```
```

- [ ] **Step 4: 审查 Day 15 边界**

确认 Day 14 只做了：
- 质量过滤（确定性后处理，无 LLM 调用）
- 空集降级路由（用户确认机制）
- 审计日志（可观测性）

不包含（留给 Day 15）：
- DSL 转执行计划
- 逐行/汇总校验
- 误差计算与定位

---

## Self-Review

### Spec coverage
- `过滤非法公式`: Task 1（阈值 + 去重 + 冲突检测）
- `为空规则集设计降级逻辑`: Task 2（`has_gap` + acknowledge 端点）
- `补充日志`: Task 3（结构化 JSON Lines 审计日志）

### Type consistency
- 过滤器输入/输出均为 `dict[str, object]`，与 Day 13 的 `formula_rules` 行格式一致
- API 返回 `FormulaRuleListResponse`，新增字段 `quality_status`、`has_gap`
- 不修改 `FormulaRuleRecordModel` 表结构（无需新迁移）
