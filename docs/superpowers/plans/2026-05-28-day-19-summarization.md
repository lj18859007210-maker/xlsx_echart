# Day 19：摘要压缩

**日期：** 2026-05-28
**状态：** in_progress
**依赖：** Day 16（validation persistence）+ Day 17-18（anomaly detection）

---

## 目标

为 Day 20（AI 分析）生成精简上下文包，控制 token 预算，让 LLM 只看最有价值的数据而非整表。

---

## 四大组件

### 1. 统计摘要 (`summary_builder.py`)
对每列 measure 计算：均值、中位数、最小值、最大值、波动率(CV)、缺失率、趋势方向

### 2. 异常切片 (`slice_builder.py`)
- 从 validation_issues + anomaly_issues 提取命中行 ±1 行上下文
- 附带表头行，标注问题单元格坐标和原因标签

### 3. Token 估算 (`token_estimator.py`)
- `len(json) / 3.5` 近似（中英文混合）
- 设置 `TOKEN_BUDGET = 4000`

### 4. 裁剪策略 (内嵌于 `summarize_service.py`)
- 超预算时按 severity 优先级裁剪 slices（error > warning）
- 保留统计摘要 + semantic_schema（始终发送）

---

## 上下文包结构

```json
{
  "statistical_summary": { ... },
  "validation_issues_summary": { ... },
  "anomaly_summary": { ... },
  "slices": [ ... ],
  "semantic_schema": { ... },
  "token_estimate": 1500,
  "token_budget": 4000,
  "trimmed": false
}
```

---

## 数据模型

`summary_records` 表：id, task_id, summary_json, slice_json, token_estimate, created_at

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `app/db/models/summary_record.py` | NEW |
| `alembic/versions/20260528_0007_add_summary_records.py` | NEW |
| `app/db/base.py` | MOD |
| `app/services/summarize/__init__.py` | NEW |
| `app/services/summarize/summary_builder.py` | NEW |
| `app/services/summarize/slice_builder.py` | NEW |
| `app/services/summarize/token_estimator.py` | NEW |
| `app/services/summarize/summarize_service.py` | NEW |
| `app/schemas/summary_schema.py` | NEW |
| `app/api/routes/tasks.py` | MOD |
| `tests/unit/test_summarize_service.py` | NEW |