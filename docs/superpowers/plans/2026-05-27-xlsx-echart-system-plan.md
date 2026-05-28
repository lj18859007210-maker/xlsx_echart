# 表格分析与图表系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个从表格输入、结构识别、人工确认、公式校验、异常检测、AI 分析到图表输出的完整系统，并保证结果可解释、可追踪、可扩展。

**Architecture:** 采用“LLM 做理解与解释、Python 做确定性计算、前端承接人工确认”的混合架构。第一版优先支持 Excel/规则化表格，保留 OCR 图片表格扩展位；所有高风险自动判断都必须有结构化输出和可回溯日志。

**Tech Stack:** `FastAPI`、`Pandas`、`Pydantic`、`OpenPyXL`、`ECharts`、`Vue/React`、`SQLite/PostgreSQL`、`Redis(可选)`、`LLM API`

---

### Task 1: 冻结需求与边界

**目标：** 先把“第一版做什么、不做什么”写死，避免后面返工。

- [ ] 明确第一版输入范围：优先支持 `.xlsx`，暂不把 OCR 图片识别作为第一阶段必做项。
- [ ] 明确第一版输出范围：必须包含 `清洗后的表格视图`、`校验错误清单`、`异常清单`、`分析结论`、`图表推荐与渲染结果`。
- [ ] 明确第一版场景范围，覆盖四个核心场景：
  1. **通用经营分析表**（默认基座）：任何"维度列 + 指标列"的二维经营数据表——按区域/产品/月份统计的收入、成本、利润、费用等，支持跨列公式校验和趋势异常检测。
  2. **通信运营商**：省份x用户数xARPUx收入x掉线率等关键运营指标，公式校验（收入=用户数xARPU）、离群值检测（某省掉线率异常偏高）、趋势预警（ARPU连续下滑）。
  3. **互联网运营**：渠道x曝光量x点击率x转化率xGMVx获客成本等增长指标体系，转化漏斗校验、渠道ROI对比、结构占比异常（某渠道GMV占比突变）。
  4. **监控运维**：服务名xCPU%x内存xQPSxP99延迟x错误率等SLA指标，性能劣化检测（延迟突增>300%）、流量异常（QPS连续3期下降）、热点识别（IQR标记极端CPU/内存）。
- [ ] 定义不做项：暂不做多租户、复杂权限、移动端、批量异步大规模任务编排、可视化规则编排器。
- [ ] 产出一份 `需求冻结清单`，至少包含：用户角色、输入格式、处理链路、输出物、异常处理、验收标准。

### Task 2: 设计系统总模块

**目标：** 把文档中的“六阶段”翻译成真正可开发的模块边界。

- [ ] 拆分 8 个核心模块：`文件接入模块`、`表格解析模块`、`Gate 1 纠错模块`、`公式推导模块`、`校验引擎模块`、`异常检测模块`、`AI 分析模块`、`图表生成模块`。
- [ ] 定义每个模块的输入输出 JSON 结构，避免模块间直接传 DataFrame 以外的隐式状态。
- [ ] 确定统一任务主线：`upload -> parse -> confirm -> infer-formula -> validate -> detect-anomaly -> summarize -> analyze -> chart`。
- [ ] 设计任务状态机：`uploaded`、`parsed`、`waiting_confirm`、`confirmed`、`validated`、`analyzed`、`chart_ready`、`failed`。
- [ ] 设计错误码规范，至少区分：上传错误、解析错误、结构错误、公式推导错误、分析错误、图表错误。

### Task 3: 设计数据模型

**目标：** 先定义数据结构，再开始写任何实现。

- [ ] 设计 `FileRecord`：记录原始文件路径、文件类型、上传时间、任务状态。
- [ ] 设计 `SheetRecord`：记录工作表名、原始尺寸、解析后的网格信息。
- [ ] 设计 `CellRecord`：记录行列坐标、原始值、标准化值、单元格类型、是否合并、合并范围。
- [ ] 设计 `StructureVersion`：记录每次 Gate 1 用户纠错后的网格版本，保证可回滚。
- [ ] 设计 `FormulaRule`：记录 LLM 推导出的公式、公式说明、作用范围、可信度、版本号。
- [ ] 设计 `ValidationIssue` 与 `AnomalyIssue`：记录问题类型、严重级别、定位坐标、原因说明。
- [ ] 设计 `InsightRecord`：记录 AI 结论、建议、引用数据点、关联图表。
- [ ] 设计 `ChartSpec`：统一图表配置格式，建议采用 ECharts option 的受控子集。

### Task 4: 搭建项目骨架

**目标：** 先搭建可持续扩展的目录，不把逻辑堆在一起。

