import { startTransition, useEffect, useMemo, useState } from "react";

import { ReviewGrid } from "../modules/review-grid/ReviewGrid";
import {
  buildDraftSheet,
  mergeDraftSelection,
  splitDraftSelection,
} from "../modules/review-grid/draftEditing";
import { selectReviewSheet } from "../modules/review-grid/reviewSelection";
import type {
  DraftCellTag,
  DraftReviewSheet,
  DraftSelectionRange,
  GridPoint,
  ReviewSheetSnapshot,
  TaskReviewResponse,
} from "../types/review";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

function normalizeRange(anchor: GridPoint, focus: GridPoint) {
  return {
    startRow: Math.min(anchor.row, focus.row),
    endRow: Math.max(anchor.row, focus.row),
    startCol: Math.min(anchor.col, focus.col),
    endCol: Math.max(anchor.col, focus.col),
  };
}

export function TaskReviewPage() {
  const [taskIdInput, setTaskIdInput] = useState("1");
  const [activeTaskId, setActiveTaskId] = useState("1");
  const [viewMode, setViewMode] = useState<"raw" | "aligned">("aligned");
  const [payload, setPayload] = useState<TaskReviewResponse | null>(null);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [draftSheets, setDraftSheets] = useState<Record<number, DraftReviewSheet>>({});
  const [selectionAnchor, setSelectionAnchor] = useState<GridPoint | null>(null);
  const [selectionFocus, setSelectionFocus] = useState<GridPoint | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchReview() {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}/tasks/${activeTaskId}/review`);
        const data = (await response.json()) as TaskReviewResponse | { detail?: string };

        if (!response.ok) {
          throw new Error(
            typeof data === "object" && data && "detail" in data && data.detail
              ? data.detail
              : "Failed to load review data",
          );
        }

        if (!cancelled) {
          setPayload(data as TaskReviewResponse);
          startTransition(() => {
            setSelectedSheetId((data as TaskReviewResponse).sheets[0]?.sheet_id ?? null);
          });
          setDraftSheets(
            Object.fromEntries(
              (data as TaskReviewResponse).sheets.map((sheet) => [
                sheet.sheet_id,
                buildDraftSheet(sheet),
              ]),
            ),
          );
          setSelectionAnchor(null);
          setSelectionFocus(null);
        }
      } catch (requestError) {
        if (!cancelled) {
          setPayload(null);
          setSelectedSheetId(null);
          setDraftSheets({});
          setSelectionAnchor(null);
          setSelectionFocus(null);
          setError(
            requestError instanceof Error ? requestError.message : "Failed to load review data",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void fetchReview();

    return () => {
      cancelled = true;
    };
  }, [activeTaskId]);

  const selectedSheet = useMemo<ReviewSheetSnapshot | null>(() => {
    if (!payload) {
      return null;
    }

    return (
      payload.sheets.find((sheet) => sheet.sheet_id === selectedSheetId) ??
      payload.sheets[0] ??
      null
    );
  }, [payload, selectedSheetId]);

  const selectedDraftSheet = selectedSheetId ? draftSheets[selectedSheetId] ?? null : null;

  const selectedRange = useMemo<DraftSelectionRange | null>(() => {
    if (!selectionAnchor || !selectionFocus) {
      return null;
    }

    return normalizeRange(selectionAnchor, selectionFocus);
  }, [selectionAnchor, selectionFocus]);

  function updateDraftSheet(
    updater: (currentSheet: DraftReviewSheet) => DraftReviewSheet,
  ) {
    if (!selectedSheetId) {
      return;
    }

    setDraftSheets((current) => {
      const sheet = current[selectedSheetId];
      if (!sheet) {
        return current;
      }

      return {
        ...current,
        [selectedSheetId]: updater(sheet),
      };
    });
  }

  function handleCellSelect(point: GridPoint) {
    if (!selectionAnchor) {
      setSelectionAnchor(point);
      setSelectionFocus(point);
      return;
    }

    setSelectionFocus(point);
  }

  function resetSelection() {
    setSelectionAnchor(null);
    setSelectionFocus(null);
  }

  useEffect(() => {
    setSelectionAnchor(null);
    setSelectionFocus(null);
  }, [selectedSheetId]);

  function mergeSelection() {
    if (!selectedRange) {
      return;
    }

    updateDraftSheet((sheet) => mergeDraftSelection(sheet, selectedRange));
  }

  function splitSelection() {
    if (!selectedRange || !selectedSheet) {
      return;
    }

    updateDraftSheet((sheet) => splitDraftSelection(sheet, selectedSheet, selectedRange));
  }

  function markSelection(tag: DraftCellTag) {
    if (!selectedRange || tag === "none") {
      return;
    }

    updateDraftSheet((sheet) => {
      const cellTags = sheet.cellTags.map((row) => [...row]);
      const alignedRoles = sheet.alignedRoles.map((row) => [...row]);

      for (let row = selectedRange.startRow; row <= selectedRange.endRow; row += 1) {
        for (let col = selectedRange.startCol; col <= selectedRange.endCol; col += 1) {
          cellTags[row][col] = tag;
          alignedRoles[row][col] = tag === "header" ? "dimension" : "measure";
        }
      }

      return {
        ...sheet,
        cellTags,
        alignedRoles,
      };
    });
  }

  const taskSummary = payload
    ? [
        { label: "Task", value: `#${payload.task_id}` },
        { label: "Status", value: payload.status },
        { label: "Sheets", value: String(payload.sheets.length) },
        { label: "Structure", value: `v${payload.structure_version}` },
        { label: "Selection", value: selectedRange ? "active" : "none" },
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
            setActiveTaskId(taskIdInput.trim() || "1");
          }}
        >
          <label className="task-launcher-label" htmlFor="task-id">
            Review task id
          </label>
          <div className="task-launcher-row">
            <input
              id="task-id"
              className="task-launcher-input"
              value={taskIdInput}
              onChange={(event) => setTaskIdInput(event.target.value)}
              placeholder="Enter task id"
            />
            <button className="task-launcher-button" type="submit">
              Load review
            </button>
          </div>
          <p className="task-launcher-hint">
            Start with a parsed task id. The page will call `GET /api/tasks/{activeTaskId}/review`.
          </p>
        </form>
      </section>

      <section className="task-overview-strip">
        {taskSummary.map((item) => (
          <article className="overview-card" key={item.label}>
            <p>{item.label}</p>
            <strong>{item.value}</strong>
          </article>
        ))}
      </section>

      <section className="gate-layout">
        <aside className="review-sidebar">
          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">Task Detail</p>
              <h2>Sheet Stack</h2>
            </div>

            {loading && <p className="sidebar-message">Loading review payload…</p>}
            {error && <p className="sidebar-message is-error">{error}</p>}

            {payload && (
              <div className="sheet-stack">
                {payload.sheets.map((sheet) => (
                  <button
                    key={sheet.sheet_id}
                    type="button"
                    className={`sheet-chip ${
                      sheet.sheet_id === selectedSheet?.sheet_id ? "is-active" : ""
                    }`}
                    onClick={() => {
                      startTransition(() => {
                        const nextState = selectReviewSheet(
                          {
                            selectedSheetId,
                            selectionAnchor,
                            selectionFocus,
                          },
                          sheet.sheet_id,
                        );
                        setSelectedSheetId(nextState.selectedSheetId);
                        setSelectionAnchor(nextState.selectionAnchor);
                        setSelectionFocus(nextState.selectionFocus);
                      });
                    }}
                  >
                    <span>{sheet.sheet_name}</span>
                    <small>
                      {sheet.row_count}×{sheet.col_count}
                      {sheet.is_hidden ? " · hidden" : ""}
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
              {(selectedSheet?.merge_ranges ?? []).map((range) => (
                <span className="merge-pill" key={range}>
                  {range}
                </span>
              ))}
              {selectedSheet && selectedSheet.merge_ranges.length === 0 && (
                <p className="sidebar-message">No merged ranges in this sheet.</p>
              )}
            </div>
          </div>

          <div className="sidebar-panel">
            <div className="sidebar-heading">
              <p className="mini-label">Edit Controls</p>
              <h2>Draft Actions</h2>
            </div>
            <div className="action-stack">
              <button className="action-button" type="button" onClick={mergeSelection}>
                Merge selection
              </button>
              <button className="action-button" type="button" onClick={splitSelection}>
                Split selection
              </button>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => markSelection("header")}
              >
                Mark header
              </button>
              <button
                className="action-button is-soft"
                type="button"
                onClick={() => markSelection("data")}
              >
                Mark data
              </button>
              <button className="action-button is-ghost" type="button" onClick={resetSelection}>
                Clear selection
              </button>
            </div>
            <p className="sidebar-message">
              Day 9 edits stay local on the aligned draft layer. Persistence starts on Day 10.
            </p>
          </div>
        </aside>

        <section className="review-stage">
          <div className="stage-toolbar">
            <div>
              <p className="mini-label">Structure Review</p>
              <h2>{selectedSheet?.sheet_name ?? "No sheet selected"}</h2>
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

          {selectedSheet ? (
            <ReviewGrid
              draftSheet={selectedDraftSheet}
              mode={viewMode}
              onCellSelect={viewMode === "aligned" ? handleCellSelect : undefined}
              selectedRange={viewMode === "aligned" ? selectedRange : null}
              sheet={selectedSheet}
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
