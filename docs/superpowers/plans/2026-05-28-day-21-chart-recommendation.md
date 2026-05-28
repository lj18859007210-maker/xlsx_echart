# Day 21：图表推荐（Chart Recommendation）

> 日期：2026-05-28（下午）
> 前置依赖：Day 19（摘要）、Day 20（AI 分析）
> 后置依赖：Day 22（结果页）
>
> **核心原则：确定性规则引擎，不依赖 LLM。**

---

## 一、目标

根据数据特征智能化推荐 ECharts 图表类型，生成 ChartSpec。

三种核心能力：
1. 选图 — 基于数据结构特征自动选择图表类型
2. 生图 — 生成 ECharts option 子集
3. 降级 — 不可成图场景优雅返回空列表 + 原因

---

## 二、输入来源

| 输入 | 来源 | 说明 |
|------|------|------|
| semantic_schema | Day 19 summary | 每列类型(dimension/measure)和路径 |
| chart_hints | Day 20 AI分析 | LLM建议(需验证) |
| aligned_grid | StructureVersion | 原始数据网格 |
| statistical_summary | Day 19 summary | 每列统计特征(含trend) |

---

## 三、选图规则引擎

### 3.1 优先级

P0: 不可成图 → 返回空
P1: chart_hints可用 → 采纳
P2: 自动推断 → 基于数据结构

### 3.2 推断规则矩阵

| 条件 | 类型 | 场景 |
|------|------|------|
| 1 dim + multi measures, 非时间 | bar | 地区收入对比 |
| 1 dim(time-like) + 1+ measures | line | 月度趋势 |
| 1 dim + 1 measure, <=6行 | pie | 市场占比 |
| 2 measures 无dim | scatter | 相关性 |
| 2+ dims + 2+ measures | grouped_bar | 多维分组 |
| 1 dim + 1 measure, >6行 | line | 长序列趋势 |

### 3.3 时间维度识别

关键词: 月, 年, 季, 日, 周, 时, month, year, quarter, day, week, date, 时间, 日期

### 3.4 不可成图

- aligned_grid 为空
- 无可识别 dimension 列
- 数据行 < 2

---

## 四、ChartSpec 结构

{
  chart_type, title, x_field, y_fields[],
  series: [{name, data[]}],
  highlights: [{index, reason}],
  source_cells: [range str],
  reason: str
}

---

## 五、服务架构

chart_service.py ← 编排
  ├── rule_engine.py ← 选图规则
  ├── spec_builder.py ← 构建ChartSpec
  └── highlight_detector.py ← 异常标注

---

## 六、chart_specs 表

id(INT PK), task_id(FK INT), chart_index(INT),
chart_type(VARCHAR), title(VARCHAR), x_field(VARCHAR),
y_fields_json(JSON), series_json(JSON), highlights_json(JSON),
source_cells_json(JSON), reason(TEXT), created_at(DATETIME)

---

## 七、API

POST /api/tasks/{task_id}/recommend-charts → 生成(幂等)
GET  /api/tasks/{task_id}/chart-specs     → 读取

---

## 八、状态

analyzed → recommend-charts → chart_ready

---

## 九、测试(TDD, 约18个)

rule_engine (7): bar/line/pie/scatter选择, 无数据, 无dim, hints验证
spec_builder (5): bar/line/pie spec, 数据提取, series格式
chart_service (6): 正常流程, 幂等, 空结果, 持久化, GET, 状态

---

## 十、文件

db/models/chart_spec_record.py (新)
schemas/chart_schema.py (新)
services/chart_recommendation/ (新,4文件)
api/routes/tasks.py (改)
tests/unit/test_chart_service.py (新)
