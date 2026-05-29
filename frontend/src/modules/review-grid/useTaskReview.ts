import { startTransition, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { buildDraftSheet } from "./draftEditing";
import type {
  DraftReviewSheet,
  PagedSheetPayload,
  ReviewSheetSnapshot,
  TaskReviewPagedResponse,
  TaskReviewResponse,
} from "../../types/review";
import { api, ApiError } from "../api-client";

const PAGE_SIZE = 200;
const LOAD_AHEAD = 30;

export function useTaskReview(activeTaskId: string) {
  const [payload, setPayload] = useState<TaskReviewResponse | null>(null);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [draftSheets, setDraftSheets] = useState<Record<number, DraftReviewSheet>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [pagedData, setPagedData] = useState<Record<number, PagedSheetPayload>>({});
  const [loadingMore, setLoadingMore] = useState(false);
  const loadingMoreRef = useRef(false);
  const failedPagesRef = useRef<Set<string>>(new Set());

  const selectedSheet: ReviewSheetSnapshot | undefined = useMemo(() => {
    if (!payload || selectedSheetId == null) return undefined;
    const meta = payload.sheets.find((s) => s.sheet_id === selectedSheetId);
    if (!meta) return undefined;
    const paged = pagedData[selectedSheetId];
    if (!paged) return meta;
    return {
      ...meta,
      aligned_grid: paged.rows,
      aligned_cell_roles: paged.roles,
      aligned_source_map: paged.source_map,
      cell_tags: paged.tags,
      grid_snapshot: paged.raw_rows,
      address_map: paged.raw_source_map,
    } as ReviewSheetSnapshot;
  }, [payload, selectedSheetId, pagedData]);

  const loadDraftSheet = (sheet: ReviewSheetSnapshot, prev?: Record<number, DraftReviewSheet>) => {
    const current = prev ?? draftSheets;
    if (current[sheet.sheet_id]) return;
    const ds = buildDraftSheet(sheet);
    startTransition(() => {
      setDraftSheets((prev) => ({ ...prev, [sheet.sheet_id]: ds }));
    });
  };

  const fetchPage = useCallback(
    async (sheetId: number, offset: number): Promise<boolean> => {
      const failKey = sheetId + ":" + offset;
      if (failedPagesRef.current.has(failKey)) return false;
      if (loadingMoreRef.current) return true;
      loadingMoreRef.current = true;
      setLoadingMore(true);

      try {
        const url =
          "/tasks/" + activeTaskId + "/review/rows?sheet_id=" + sheetId + "&offset=" + offset + "&limit=" + PAGE_SIZE;
        const data = (await api.get(url)) as TaskReviewPagedResponse;

        setPagedData((prev) => {
          const existing = prev[sheetId];
          const newRows =
            existing && existing.rows.length > 0
              ? [...existing.rows, ...data.sheet.rows]
              : data.sheet.rows;
          const newRoles =
            existing && existing.roles.length > 0
              ? [...existing.roles, ...data.sheet.roles]
              : data.sheet.roles;
          const newSourceMap =
            existing && existing.source_map.length > 0
              ? [...existing.source_map, ...data.sheet.source_map]
              : data.sheet.source_map;
          const newTags =
            existing && existing.tags.length > 0
              ? [...existing.tags, ...data.sheet.tags]
              : data.sheet.tags;
          const newRawRows =
            existing && existing.raw_rows.length > 0
              ? [...existing.raw_rows, ...data.sheet.raw_rows]
              : data.sheet.raw_rows;
          const newRawSourceMap =
            existing && existing.raw_source_map.length > 0
              ? [...existing.raw_source_map, ...data.sheet.raw_source_map]
              : data.sheet.raw_source_map;

          const merged: PagedSheetPayload = {
            ...data.sheet,
            rows: newRows,
            roles: newRoles,
            source_map: newSourceMap,
            tags: newTags,
            raw_rows: newRawRows,
            raw_source_map: newRawSourceMap,
            offset: 0,
            limit: newRows.length,
          };

          return { ...prev, [sheetId]: merged };
        });

        const hasMore = offset + PAGE_SIZE < data.sheet.row_count;
        return hasMore;
      } catch (e) {
        failedPagesRef.current.add(failKey);
        console.error("Failed to fetch page:", e);
        return false;
      } finally {
        loadingMoreRef.current = false;
        setLoadingMore(false);
      }
    },
    [activeTaskId],
  );

  const loadMoreRows = useCallback(
    async (sheetId: number, _visibleEndIndex: number) => {
      const existing = pagedData[sheetId];
      const loadedCount = existing?.rows.length ?? 0;

      if (loadedCount === 0) {
        await fetchPage(sheetId, 0);
        return;
      }

      const sheetMeta = payload?.sheets.find((s) => s.sheet_id === sheetId);
      const totalRows = sheetMeta?.row_count ?? 0;

      if (loadedCount >= totalRows) return;

      await fetchPage(sheetId, loadedCount);
    },
    [fetchPage, pagedData, payload],
  );

  async function fetchReview() {
    setLoading(true);
    setError(null);

    try {
      const data = (await api.get("/tasks/" + activeTaskId + "/review")) as TaskReviewResponse;
      setPayload(data);

      const sheetId = data.sheets[0]?.sheet_id ?? null;
      setSelectedSheetId(sheetId);

      setPagedData({});
      failedPagesRef.current.clear();
      loadingMoreRef.current = false;

      if (sheetId != null) {
        const sheet = data.sheets.find((s) => s.sheet_id === sheetId);
        if (sheet) {
          if (sheet.row_count <= PAGE_SIZE) {
            loadDraftSheet(sheet, {});
          } else {
            await fetchPage(sheetId, 0);
          }
        }
      }
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? e.detail
          : e instanceof Error
            ? e.message
            : "failed to load";
      setError(msg);
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchReview();
  }, [activeTaskId]);

  useEffect(() => {
    if (selectedSheet && selectedSheet.row_count > PAGE_SIZE) {
      const paged = pagedData[selectedSheet.sheet_id];
      if (paged && paged.rows.length > 0) {
        loadDraftSheet(selectedSheet);
      }
    }
  }, [selectedSheet]);

  return {
    payload,
    selectedSheetId,
    selectedSheet,
    draftSheets,
    loading,
    loadingMore,
    error,
    setPayload,
    setSelectedSheetId,
    setDraftSheets,
    setError,
    loadMoreRows,
  };
}