- [ ] 创建后端目录：`backend/app/api`、`backend/app/services`、`backend/app/domain`、`backend/app/repositories`、`backend/app/schemas`。
- [ ] 创建前端目录：`frontend/src/pages`、`frontend/src/components`、`frontend/src/modules/review-grid`、`frontend/src/modules/chart-panel`。
- [ ] 创建共享文档目录：`docs/api`、`docs/data-contracts`、`docs/prompts`、`docs/test-cases`。
- [ ] 创建测试目录：`backend/tests/unit`、`backend/tests/integration`、`frontend/tests`。
- [ ] 建立 `.env.example`，列出数据库、对象存储、LLM、日志等配置项。

### Task 5: 实现文件接入与基础解析

**目标：** 先让系统稳定接收 Excel 并抽出结构化表格。

- [ ] 实现文件上传接口：支持单文件上传、基本格式校验、大小限制、任务 ID 返回。
- [ ] 实现 Excel 读取服务：读取 workbook、sheet 列表、单元格值、合并区域、基础样式信息。
- [ ] 实现初步二维矩阵转换：把每个 sheet 转成统一网格对象，而不是直接交给后续模块处理原始库对象。
- [ ] 保留原始坐标与显示值，避免标准化过程中丢失上下文。
- [ ] 增加空表、超大表、多 sheet、隐藏 sheet 的边界处理。

### Task 6: 实现“双轨制”结构对齐

**目标：** 按你的 md 把“维度复制、数值留空”真正落地。

- [ ] 编写单元格分类器：先粗分为 `dimension`、`measure`、`empty`、`unknown`。
- [ ] 对表头/维度合并单元格执行 padding：向右、向下填充继承值。
- [ ] 对数值类合并单元格执行保守策略：仅左上角保留值，其余写 `NaN`。
- [ ] 设计可配置策略项：为未来支持“按比例拆分”预留接口，但第一版默认关闭。
- [ ] 输出结构对齐后的临时矩阵，并保留原始映射关系，保证后续能高亮回原单元格。
- [ ] 建立这一步的对比测试集：至少覆盖横向合并、纵向合并、标题+数值混合合并三类表。

### Task 7: 实现 Gate 1 人工确认界面

**目标：** 把错误拦在最前面，这是整套系统准确率的关键。

- [ ] 设计预览页面：左侧原表/截图，右侧结构化网格预览。
- [ ] 提供最小可用编辑能力：行列线微调、单元格合并、单元格拆分、表头区标记、数据区标记。
- [ ] 每次编辑都产生新的 `StructureVersion`，不覆盖旧版本。
- [ ] 用户点击“确认结构”后，才允许进入公式推导和分析阶段。
- [ ] 明确这一步的验收标准：用户能在 1-3 分钟内完成单张表结构校正。
- [ ] 记录所有人工操作日志，为后续优化自动识别提供样本。

### Task 8: 实现多级表头解析

**目标：** 把表格变成机器可理解的维度-指标模型。

- [ ] 提取层级表头树，识别时间、地区、部门、产品、指标等候选维度。
- [ ] 建立列语义映射：每一列都要有“上层表头路径 + 当前列名 + 推测指标类型”。
- [ ] 建立行语义映射：识别总计、分项、子项、期间等关系。
- [ ] 对无法确定的列标记 `unknown_semantic`，不要强行猜。
- [ ] 输出统一的 `semantic_schema.json`，供公式推导和图表推荐复用。

### Task 9: 实现 AI 动态公式推导

**目标：** 让 LLM 只负责“推导候选关系”，不直接碰业务结果。

- [ ] 设计严格的 Prompt：输入仅包含多级表头结构、少量样本行、允许的公式语法说明。
- [ ] 限制输出格式为 JSON，字段至少包含：`formula`、`description`、`scope`、`confidence`、`rule_type`。
- [ ] 设计可解析的公式 DSL，不要直接执行自然语言。
- [ ] 为公式类型分层：列间关系、行间汇总、同比环比、占比、差值。
- [ ] 加入格式校验器：如果 LLM 输出不合法，必须要求重试或降级为空规则集。
- [ ] 保存全部提示词、响应、解析结果，便于后期调优。

### Task 10: 实现 Python 校验引擎

**目标：** 所有“对不对”的判断由确定性代码负责。

- [ ] 把公式 DSL 翻译成受控执行计划，不允许任意代码执行。
- [ ] 对列公式执行逐行校验，对行公式执行聚合校验。
- [ ] 处理浮点误差：定义统一容差，比如 `abs(actual - expected) <= epsilon`。
- [ ] 输出 `ValidationIssue`，包括单元格位置、期望值、实际值、偏差值、命中公式。
- [ ] 对无法执行的公式给出明确失败原因，不静默忽略。
- [ ] 编写一套标准测试表，确保“收入-成本=利润”“分项求和=总计”等规则可稳定跑通。

### Task 11: 实现混合异常检测

**目标：** 按样本量自动选择算法，降低误报。

