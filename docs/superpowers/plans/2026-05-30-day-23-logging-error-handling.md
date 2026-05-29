# Day 23：日志系统 + 错误处理 + 管线容错
**日期：** 2026-05-30
**状态：** pending
**依赖：** Day 22（前后端功能完成）

---

## 一、后端日志系统

### 1.1 结构化日志
**目标：** 用 `structlog` 替换 `print` / `logging.info`，每条日志带 task_id、耗时、状态。

**任务：**
- [ ] 安装 `structlog`
- [ ] 创建 `app/core/logging.py` 配置模块
  - JSON 格式输出到 `logs/app.log`
  - 开发环境同时输出到控制台（可读格式）
  - 自动注入 `task_id`（从 contextvars 获取）
- [ ] 所有 router 添加请求日志中间件
  - 记录：method、path、status、duration_ms、task_id
- [ ] 所有 service 层关键操作加日志
  - 上传：file_name、file_size、upload_duration
  - 解析：sheet_count、cell_count、parse_duration
  - 公式推导：rule_count、gap_count
  - 校验：issue_count
  - 异常检测：anomaly_count
  - AI 分析：prompt_tokens、completion_tokens、duration
  - 图表推荐：chart_count

**涉及文件：**
| 文件 | 操作 |
|------|------|
| `backend/app/core/logging.py` | NEW |
| `backend/app/main.py` | MOD（注册中间件） |
| `backend/app/api/tasks.py` | MOD（添加日志） |
| `backend/app/api/files.py` | MOD（添加日志） |
| `backend/app/services/*.py` | MOD（关键服务加日志） |

### 1.2 错误处理中间件
**目标：** 统一异常处理，不要让 FastAPI 返回裸 traceback。

**任务：**
- [ ] 创建 `app/core/error_handler.py`
  - 捕获所有未处理异常
  - 返回统一 JSON：`{"detail": "...", "error_code": "...", "task_id": "..."}`
  - 区分：ValidationError（422）、NotFound（404）、InternalError（500）
- [ ] 在 `app/main.py` 注册异常处理器

---

## 二、管线容错

### 2.1 单步失败不阻塞后续
**目标：** 管线的 7 步中，某一步失败后，后续步骤仍可执行（标记为 skipped）。

**现状：** `usePipeline.ts` 中 `for` 循环 `break` 在失败时。

**任务：**
- [ ] 改 `usePipeline.ts` 的 `run()` 函数：单步失败后不 `break`，而是继续执行后续步骤
- [ ] 失败的步骤状态标记为 `failed`，后续依赖该步骤的标记为 `skipped`
- [ ] 添加步骤依赖声明：
  - `infer`（推导公式）→ 无依赖
  - `rules`（规则检查）→ 依赖 infer
  - `validate`（校验）→ 依赖 rules
  - `anomaly`（异常检测）→ 无依赖（可独立执行）
  - `summarize`（摘要）→ 无依赖
  - `analyze`（AI 分析）→ 无依赖
  - `chart`（图表推荐）→ 无依赖

### 2.2 后端管线执行器
**目标：** 在后端添加一个 `/api/tasks/{id}/run-pipeline` 端点，一键执行所有步骤，前端只需轮询状态。

**任务：**
- [ ] 创建 `app/services/pipeline_runner.py`
  - `run_full_pipeline(task_id)` — 依次执行 7 步
  - 每步结果写入 `pipeline_step_results` 表（JSON 字段或新表）
- [ ] 创建 `POST /api/tasks/{id}/run-pipeline` 端点
- [ ] 创建 `GET /api/tasks/{id}/pipeline-status` 端点（前端轮询）
- [ ] 前端 `usePipeline.ts` 改为轮询模式（POST 触发 → GET 轮询状态）

**涉及文件：**
| 文件 | 操作 |
|------|------|
| `backend/app/services/pipeline_runner.py` | NEW |
| `backend/app/api/tasks.py` | MOD |
| `frontend/src/modules/pipeline/usePipeline.ts` | MOD |

---

## 三、前端错误边界

### 3.1 组件级错误边界
**目标：** 每个页面有独立的 ErrorBoundary，异常时显示友好提示而不是白屏。

**任务：**
- [ ] 创建 `frontend/src/components/ErrorBoundary.tsx`
  - 捕获子组件渲染错误
  - 显示"页面出错了" + 错误信息 + 重试按钮
- [ ] 在 App.tsx 中包裹每个 phase 的组件

### 3.2 API 请求统一错误处理
**任务：**
- [ ] 创建 `frontend/src/modules/api-client.ts`
  - 封装 `fetch`，统一处理：
    - 网络错误 → "无法连接服务器，请确认后端已启动"
    - 4xx → 显示后端返回的 detail
    - 5xx → "服务器内部错误，请稍后重试"
  - 超时设置（30s）
- [ ] 改造所有 hook 使用 `api-client.ts`

**涉及文件：**
| 文件 | 操作 |
|------|------|
| `frontend/src/components/ErrorBoundary.tsx` | NEW |
| `frontend/src/modules/api-client.ts` | NEW |
| `frontend/src/App.tsx` | MOD |
| `frontend/src/modules/upload/useFileUpload.ts` | MOD |
| `frontend/src/modules/review-grid/useTaskReview.ts` | MOD |
| `frontend/src/modules/pipeline/usePipeline.ts` | MOD |
| `frontend/src/modules/results/useResultsData.ts` | MOD |

---

## 四、检查清单

- [ ] 后端所有 API 请求有结构化日志
- [ ] 异常统一返回 JSON（不暴露 traceback）
- [ ] 管线单步失败不阻塞后续
- [ ] 前端组件崩溃不白屏
- [ ] API 请求失败有中文错误提示
- [ ] 前后端测试全部通过

---

## 文件变更汇总

| 文件 | 操作 |
|------|------|
| `backend/app/core/logging.py` | NEW |
| `backend/app/core/error_handler.py` | NEW |
| `backend/app/services/pipeline_runner.py` | NEW |
| `backend/app/main.py` | MOD |
| `backend/app/api/tasks.py` | MOD |
| `backend/app/api/files.py` | MOD |
| `backend/app/services/*.py` | MOD（加日志） |
| `frontend/src/components/ErrorBoundary.tsx` | NEW |
| `frontend/src/modules/api-client.ts` | NEW |
| `frontend/src/App.tsx` | MOD |
| `frontend/src/modules/**/use*.ts` | MOD（用 api-client） |
