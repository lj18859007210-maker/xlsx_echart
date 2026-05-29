# Day 22：结果页（Results Page）

> 日期：2026-05-28
> 前置依赖：Day 8-9（前端骨架）、Day 19-21（后端 API）
>
> **核心原则：所有数据来自后端 API，前端纯展示+交互。**

---

## 一、目标

构建分析结果展示页，四种核心交互：
1. 概览卡片 — 任务执行摘要（问题数/异常数/图表数/分析结论）
2. 问题列表 — 校验异常 + 业务异常合并展示，可排序筛选
3. 图表画布 — 使用 ECharts 渲染 Day 21 的 ChartSpec
4. 原表联动 — 点击问题/图表数据点，高亮原始单元格

---

## 二、页面布局

`
+--------------------------------------------------+
|  概览卡片行 (4 cards: 校验问题/业务异常/图表/AI)    |
+--------------------------------------------------+
|  图表画布 (ECharts, 可切换)  |  问题列表 (可排序)   |
|                             |                     |
+-----------------------------+---------------------+
|  原表 (点击高亮联动)                               |
+--------------------------------------------------+
`

---

## 三、技术方案

- echarts: ^5.6.0 — 图表渲染
- echarts-for-react: ^3.0.2 — React 封装
- 无需路由库 — App.tsx 用 phase 状态切换 TaskReviewPage / ResultsPage
- 数据获取：自定义 hooks 复用已有 fetch 模式

---

## 四、API 消费

| 组件 | API |
|------|-----|
| OverviewCards | GET /tasks/{id}/summary + /insights + /chart-specs |
| IssueList | GET /tasks/{id}/validation-issues + /anomaly-issues |
| ChartCanvas | GET /tasks/{id}/chart-specs |
| SourceTable | GET /tasks/{id}/review |

---

## 五、组件清单

src/
  types/results.ts           # 新建 — 结果页类型
  modules/results/
    OverviewCards.tsx          # 新建
    IssueList.tsx              # 新建
    ChartCanvas.tsx            # 新建
    SourceTable.tsx            # 新建
    useResultsData.ts          # 新建 — 数据获取 hook
  pages/ResultsPage.tsx        # 新建
  App.tsx                      # 修改 — phase 切换
  styles.css                   # 修改 — 新增样式

---

## 六、交互细节

- 概览卡片用数字+标签，加载态骨架屏
- 问题列表：severity 颜色标记，点击行 → 高亮原始表的对应单元格
- 图表画布：ECharts setOption()，支持 bar/line/pie/scatter/stacked_bar/horizontal_bar
- 原表：点击问题行 → 滚动到对应行并高亮，点击图表数据点 → 在原表高亮
- 无数据时的空状态提示

---

## 七、测试要点

- 组件渲染（有数据/无数据/加载态）
- API 错误处理
- 图表类型覆盖
- 联动高亮逻辑