- [ ] 先实现业务规则版异常检测，这是第一版主干。
- [ ] 业务规则至少包含：异常增长率、连续下滑、负值异常、零值异常、结构占比突变。
- [ ] 当有效样本数 `N >= 30` 时，再启用统计模型，如 IQR。
- [ ] 统计模型输出不能直接给用户，必须和业务规则结果一起合并并标记来源。
- [ ] 为每条异常生成人类可读理由，避免只返回“异常分数”。
- [ ] 记录误报样本，后续再评估是否引入 Isolation Forest 等更复杂模型。

### Task 12: 实现摘要压缩

**目标：** 控制上下文大小，让 LLM 只看有价值的数据。

- [ ] 生成统计摘要：均值、中位数、最大最小值、波动率、缺失率、Top 异常指标。
- [ ] 生成异常切片：只截取命中问题的行、列、邻近上下文。
- [ ] 为每条切片补充原因标签：`公式错误`、`增长异常`、`汇总不一致` 等。
- [ ] 设计统一上下文包结构：`summary + validation_issues + anomaly_slices + semantic_schema`。
- [ ] 设置大小上限，超过上限时按重要性裁剪，而不是把整表塞给模型。

### Task 13: 实现 AI 深度分析

**目标：** 让 LLM 产出“解释和建议”，而不是重新做计算。

- [ ] 设计分析 Prompt：要求模型只能基于摘要包输出结论、风险、建议、待确认项。
- [ ] 输出强约束 JSON：`executive_summary`、`key_findings`、`risks`、`recommendations`、`chart_hints`。
- [ ] 明确禁止模型虚构不存在的数据点，要求每条结论引用来源单元格或指标。
- [ ] 对高风险结论设置兜底文案，如“建议人工复核”。
- [ ] 建立分析质量评估集，人工检查是否存在胡编、过度推断、遗漏重点。

### Task 14: 实现图表推荐与渲染

**目标：** 图表必须稳定、可解释、可复现。

- [ ] 先做规则驱动图表选择：趋势用折线，结构占比用柱状/堆叠柱，排名用条形，构成用饼图需谨慎。
- [ ] 把 LLM 的 `chart_hints` 作为建议，而不是直接决定图表。
- [ ] 生成统一 `ChartSpec`，并由前端转换成 ECharts option。
- [ ] 每张图都显示图表标题、数据来源、筛选条件、异常高亮说明。
- [ ] 对无法生成图的场景给出原因，如“缺少时间维度，无法生成趋势图”。

### Task 15: 实现结果页与可追溯能力

**目标：** 用户不仅要看到结论，还要能追到证据。

- [ ] 结果页展示顺序建议为：概览结论 -> 问题清单 -> 图表 -> 原始表定位。
- [ ] 点击异常项时，能高亮原始单元格或对应行列。
- [ ] 点击分析结论时，能看到引用的数据来源。
- [ ] 保留每次任务的结构版本、公式版本、分析版本，确保结果可复盘。

### Task 16: 实现测试体系

**目标：** 没有测试集，这套系统后面一定会飘。

- [ ] 建立最小样本库：正常表、汇总错误表、增长异常表、复杂表头表、合并单元格表。
- [ ] 为解析、双轨填充、公式推导解析、校验引擎、异常检测分别写单元测试。
- [ ] 为完整链路写集成测试：上传 -> 解析 -> 确认 -> 校验 -> 分析 -> 出图。
- [ ] 建立人工验收清单：结果是否可解释、定位是否准确、图表是否合理。
- [ ] 每次新增行业规则，都必须补对应样本表。

### Task 17: 实现日志、监控与失败兜底

**目标：** 让系统出了问题时能定位，而不是“黑盒报错”。

- [ ] 记录每个阶段的输入摘要、输出摘要、耗时、失败原因。
- [ ] 为 LLM 调用记录 token、模型名、重试次数、结构化解析结果。
- [ ] 实现阶段性失败兜底：公式推导失败时仍允许继续做基础异常检测；图表失败时仍输出文本分析。
- [ ] 增加后台任务详情页或日志查询能力，便于排查。

### Task 18: 制定迭代路线

**目标：** 第一版先可用，再逐步增强。

- [ ] 第一里程碑：仅支持 Excel，跑通主链路。
- [ ] 第二里程碑：补上 OCR 图片表格识别，并复用同一 Gate 1 纠错层。
- [ ] 第三里程碑：沉淀行业规则包，如财务、销售、库存。
- [ ] 第四里程碑：引入异步任务队列、批量处理、权限与审计。
- [ ] 第五里程碑：积累人工修正数据，反哺结构识别和公式推导模型。

### 验收标准

- [ ] 上传一个标准 Excel 后，系统能在可接受时间内输出结构化结果、问题列表、分析文本和至少 1 张合理图表。
- [ ] 合并单元格不会导致求和翻倍。
- [ ] 用户能在 Gate 1 页面修正错误结构并重新推进流程。
- [ ] 公式校验结果可以追溯到具体规则和具体单元格。
- [ ] 异常结论具备可读原因，不是单纯分数。
- [ ] 图表有明确来源和解释，不是“为了出图而出图”。
- [ ] 任意阶段失败时，系统能给出明确错误说明和当前可继续的最小结果。

