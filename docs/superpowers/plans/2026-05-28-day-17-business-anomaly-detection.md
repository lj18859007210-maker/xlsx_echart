# Day 17：业务规则异常检测

**日期：** 2026-05-28
**状态：** in_progress
**依赖：** Day 16（validation persistence 完成）

---

## 目标

在公式校验之后，对表格指标列执行业务规则异常检测，识别数据中的业务风险点。

四条检测规则：
1. **异常增长率** — 单期环比超过阈值（默认 ±50%）
2. **连续下滑** — 连续 N 期（默认 3 期）同比下降
3. **负值/零值异常** — 预期为正的指标出现 ≤ 0
4. **结构占比异常** — 某维度指标的占比变化超过阈值（默认 ±20pp）

---

## 技术方案

### 1. 架构

```
anomaly_service.py (编排层)
  ├── growth_rate_detector.py    (异常增长率)
  ├── decline_detector.py        (连续下滑)
  ├── negative_zero_detector.py  (负值/零值)
  └── structure_share_detector.py (结构占比)
```

每个检测器独立运行、无状态。编排层合并、去重、排序后输出。

### 2. 新模型：`AnomalyIssueRecordModel`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增 |
| task_id | FK → tasks | 所属任务 |
| sheet_id | FK → sheets | 所属 Sheet |
| row_index | Integer | 行号（0-based） |
| col_index | Integer | 列号（0-based） |
| issue_type | String(50) | growth_rate_anomaly / consecutive_decline / negative_or_zero / structure_share_anomaly |
| severity | String(20) | warning / error |
| metric_name | String(200) | 指标名称（列名） |
| detection_source | String(30) | 固定 "business_rule" |
| reason | Text | 人类可读原因（中文） |
| score | Float | 异常程度分数 0-1 |
| created_at | DateTime(tz) | 创建时间 |

### 3. 检测器设计

#### 3.1 growth_rate_detector
- 读取 `column_kinds` 选 measure 列，读取 `aligned_grid` 逐行计算环比
- `row[i+1] - row[i] / abs(row[i])` 超出 ±50% → 标记
- 可配置：`GROWTH_RATE_THRESHOLD = 0.5`

#### 3.2 decline_detector
- 对每列 measure 逐行检查：连续 N=3 期值递减
- 可配置：`CONSECUTIVE_DECLINE_N = 3`

#### 3.3 negative_zero_detector
- 对每列 measure：值 ≤ 0 即标记（收入、利润等不应为负）
- 可配置：`NEGATIVE_THRESHOLD = 0`

#### 3.4 structure_share_detector
- 每行对 measure 列计算占比 → 跨行对比占比变化
- 占比变化 ≥ ±20pp → 标记
- 可配置：`SHARE_CHANGE_THRESHOLD = 0.20`

### 4. API 端点

`POST /{task_id}/detect-anomalies`：
- 输入：无 body（或可选阈值覆盖）
- 输出：`AnomalyDetectionResult { task_id, status, detection_mode, total_issues, issues[] }`
- 前置：task.status 必须是 `validated` 或 `formula_gap_acknowledged`
- 落库：幂等（先删旧后插新）

### 5. 不变更

- 不引入统计模型（Day 18）
- 不修改任务状态（anomaly detection 是无副作用的分析读操作）
- 不引入外部配置服务

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/db/models/anomaly_issue_record.py` | NEW | ORM 模型 |
| `alembic/versions/20260528_0006_add_anomaly_issues.py` | NEW | 迁移 |
| `app/db/base.py` | MOD | 注册模型 |
| `app/db/models/task_record.py` | MOD | relationship |
| `app/services/anomaly/__init__.py` | NEW | 包 |
| `app/services/anomaly/growth_rate_detector.py` | NEW | 增长率检测 |
| `app/services/anomaly/decline_detector.py` | NEW | 连续下滑检测 |
| `app/services/anomaly/negative_zero_detector.py` | NEW | 负值/零值检测 |
| `app/services/anomaly/structure_share_detector.py` | NEW | 结构占比检测 |
| `app/services/anomaly/anomaly_service.py` | NEW | 编排层 |
| `app/schemas/anomaly_schema.py` | NEW | API Schema |
| `app/api/routes/tasks.py` | MOD | detect-anomalies 端点 |
| `tests/unit/test_anomaly_service.py` | NEW | 测试 |

---

## 测试策略

1. **test_growth_rate_detector** — 跨行环比超阈值被捕获
2. **test_decline_detector** — 连续 3 期下降被捕获
3. **test_negative_zero_detector** — 负值和零值被捕获
4. **test_structure_share_detector** — 占比变化超 20pp 被捕获
5. **test_anomaly_service_orchestration** — 全量编排+落库+幂等
6. **test_detect_anomalies_endpoint** — API 端点完整调用链