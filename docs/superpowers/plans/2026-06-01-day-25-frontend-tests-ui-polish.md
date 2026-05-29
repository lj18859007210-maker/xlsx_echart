# Day 25：前端测试补充 + UI 打磨
**日期：** 2026-06-01
**状态：** pending
**依赖：** Day 24（Mock 模式）

---

## 一、前端测试补充

### 1.1 现状
仅有 1 个测试文件 `draftEditing.test.ts`，原来 7 个测试被删除了 6 个（`reviewSelection.test.ts` 等）。

### 1.2 需补充的测试

| 测试文件 | 测试内容 | 优先级 |
|----------|----------|--------|
| `useFileUpload.test.ts` | 上传状态机：idle→uploading→success/error | P0 |
| `usePipeline.test.ts` | 管线状态：7 步依次完成、单步失败不阻塞 | P0 |
| `PipelinePanel.test.tsx` | 管线面板渲染：各状态图标正确 | P1 |
| `UploadPage.test.tsx` | 上传页：拖拽区渲染、上传中进度条、成功后按钮 | P1 |
| `TaskReviewPage.test.tsx` | 结构确认页：工作表列表、网格渲染 | P1 |
| `ResultsPage.test.tsx` | 结果页：加载态、错误态、数据展示 | P1 |

**总目标：** 前端测试 ≥ 7 个文件，覆盖率关键路径。

### 1.3 测试基础设施
- [ ] 确认 `vitest` 配置正确（`frontend/vitest.config.ts`）
- [ ] 添加 `@testing-library/react` 和 `@testing-library/jest-dom`
- [ ] 添加 MSW（Mock Service Worker）用于 mock API 响应
- [ ] 创建 `frontend/tests/setup.ts` 测试初始化文件
- [ ] 创建 `frontend/tests/mocks/handlers.ts` API mock handlers

---

## 二、UI 打磨——任务概览卡片

### 2.1 问题
`TaskReviewPage.tsx` 中的任务信息区域：
```
任务      状态        工作表      结构版本
#3        confirmed   3          v1
```
纯文字平铺，缺乏视觉层次。

### 2.2 改造目标
每个卡片包含：
- 图标（emoji 或 CSS icon）
- 标签（小字灰色）
- 数值（大字号）
- 状态卡片：彩色背景（confirmed=绿色、pending=黄色、failed=红色）

**任务：**
- [ ] 重新设计 `.task-overview-strip` 的 CSS
  - 卡片最小宽度 120px
  - 图标 + 标签 + 数值垂直排列
  - 状态卡片使用 `var(--accent)` 浅色背景
- [ ] 为每个卡片添加图标：
  - 任务：📋
  - 状态：✅（confirmed）/ ⏳（pending）/ ❌（failed）
  - 工作表：📊
  - 结构版本：🔖

---

## 三、UI 打磨——编辑工具区域

### 3.1 问题
8 个按钮垂直堆叠，无分组、无说明，用户不理解各自用途。

### 3.2 改造目标
按钮分 3 组，每组有标题和分隔线：

**第 1 组：区域操作**
- 合并选中区域 — 将选中的多个单元格合并为一个区域
- 拆分选中区域 — 将合并的区域拆分为独立单元格

**第 2 组：标记操作**
- 标记为表头 — 将选中行标记为表头行（黄色背景）
- 标记为数据 — 将选中行标记为数据行（绿色背景）

**第 3 组：提交操作**
- 清除选择 — 取消当前选区
- 保存草稿 — 保存当前编辑状态
- 确认结构 — 确认后自动执行分析管线

**任务：**
- [ ] 修改 `.action-stack` CSS：组间用 `border-top` 分隔
- [ ] 每个按钮下方添加 `.action-hint` 小字描述
- [ ] 第 3 组按钮样式加重视觉权重（`确认结构` 用主色按钮）
- [ ] `确认结构后将自动执行后续分析管线` 提示用醒目样式（黄色浅底 + 边框）

---

## 四、UI 打磨——结构预览区

### 4.1 问题
网格中表头和数据行颜色无区分，合并单元格无视觉提示。

### 4.2 改造目标
- 表头行：`var(--dimension)` 背景色（暖黄色）
- 数据行：`var(--measure)` 背景色（浅绿色）
- 合并单元格：加粗边框
- 选中区域：蓝色边框高亮
- 未知类型行：`var(--unknown)` 背景色（浅紫色）

**任务：**
- [ ] 修改 `ReviewGrid.tsx` 中单元格的 className 逻辑
  - 根据 `draftSheet.alignedRoles` 或 `sheet.aligned_cell_roles` 添加 `is-header`、`is-data`、`is-dimension`、`is-measure` 类
- [ ] 添加对应的 CSS 规则

---

## 五、检查清单

- [ ] 前端测试 ≥ 7 个文件
- [ ] 测试覆盖率关键路径（上传→解析→确认→管线→结果）
- [ ] 任务概览卡片有图标和颜色区分
- [ ] 编辑工具按钮分组清晰，每个有说明文字
- [ ] 结构预览区表头/数据有颜色区分
- [ ] 前端构建零错误
- [ ] 前端测试全部通过