### 推荐开发顺序

- [ ] 第 1 周：需求冻结、数据模型、项目骨架、上传解析。
- [ ] 第 2 周：双轨填充、Gate 1 结构确认。
- [ ] 第 3 周：多级表头解析、公式 DSL、LLM 公式推导。
- [ ] 第 4 周：Python 校验引擎、异常检测。
- [ ] 第 5 周：摘要压缩、AI 分析、图表生成。
- [ ] 第 6 周：结果页联动、日志监控、测试补齐、试运行。

### 风险提示

- [ ] 最大风险不是模型能力，而是前置结构识别不准，所以 Gate 1 必须优先做。
- [ ] 第二风险是公式 DSL 设计过松，导致校验引擎不稳定。
- [ ] 第三风险是想一版吃下 OCR、任意表格、多行业规则，范围过大。
- [ ] 最稳妥的策略是先把 Excel 主链路做准，再逐步扩大输入范围。

---

## 附录 A：推荐项目目录结构

```text
xlsx_echart/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  │  ├─ routes/
│  │  │  │  ├─ files.py
│  │  │  │  ├─ tasks.py
│  │  │  │  ├─ review.py
│  │  │  │  ├─ formulas.py
│  │  │  │  ├─ analysis.py
│  │  │  │  └─ charts.py
│  │  │  └─ deps.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  ├─ logger.py
│  │  │  └─ errors.py
│  │  ├─ domain/
│  │  │  ├─ entities/
│  │  │  ├─ enums/
│  │  │  └─ value_objects/
│  │  ├─ repositories/
│  │  │  ├─ file_repo.py
│  │  │  ├─ task_repo.py
│  │  │  ├─ structure_repo.py
│  │  │  ├─ formula_repo.py
│  │  │  ├─ issue_repo.py
│  │  │  └─ result_repo.py
│  │  ├─ schemas/
│  │  │  ├─ file_schema.py
│  │  │  ├─ task_schema.py
│  │  │  ├─ grid_schema.py
│  │  │  ├─ formula_schema.py
│  │  │  ├─ issue_schema.py
│  │  │  ├─ insight_schema.py
│  │  │  └─ chart_schema.py
│  │  ├─ services/
│  │  │  ├─ ingest/
│  │  │  │  ├─ file_store_service.py
│  │  │  │  ├─ excel_reader_service.py
│  │  │  │  └─ workbook_normalizer.py
│  │  │  ├─ parse/
│  │  │  │  ├─ grid_builder.py
│  │  │  │  ├─ merged_cell_resolver.py
│  │  │  │  ├─ cell_classifier.py
│  │  │  │  └─ header_tree_builder.py
│  │  │  ├─ review/
│  │  │  │  ├─ structure_patch_service.py
│  │  │  │  └─ structure_version_service.py
│  │  │  ├─ formula/
│  │  │  │  ├─ formula_prompt_builder.py
│  │  │  │  ├─ formula_inference_service.py
│  │  │  │  ├─ formula_parser.py
│  │  │  │  └─ formula_validator.py
│  │  │  ├─ validation/
│  │  │  │  ├─ execution_planner.py
│  │  │  │  ├─ dataframe_validator.py
│  │  │  │  └─ tolerance.py
│  │  │  ├─ anomaly/
│  │  │  │  ├─ rule_detector.py
│  │  │  │  ├─ stat_detector.py
│  │  │  │  └─ anomaly_merger.py
│  │  │  ├─ summary/
│  │  │  │  ├─ summary_builder.py
│  │  │  │  └─ anomaly_slice_builder.py
│  │  │  ├─ analysis/
│  │  │  │  ├─ analysis_prompt_builder.py
│  │  │  │  ├─ insight_service.py
│  │  │  │  └─ citation_mapper.py
│  │  │  └─ chart/
│  │  │     ├─ chart_rule_selector.py
│  │  │     ├─ chart_spec_builder.py
│  │  │     └─ echarts_adapter.py
│  │  ├─ db/
│  │  │  ├─ base.py
│  │  │  ├─ session.py
│  │  │  └─ models/
│  │  └─ main.py
│  └─ tests/
├─ frontend/
│  ├─ src/
│  │  ├─ api/
│  │  ├─ pages/
│  │  ├─ modules/
│  │  ├─ components/
│  │  ├─ store/
│  │  ├─ types/
│  │  └─ utils/
│  └─ tests/
├─ sample_data/
├─ docs/
│  ├─ api/
│  ├─ data-contracts/
│  ├─ prompts/
│  ├─ test-cases/
│  └─ superpowers/
└─ scripts/
```

**目录设计原则：**

