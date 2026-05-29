# Day 24：Mock 模式 + 配置整理
**日期：** 2026-05-31
**状态：** pending
**依赖：** Day 23（日志系统）

---

## 一、Mock 模式——无 LLM Key 也能跑通全流程

### 1.1 问题
当前管线中 3 个步骤依赖 LLM（推导公式、AI 分析、图表推荐），没有 API Key 时这些步骤会直接失败，无法展示完整流程。

### 1.2 方案
在 `.env` 中增加 `LLM_MOCK_MODE=true`，开启后 LLM 调用返回预设的模拟数据。

### 1.3 任务

**后端 Mock 服务：**
- [ ] 创建 `app/services/llm_client.py` — 统一 LLM 调用接口
  - 读取 `LLM_MOCK_MODE` 环境变量
  - mock 模式：返回预设 JSON（从 `tests/fixtures/` 加载）
  - 真实模式：调用 OpenAI API
- [ ] 创建 `tests/fixtures/mock_formula_rules.json` — 模拟公式规则数据
- [ ] 创建 `tests/fixtures/mock_insights.json` — 模拟 AI 分析数据
- [ ] 创建 `tests/fixtures/mock_chart_specs.json` — 模拟图表推荐数据
- [ ] 改造 3 个 LLM 相关 service 使用 `llm_client.py`
  - `backend/app/services/formula_inference.py`
  - `backend/app/services/ai_analysis.py`
  - `backend/app/services/chart_recommendation.py`

**涉及文件：**
| 文件 | 操作 |
|------|------|
| `backend/app/services/llm_client.py` | NEW |
| `backend/tests/fixtures/mock_formula_rules.json` | NEW |
| `backend/tests/fixtures/mock_insights.json` | NEW |
| `backend/tests/fixtures/mock_chart_specs.json` | NEW |
| `backend/app/services/formula_inference.py` | MOD |
| `backend/app/services/ai_analysis.py` | MOD |
| `backend/app/services/chart_recommendation.py` | MOD |

---

## 二、配置整理

### 2.1 `.env.example` 去重
**问题：** 既有旧 `LLM_API_KEY` 又有新 `FORMULA_LLM_*` / `ANALYSIS_LLM_*`，重复且混乱。

**任务：**
- [ ] 统一为以下结构：
```
# ---- LLM ----
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o
LLM_API_URL=https://api.openai.com/v1
LLM_MOCK_MODE=true
```
- [ ] 删除旧的分散配置（`FORMULA_LLM_*`、`ANALYSIS_LLM_*`）
- [ ] 确保所有 service 从统一配置读取
- [ ] 更新 `app/core/config.py` 读取新配置项

### 2.2 前端环境变量
- [ ] 创建 `frontend/.env.example`
  ```
  VITE_API_BASE_URL=http://localhost:8000/api
  ```

**涉及文件：**
| 文件 | 操作 |
|------|------|
| `.env.example` | MOD（去重整理） |
| `backend/app/core/config.py` | MOD（统一 LLM 配置） |
| `frontend/.env.example` | NEW |

---

## 三、Mock 模式端到端验证

**目标：** `LLM_MOCK_MODE=true` 时，上传 .xlsx → 管线 7 步全部走完 → 结果页有图表。

- [ ] 上传测试 .xlsx 文件
- [ ] 确认结构
- [ ] 管线 7 步全部显示 `done`（不依赖外部 API）
- [ ] 结果页显示模拟图表和 AI 分析
- [ ] 关闭 mock 模式时，恢复真实 API 调用

---

## 四、检查清单

- [ ] `LLM_MOCK_MODE=true` 时全流程走通
- [ ] Mock 数据合理且覆盖主要场景
- [ ] `.env.example` 简洁清晰无冗余
- [ ] 前端 `.env.example` 存在
- [ ] 后端测试 178 依然通过
- [ ] 新增 mock 相关测试
