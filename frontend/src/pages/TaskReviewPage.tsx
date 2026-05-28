import { useState } from "react";

import { ReviewGrid } from "../modules/review-grid/ReviewGrid";
import { useTaskReview } from "../modules/review-grid/useTaskReview";
import { useDraftEditing } from "../modules/review-grid/useDraftEditing";
import { useStructureVersion } from "../modules/review-grid/useStructureVersion";

export function TaskReviewPage() {
  const [taskIdInput, setTaskIdInput] = useState("1");
  const [activeTaskId, setActiveTaskId] = useState("1");
  const [viewMode, setViewMode] = useState<"raw" | "aligned">("aligned");

  const review = useTaskReview(activeTaskId);
  const draft = useDraftEditing({
    selectedSheetId: review.selectedSheetId,
    selectedSheet: review.selectedSheet,
    draftSheets: review.draftSheets,
    setDraftSheets: review.setDraftSheets,
  });
  const versioning = useStructureVersion({
    payload: review.payload,
    setPayload: review.setPayload,
    draftSheets: review.draftSheets,
    setError: review.setError,
  });

  const taskSummary = review.payload
    ? [
        { label: "Task", value: `#${review.payload.task_id}` },
        { label: "Status", value: review.payload.status },
        { label: "Sheets", value: String(review.payload.sheets.length) },
        { label: "Structure", value: `v${review.payload.structure_version}` },
        { label: "Selection", value: draft.selectedRange ? "active" : "none" },
      ]
    : [];

  return (
    <main className="review-page">
      <section className="review-hero">
        <div className="review-hero-copy">
          <p className="eyebrow">Day 8 Gate 1 Frame</p>
          <h1>Structure Review Studio</h1>
          <p className="summary">
            Task detail, review payload, and the first Gate 1 layout are now connected to the
            live backend review endpoint.
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
          <button type="submit">Load</button>
        </form>

        {taskSummary.length > 0 && (
          <dl className="task-summary-grid">
            {taskSummary.map((item) => (
              <div className="summary-item" key={item.label}>
                <dt>{item.label}</dt>
                <dd>{item.value}</dd>
              </div>
            ))}
          </dl>
        )}

        {review.error && <p className="error-banner">{review.error}</p>}
      </section>

      {review.loading && <p className="loading-banner">Loading review data...</p>}

      <section className="review-workspace">
        <aside className="review-sidebar">
          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">Workbook</p>
              <h2>Sheets</h2>
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
                      {sheet.row_count}脳{sheet.col_count}
                      {sheet.is_hidden ? " 路 hidden" : ""}
                    </small>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">Merge Map</p>
              <h2>Ranges</h2>
            </div>
            <div className="merge-list">
              {draft.visibleMergeRanges.map((range) => (
                <span className="merge-pill" key={range}>
                  {range}
                </span>
              ))}
              {review.selectedSheet && draft.visibleMergeRanges.length === 0 && (
                <p className="sidebar-message">No merged ranges in this sheet.</p>
              )}
            </div>
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">Header Parse</p>
              <h2>Column Shape</h2>
            </div>
            {draft.headerSummary && (
              <div className="merge-list">
                <span className="merge-pill">{draft.headerSummary.headerRowSpan} header rows</span>
                <span className="merge-pill">{draft.headerSummary.dimensionCount} dimension cols</span>
                <span className="merge-pill">{draft.headerSummary.measureCount} measure cols</span>
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
              <p className="mini-label">Edit Controls</p>
              <h2>Draft Actions</h2>
            </div>
            <div className="action-stack">
              <button className="action-button" type="button" onClick={draft.mergeSelection}>
                Merge selection
              </button>
              <button className="action-button" type="button" onClick={draft.splitSelection}>
                Split selection
              </button>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => draft.markSelection("header")}
              >
                Mark header
              </button>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => draft.markSelection("data")}
              >
                Mark data
              </button>
              <button className="action-button is-ghost" type="button" onClick={draft.resetSelection}>
                Clear selection
              </button>
              <button
                className="action-button"
                type="button"
                onClick={versioning.saveDraft}
                disabled={versioning.saving}
              >
                {versioning.saving ? "Saving..." : "Save draft"}
              </button>
              <button
                className="action-button"
                type="button"
                onClick={versioning.confirmStructure}
                disabled={versioning.saving}
              >
                {versioning.saving ? "Working..." : "Confirm structure"}
              </button>
            </div>
            <p className="sidebar-message">
              {versioning.actionMessage ??
                "Day 10 now saves immutable structure versions before confirmation."}
            </p>
          </div>
        </aside>

        <section className="review-stage">
          <div className="stage-toolbar">
            <div>
              <p className="mini-label">Structure Review</p>
              <h2>{review.selectedSheet?.sheet_name ?? "No sheet selected"}</h2>
            </div>

            <div className="view-toggle">
              <button
                type="button"
                className={viewMode === "raw" ? "is-selected" : ""}
                onClick={() => setViewMode("raw")}
              >
                Original
              </button>
              <button
                type="button"
                className={viewMode === "aligned" ? "is-selected" : ""}
                onClick={() => setViewMode("aligned")}
              >
                Aligned
              </button>
            </div>
          </div>

          {review.selectedSheet ? (
            <ReviewGrid
              draftSheet={draft.selectedDraftSheet}
              mode={viewMode}
              onCellSelect={viewMode === "aligned" ? draft.handleCellSelect : undefined}
              selectedRange={viewMode === "aligned" ? draft.selectedRange : null}
              sheet={review.selectedSheet}
            />
          ) : (
            <div className="empty-state">
              <p>No review data loaded yet.</p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