- [ ] `services` 按业务链路拆，不要把所有逻辑塞进一个 `analysis_service.py`。
- [ ] `schemas` 只放接口和模块间契约，不放业务逻辑。
- [ ] `repositories` 负责存取，不直接做算法判断。
- [ ] 前端 `modules` 按功能拆：上传、结构纠错、结果展示、图表面板。

---

## 附录 B：后端接口清单

### 1. 文件上传与任务初始化

**`POST /api/files/upload`**

**用途：** 上传 Excel 文件并初始化任务。

**请求：**

- [ ] `multipart/form-data`
- [ ] 字段：`file`
- [ ] 可选字段：`project_name`

**响应示例：**

```json
{
  "file_id": "file_001",
  "task_id": "task_001",
  "status": "uploaded",
  "message": "file uploaded successfully"
}
```

### 2. 解析文件

**`POST /api/tasks/{task_id}/parse`**

**用途：** 读取 Excel，生成初始网格、sheet 信息和临时结构。

**响应示例：**

```json
{
  "task_id": "task_001",
  "status": "waiting_confirm",
  "sheets": [
    {
      "sheet_id": "sheet_001",
      "sheet_name": "经营分析",
      "row_count": 28,
      "col_count": 12
    }
  ]
}
```

### 3. 获取结构预览

**`GET /api/tasks/{task_id}/review`**

**用途：** 获取 Gate 1 页面所需原始网格、对齐网格、合并信息、编辑元数据。

**响应必须包含：**

- [ ] 原始单元格列表
- [ ] 对齐后网格
- [ ] 合并区域信息
- [ ] 维度区/数据区候选标注
- [ ] 当前 `structure_version`

### 4. 提交结构纠错

**`POST /api/tasks/{task_id}/review/patch`**

**用途：** 保存用户对网格的修改。

**请求示例：**

```json
{
  "base_version": 1,
  "operations": [
    {
      "type": "merge_cells",
      "range": "B2:D2"
    },
    {
      "type": "mark_header_region",
      "range": "A1:L3"
    },
    {
      "type": "split_cell",
      "cell": "A5"
    }
  ]
}
```

**响应示例：**

```json
{
  "task_id": "task_001",
  "structure_version": 2,
  "status": "waiting_confirm"
}
```

### 5. 确认结构

**`POST /api/tasks/{task_id}/review/confirm`**

**用途：** 用户确认结构后放行后续流程。

**响应：**

```json
{
  "task_id": "task_001",
  "status": "confirmed"
}
```

### 6. 公式推导

**`POST /api/tasks/{task_id}/infer-formulas`**

**用途：** 调用 LLM 生成结构化公式规则。

**响应必须包含：**

- [ ] `formula_version`
- [ ] 规则数量
- [ ] 无法解析的规则数量
- [ ] 降级状态

### 7. 执行公式校验

**`POST /api/tasks/{task_id}/validate`**

**用途：** 运行 Python 校验引擎。

**响应示例：**

```json
{
  "task_id": "task_001",
  "status": "validated",
  "validation_issue_count": 3
}
```

### 8. 执行异常检测

**`POST /api/tasks/{task_id}/detect-anomalies`**

**用途：** 按样本量和规则执行异常检测。

**响应字段：**

- [ ] `anomaly_issue_count`
- [ ] `detection_mode`
- [ ] `rule_hits`
- [ ] `stat_hits`

### 9. 生成摘要包

**`POST /api/tasks/{task_id}/summarize`**

**用途：** 生成 AI 分析的精简上下文。

### 10. 生成 AI 分析

**`POST /api/tasks/{task_id}/analyze`**

**用途：** 生成结构化洞察。

**响应字段：**

- [ ] `executive_summary`
- [ ] `key_findings`
- [ ] `risks`
- [ ] `recommendations`
- [ ] `chart_hints`

### 11. 生成图表

**`POST /api/tasks/{task_id}/charts`**

**用途：** 根据规则和分析提示生成图表配置。

### 12. 获取完整结果

**`GET /api/tasks/{task_id}/result`**

**用途：** 聚合返回前端结果页所需全部数据。

**响应块建议：**

- [ ] `task_meta`
- [ ] `sheet_overview`
- [ ] `validation_issues`
- [ ] `anomaly_issues`
- [ ] `insights`
- [ ] `charts`
- [ ] `trace_links`

### 13. 查询任务状态

**`GET /api/tasks/{task_id}/status`**

**用途：** 前端轮询任务处理进度。

**状态推进建议：**

```text
uploaded
parsed
waiting_confirm
confirmed
formula_inferred
validated
anomalies_detected
summarized
analyzed
chart_ready
failed
```

---

## 附录 C：数据库表设计建议

### 1. `files`

```sql
id varchar primary key
original_name varchar not null
file_type varchar not null
storage_path varchar not null
file_size bigint not null
created_at datetime not null
```

### 2. `tasks`

```sql
id varchar primary key
file_id varchar not null
status varchar not null
current_stage varchar not null
error_code varchar null
error_message text null
created_at datetime not null
updated_at datetime not null
```

