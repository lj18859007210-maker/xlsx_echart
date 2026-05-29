import { useState } from "react";

import { ReviewGrid } from "../modules/review-grid/ReviewGrid";
import { useTaskReview } from "../modules/review-grid/useTaskReview";
import { useDraftEditing } from "../modules/review-grid/useDraftEditing";
import { useStructureVersion } from "../modules/review-grid/useStructureVersion";
import { usePipeline } from "../modules/pipeline/usePipeline";
import { PipelinePanel } from "../modules/pipeline/PipelinePanel";

export function TaskReviewPage({
  taskId = "1",
  onViewResults,
}: {
  taskId?: string;
  onViewResults?: () => void;
}) {
  const [taskIdInput, setTaskIdInput] = useState(taskId);
  const [activeTaskId, setActiveTaskId] = useState(taskId);
  const [viewMode, setViewMode] = useState<"raw" | "aligned">("aligned");

  const review = useTaskReview(activeTaskId);
  const { loadMoreRows, loadingMore } = review;
  const draft = useDraftEditing({
    selectedSheetId: review.selectedSheetId,
    selectedSheet: review.selectedSheet,
    draftSheets: review.draftSheets,
    setDraftSheets: review.setDraftSheets,
  });

  const pipeline = usePipeline();

  const versioning = useStructureVersion({
    payload: review.payload,
    setPayload: review.setPayload,
    draftSheets: review.draftSheets,
    setError: review.setError,
    onConfirmed: () => {
      pipeline.run(activeTaskId);
    },
  });

  const statusLabel = (s: string) => {
    const map: Record<string, string> = {
      uploaded: "已上传",
      parsing: "解析中",
      parsed: "已解析",
      confirmed: "已确认",
      running: "执行中",
      completed: "已完成",
      failed: "失败",
    };
    return map[s] ?? s;
  };

  const statusIcon = (s: string) => {
    if (s === "confirmed" || s === "completed") return "✅";
    if (s === "running" || s === "parsing") return "⏳";
    if (s === "failed") return "❌";
    return "⏳";
  };

  const taskSummary = review.payload
    ? [
        { icon: "📋", label: "任务", value: `#${review.payload.task_id}` },
        { icon: statusIcon(review.payload.status), label: "状态", value: statusLabel(review.payload.status), isStatus: true, status: review.payload.status },
        { icon: "📊", label: "工作表", value: String(review.payload.sheets.length) },
        { icon: "🔖", label: "结构版本", value: `v${review.payload.structure_version}` },
      ]
    : [];

  return (
    <main className="review-page">
      <section className="review-hero">
        <div className="review-hero-copy">
          <p className="eyebrow">Gate 1 · 结构确认</p>
          <h1>结构编辑</h1>
          <p className="summary">
            确认表格结构（合并/拆分/表头标记）后，系统将自动执行公式校验、异常检测、AI 分析与图表生成。
          </p>
        </div>

        <form
          className="task-launcher"
          onSubmit={(event) => {
            event.preventDefault();
            setActiveTaskId(taskIdInput);
          }}
        >
          <label>
            <span>Task ID</span>
            <input
              value={taskIdInput}
              onChange={(event) => setTaskIdInput(event.target.value)}
            />
          </label>
          <button type="submit">加载</button>
        </form>

        {taskSummary.length > 0 && (
          <div className="task-overview-strip">
            {taskSummary.map((item: any) => (
              <div className={`overview-card${item.isStatus ? " status-" + item.status : ""}`} key={item.label}>
                <span className="overview-card-icon">{item.icon}</span>
                <div>
                  <p>{item.label}</p>
                  <strong>{item.value}</strong>
                </div>
              </div>
            ))}
          </div>
        )}

        {review.error && <p className="error-banner">{review.error}</p>}
      </section>

      {review.loading && <p className="loading-banner">加载中...</p>}

      <section className="review-workspace">
        <aside className="review-sidebar">
          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">工作簿</p>
              <h2>工作表</h2>
            </div>
            {review.payload && (
              <div className="sheet-stack">
                {review.payload.sheets.map((sheet) => (
                  <button
                    key={sheet.sheet_id}
                    className={`sheet-pill${review.selectedSheetId === sheet.sheet_id ? " is-active" : ""}`}
                    type="button"
                    onClick={() => {
                      review.setSelectedSheetId(sheet.sheet_id);
                      draft.setSelectionAnchor(null);
                      draft.setSelectionFocus(null);
                    }}
                  >
                    <span>{sheet.sheet_name}</span>
                    <small>
                      {sheet.row_count}×{sheet.col_count}
                      {sheet.is_hidden ? " · 隐藏" : ""}
                    </small>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">合并区域</p>
              <h2>范围</h2>
            </div>
            <div className="merge-list">
              {draft.visibleMergeRanges.map((range) => (
                <span className="merge-pill" key={range}>
                  {range}
                </span>
              ))}
              {review.selectedSheet && draft.visibleMergeRanges.length === 0 && (
                <p className="sidebar-message">当前工作表无合并单元格。</p>
              )}
            </div>
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">表头解析</p>
              <h2>列结构</h2>
            </div>
            {draft.headerSummary && (
              <div className="merge-list">
                <span className="merge-pill">{draft.headerSummary.headerRowSpan} 行表头</span>
                <span className="merge-pill">{draft.headerSummary.dimensionCount} 个维度列</span>
                <span className="merge-pill">{draft.headerSummary.measureCount} 个指标列</span>
                {draft.headerSummary.previewPaths.map((path) => (
                  <span className="merge-pill" key={path}>
                    {path}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">编辑工具</p>
              <h2>操作</h2>
            </div>
            <div className="action-stack">
              <p className="action-group-label">区域操作</p>
              <button className="action-button" type="button" onClick={draft.mergeSelection}>
                合并选中区域
              </button>
              <span className="action-hint">将选中的多个单元格合并为一个区域</span>
              <button className="action-button" type="button" onClick={draft.splitSelection}>
                拆分选中区域
              </button>
              <span className="action-hint">将合并的区域拆分为独立单元格</span>

              <p className="action-group-label">标记操作</p>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => draft.markSelection("header")}
              >
                标记为表头
              </button>
              <span className="action-hint">将选中行标记为表头行</span>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => draft.markSelection("data")}
              >
                标记为数据
              </button>
              <span className="action-hint">将选中行标记为数据行</span>

              <p className="action-group-label">提交操作</p>
              <button className="action-button is-ghost" type="button" onClick={draft.resetSelection}>
                清除选择
              </button>
              <button
                className="action-button"
                type="button"
                onClick={versioning.saveDraft}
                disabled={versioning.saving}
              >
                {versioning.saving ? "保存中..." : "保存草稿"}
              </button>
              <button
                className="action-button is-primary"
                type="button"
                onClick={versioning.confirmStructure}
                disabled={versioning.saving || pipeline.running}
              >
                {versioning.saving ? "处理中..." : "确认结构"}
              </button>
            </div>
            <div className="action-confirm-hint">
              <p>{versioning.actionMessage ?? "确认结构后将自动执行后续分析管线。"}</p>
            </div>
          </div>
        </aside>

        <section className="review-stage">
          <div className="stage-toolbar">
            <div>
              <p className="mini-label">结构预览</p>
              <h2>{review.selectedSheet?.sheet_name ?? "未选择工作表"}</h2>
            </div>

            <div className="view-toggle">
              <button
                type="button"
                className={viewMode === "raw" ? "is-selected" : ""}
                onClick={() => setViewMode("raw")}
              >
                原始
              </button>
              <button
                type="button"
                className={viewMode === "aligned" ? "is-selected" : ""}
                onClick={() => setViewMode("aligned")}
              >
                对齐后
              </button>
            </div>
          </div>

          {review.selectedSheet ? (
            <ReviewGrid
              draftSheet={draft.selectedDraftSheet}
              loadingMore={loadingMore}
              mode={viewMode}
              onLoadMore={() => {
                if (review.selectedSheetId != null) {
                  void loadMoreRows(review.selectedSheetId, 0);
                }
              }}
              onCellSelect={viewMode === "aligned" ? draft.handleCellSelect : undefined}
              selectedRange={viewMode === "aligned" ? draft.selectedRange : null}
              sheet={review.selectedSheet}
            />
          ) : (
            <div className="empty-state">
              <p>尚未加载数据。</p>
            </div>
          )}
        </section>
      </section>

      <PipelinePanel
        steps={pipeline.steps}
        running={pipeline.running}
        allDone={pipeline.allDone}
        hasFailure={pipeline.hasFailure}
        onViewResults={onViewResults}
      />
    </main>
  );
}
