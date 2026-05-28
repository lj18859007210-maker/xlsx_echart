# Day 20：AI 深度分析

**日期：** 2026-05-28
**状态：** in_progress
**依赖：** Day 19（摘要压缩完成）

---

## 目标

LLM 基于摘要包生成结构化商业分析报告，包含结论、风险、建议、图表提示，每条结论必须引用证据。

---

## 核心设计原则

1. **LLM 只看摘要包** — 不传原始数据，不传完整表格
2. **禁止虚构** — Prompt 明确要求每条结论引用来源指标/坐标
3. **Pydantic 校验** — LLM 输出先过 JSON Schema 校验，不合法直接拒绝
4. **高风险兜底** — 高风险结论自动附加"建议人工复核"
5. **Mockable LLM** — 测试用 Mock 客户端，生产用真实 API

---

## 数据模型

`insight_records`: id, task_id, version_no, executive_summary, key_findings_json, risks_json, recommendations_json, citations_json, model_name, created_at

---

## Prompt 设计（关键）

```
你是财务数据分析师。只基于下方的数据摘要包输出分析结论。

规则：
1. 每条结论必须引用来源（sheet名、指标名、行号、列号）
2. 不虚构数据。不确定时写"需要人工复核"
3. 高风险结论（critical severity）必须附加"建议人工复核"
4. 输出严格JSON

[上下文包嵌入]
```

---

## 文件清单

| 文件 | 操作 |
|------|------|
| `app/db/models/insight_record.py` | NEW |
| `alembic/versions/20260528_0008_add_insight_records.py` | NEW |
| `app/db/base.py` | MOD |
| `app/core/config.py` | MOD |
| `app/services/analysis/__init__.py` | NEW |
| `app/services/analysis/prompt_builder.py` | NEW |
| `app/services/analysis/llm_client.py` | NEW |
| `app/services/analysis/analysis_service.py` | NEW |
| `app/schemas/analysis_schema.py` | NEW |
| `app/api/routes/tasks.py` | MOD |
| `tests/unit/test_analysis_service.py` | NEW |