### 3. `sheets`

```sql
id varchar primary key
task_id varchar not null
sheet_name varchar not null
sheet_index int not null
row_count int not null
col_count int not null
is_hidden boolean not null default false
```

### 4. `cells`

```sql
id varchar primary key
sheet_id varchar not null
row_index int not null
col_index int not null
address varchar not null
raw_value text null
normalized_value text null
value_type varchar not null
cell_role varchar not null
merge_range varchar null
```

### 5. `structure_versions`

```sql
id varchar primary key
task_id varchar not null
version_no int not null
source varchar not null
grid_snapshot_json text not null
operations_json text not null
created_at datetime not null
```

### 6. `formula_rules`

```sql
id varchar primary key
task_id varchar not null
version_no int not null
rule_type varchar not null
formula_text text not null
formula_dsl text not null
description text not null
scope_json text not null
confidence decimal(5,4) null
parse_status varchar not null
```

### 7. `validation_issues`

```sql
id varchar primary key
task_id varchar not null
sheet_id varchar not null
issue_type varchar not null
severity varchar not null
cell_address varchar not null
expected_value decimal(20,6) null
actual_value decimal(20,6) null
diff_value decimal(20,6) null
reason text not null
formula_rule_id varchar null
```

### 8. `anomaly_issues`

```sql
id varchar primary key
task_id varchar not null
sheet_id varchar not null
issue_type varchar not null
severity varchar not null
metric_name varchar not null
cell_address varchar not null
detection_source varchar not null
reason text not null
score decimal(10,4) null
```

### 9. `summaries`

```sql
id varchar primary key
task_id varchar not null
summary_json text not null
slice_json text not null
token_estimate int not null
created_at datetime not null
```

### 10. `insights`

```sql
id varchar primary key
task_id varchar not null
version_no int not null
executive_summary text not null
key_findings_json text not null
risks_json text not null
recommendations_json text not null
citations_json text not null
model_name varchar not null
```

### 11. `chart_specs`

```sql
id varchar primary key
task_id varchar not null
chart_type varchar not null
title varchar not null
spec_json text not null
source_json text not null
display_order int not null
```

### 12. `stage_logs`

```sql
id varchar primary key
task_id varchar not null
stage_name varchar not null
status varchar not null
input_digest text null
output_digest text null
duration_ms int null
message text null
created_at datetime not null
```

**建表原则：**

- [ ] 原始数据和推导结果分表存储，不要混在一张大表里。
- [ ] 所有 AI 结果都要有 `version_no`，方便重跑和比对。
- [ ] 所有问题项都要能回溯到 `task_id + sheet_id + cell_address`。

---

## 附录 D：核心模块内部处理步骤

### 1. Excel 解析模块内部步骤

- [ ] 接收文件路径。
- [ ] 校验扩展名与 MIME。
- [ ] 使用 `OpenPyXL` 读取 workbook。
- [ ] 遍历所有 sheet，跳过空白尾区。
- [ ] 抽取 `value`、`number_format`、`merged_cells`、`row_dimensions`、`column_dimensions`。
- [ ] 生成标准单元格对象列表。
- [ ] 生成初始网格快照。
- [ ] 写入 `files`、`tasks`、`sheets`、`cells`。

### 2. 双轨对齐模块内部步骤

- [ ] 读取某个 sheet 的单元格矩阵。
- [ ] 识别合并区域。
- [ ] 通过规则判断合并单元格是维度还是数值。
- [ ] 若是维度，进行 padding。
- [ ] 若是数值，仅保留左上值，其余记空。
- [ ] 重新生成逻辑网格。
- [ ] 产出“原始地址 -> 对齐后坐标”的映射表。

### 3. Gate 1 模块内部步骤

- [ ] 拉取当前结构版本。
- [ ] 渲染原始网格和逻辑网格。
- [ ] 前端执行用户编辑操作。
- [ ] 生成 patch 操作列表。
- [ ] 后端校验 patch 合法性。
- [ ] 保存新版本。
- [ ] 用户确认后更新任务状态为 `confirmed`。

### 4. 公式推导模块内部步骤

- [ ] 读取 `semantic_schema`。
- [ ] 采样几行代表数据。
- [ ] 组装 Prompt。
- [ ] 请求 LLM。
- [ ] 校验返回 JSON。
- [ ] 将自然语言公式转换为 DSL。
- [ ] 过滤低可信或无法解析规则。
- [ ] 存表并产出公式版本号。

### 5. 校验引擎模块内部步骤

- [ ] 读取公式规则。
- [ ] 将 DSL 转换为执行计划。
- [ ] 对列关系执行逐行校验。
- [ ] 对汇总关系执行按范围聚合校验。
- [ ] 应用容差比较。
- [ ] 生成问题项并落库。

### 6. 异常检测模块内部步骤

- [ ] 选择分析指标列。
- [ ] 统计有效样本数。
- [ ] `N < 30` 走规则引擎。
- [ ] `N >= 30` 先走规则，再走统计模型。
- [ ] 合并结果。
- [ ] 去重并排序。
- [ ] 输出用户可读原因。

### 7. 摘要压缩模块内部步骤

- [ ] 汇总关键统计量。
- [ ] 聚合校验问题。
- [ ] 聚合异常问题。
- [ ] 抽取最重要的上下文切片。
- [ ] 估算 token 体积。
- [ ] 超限则按优先级裁剪。

### 8. AI 分析模块内部步骤

- [ ] 读取摘要包。
- [ ] 组装分析 Prompt。
- [ ] 请求 LLM。
- [ ] 校验结构化 JSON。
- [ ] 建立结论与数据点引用关系。
- [ ] 落库存档。

### 9. 图表模块内部步骤

- [ ] 读取 `semantic_schema`、摘要、分析提示。
- [ ] 用规则选图。
- [ ] 生成 `ChartSpec`。
- [ ] 用前端 `ECharts` 适配器渲染。
- [ ] 回写图表结果与数据来源。

---

## 附录 E：前端页面清单与交互流程

### 页面 1：上传页

**功能：**

- [ ] 文件选择/拖拽上传
- [ ] 上传进度
- [ ] 上传结果提示
- [ ] 进入任务详情

**组件：**

- [ ] `UploadDropzone`
- [ ] `FileInfoCard`
- [ ] `UploadProgressBar`

### 页面 2：任务处理中转页

**功能：**

- [ ] 展示当前任务状态
- [ ] 自动轮询
- [ ] 状态失败时显示错误原因

**组件：**

- [ ] `TaskStageStepper`
- [ ] `RetryActionBar`

### 页面 3：Gate 1 结构确认页

**功能：**

- [ ] 左侧原表视图
- [ ] 右侧结构化网格
- [ ] 合并/拆分工具
- [ ] 表头区/数据区标记
- [ ] 保存版本
- [ ] 最终确认

**组件：**

- [ ] `OriginalSheetPreview`
- [ ] `ReviewGridCanvas`
- [ ] `ReviewToolbar`
- [ ] `VersionHistoryPanel`

### 页面 4：分析结果页

**功能：**

- [ ] 概要结论
- [ ] 校验问题列表
- [ ] 异常问题列表
- [ ] 图表展示
- [ ] 原始表联动定位

**组件：**

- [ ] `ExecutiveSummaryCard`
- [ ] `IssueListPanel`
- [ ] `InsightPanel`
- [ ] `ChartGallery`
- [ ] `SheetTraceViewer`

### 页面 5：任务日志页

**功能：**

- [ ] 阶段耗时
- [ ] 模块输出摘要
- [ ] 错误定位

**组件：**

- [ ] `StageLogTable`
- [ ] `TaskMetaCard`

### 前端主交互流程

```text
上传文件
-> 文件上传成功
-> 触发解析
-> 进入 Gate 1
-> 用户修正并确认
-> 后端依次执行公式推导/校验/异常/摘要/分析/图表
-> 前端跳转结果页
-> 用户查看问题与图表
-> 如结构仍不对，可回退到 Gate 1 重跑
```

---

## 附录 F：推荐 API 响应契约

### `IssueItem`

```json
{
  "id": "issue_001",
  "type": "validation_error",
  "severity": "high",
  "sheet_name": "经营分析",
  "cell_address": "F12",
  "metric_name": "营业利润",
  "reason": "营业利润不等于营业收入减营业成本",
  "expected_value": 120.5,
  "actual_value": 98.2,
  "trace_ref": {
    "task_id": "task_001",
    "sheet_id": "sheet_001",
    "structure_version": 2
  }
}
```

### `ChartSpec`

```json
{
  "id": "chart_001",
  "chart_type": "line",
  "title": "营业收入趋势",
  "x_field": "月份",
  "y_fields": ["营业收入"],
  "series": [
    {
      "name": "营业收入",
      "data": [120, 132, 145, 160]
    }
  ],
  "highlights": [
    {
      "index": 3,
      "reason": "环比增长异常"
    }
  ],
  "source_cells": ["B5:E5", "B2:E2"]
}
```

### `InsightItem`

```json
{
  "id": "insight_001",
  "severity": "medium",
  "title": "第三季度利润下滑",
  "summary": "第三季度营业利润连续下降，且与成本上升同步。",
  "evidence": [
    {
      "metric": "营业利润",
      "cell_address": "H12"
    },
    {
      "metric": "营业成本",
      "cell_address": "H10"
    }
  ],
  "recommendation": "建议核查第三季度采购成本和费用归集逻辑。"
}
```

---

## 附录 G：按天开发顺序表

### 第 1 天：需求冻结

- [x] 写 `README` 的产品目标。
- [x] 写第一版范围与非目标。
- [x] 定义用户主流程。
- [x] 画出系统状态机。
- [x] 确定技术栈。

### 第 2 天：项目初始化

- [x] 初始化后端工程。
- [x] 初始化前端工程。
- [x] 初始化代码规范、格式化、环境变量。
- [x] 建立基础目录。

### 第 3 天：数据库与基础模型

- [x] 建立数据库连接。
- [x] 创建 `files`、`tasks`、`sheets` 表。
- [x] 创建基础 ORM 模型。
- [x] 跑通迁移。

### 第 4 天：文件上传

- [x] 写上传接口。
- [x] 落盘或对象存储。
- [x] 返回任务 ID。
- [x] 写上传单元测试。

### 第 5 天：Excel 读取

- [x] 读取 workbook。
- [x] 解析 sheet。
- [x] 解析合并单元格。
- [x] 保存 cells。

### 第 6 天：初始网格生成

- [x] 生成网格快照。
- [x] 生成原始地址映射。
- [x] 输出 review 所需 JSON。

### 第 7 天：双轨单元格策略

- [x] 编写单元格分类器。
- [x] 实现维度 padding。
- [x] 实现数值 NaN 留空。
- [x] 写边界测试。

### 第 8 天：Gate 1 页面骨架

- [x] 搭建任务详情页。
- [x] 搭建结构确认页布局。
- [x] 接通预览接口。

### 第 9 天：结构编辑能力

- [x] 实现合并。
- [x] 实现拆分。
- [x] 实现表头标记。
- [x] 实现数据区标记。

### 第 10 天：结构版本化

- [x] 保存 patch。
- [x] 保存 `structure_versions`。
- [x] 实现确认接口。

### 第 11 天：多级表头解析

- [x] 识别表头层级。
- [x] 生成列路径。
- [x] 识别指标列。

### 第 12 天：公式 DSL 设计

- [x] 定义列关系语法。
- [x] 定义汇总关系语法。
- [x] 定义同比环比语法。
- [x] 写解析器测试。

### 第 13 天：LLM 公式推导

- [x] 写 Prompt。
- [x] 接入模型。
- [x] 解析 JSON。
- [x] 存储公式规则。

### 第 14 天：公式兜底与清洗

- [x] 过滤非法公式。
- [x] 为空规则集设计降级逻辑。
- [x] 补充日志。

### 第 15 天：校验引擎主逻辑

- [x] DSL 转执行计划。
- [x] 实现逐行校验。
- [x] 实现汇总校验。

### 第 16 天：校验结果落库

- [x] 记录误差。
- [x] 记录定位。
- [x] 记录命中规则。

### 第 17 天：业务规则异常检测

- [x] 异常增长率。
- [x] 连续下滑。
- [x] 负值/零值异常。
- [x] 结构占比异常。

### 第 18 天：统计异常检测

- [x] 接入 IQR。
- [x] 根据样本量切换模式。
- [x] 合并规则异常结果。

### 第 19 天：摘要压缩

- [x] 统计摘要。
- [x] 异常切片。
- [x] token 估算。
- [x] 裁剪策略。

### 第 20 天：AI 分析

- [x] 写分析 Prompt。
- [x] 定义输出 JSON。
- [x] 建立证据引用。

### 第 21 天：图表推荐

- [x] 设计选图规则。
- [x] 生成 `ChartSpec`。
- [x] 处理不可成图场景。

### 第 22 天：结果页

- [ ] 概览卡片。
- [ ] 问题列表。
- [ ] 图表画廊。
- [ ] 原表联动。

### 第 23 天：日志与可追溯

- [ ] 阶段日志。
- [ ] 模型调用日志。
- [ ] 错误页展示。

### 第 24 天：联调

- [ ] 打通全链路。
- [ ] 修复状态流转问题。
- [ ] 修复接口契约问题。

### 第 25 天：样本测试

- [ ] 正常样本表。
- [ ] 异常样本表。
- [ ] 复杂表头样本表。
- [ ] 合并单元格样本表。

### 第 26 天：人工验收

- [ ] 检查是否能定位原始单元格。
- [ ] 检查分析是否引用证据。
- [ ] 检查图表是否合理。

### 第 27 天：修收尾问题

- [ ] 性能问题。
- [ ] 文案问题。
- [ ] 边界问题。

### 第 28 天：发布第一版

- [ ] 打包部署。
- [ ] 准备演示样本。
- [ ] 输出版本说明。

---

## 附录 H：第一版一定要守住的开发原则

- [ ] 先做 Excel 主链路，不要先做 OCR。
- [ ] 先做结构准，再做分析美。
- [ ] 先做规则校验，再做模型解释。
- [ ] 先保证可追溯，再追求自动化程度。
- [ ] 先把每一步输出存下来，再考虑性能优化。
- [ ] 遇到无法判断的语义，宁可标记 `unknown`，不要强猜。
- [ ] 所有模型输出都必须经过结构化校验，不能直接驱动结果页。
