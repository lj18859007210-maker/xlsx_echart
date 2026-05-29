import { startTransition, useEffect, useMemo, useState } from "react";

import { buildDraftSheet } from "./draftEditing";
import type { DraftReviewSheet, ReviewSheetSnapshot, TaskReviewResponse } from "../../types/review";
import { api, ApiError } from "../api-client";

export function useTaskReview(activeTaskId: string) {
  const [payload, setPayload] = useState<TaskReviewResponse | null>(null);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [draftSheets, setDraftSheets] = useState<Record<number, DraftReviewSheet>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSheet: ReviewSheetSnapshot | undefined = useMemo(() => {
    if (!payload || selectedSheetId == null) return undefined;
    return payload.sheets.find((s) => s.sheet_id === selectedSheetId);
  }, [payload, selectedSheetId]);

  const loadDraftSheet = (sheet: ReviewSheetSnapshot, prev?: Record<number, DraftReviewSheet>) => {
    const current = prev ?? draftSheets;
    if (current[sheet.sheet_id]) return;
    const ds = buildDraftSheet(sheet);
    startTransition(() => {
      setDraftSheets((prev) => ({ ...prev, [sheet.sheet_id]: ds }));
    });
  };

  async function fetchReview() {
    setLoading(true);
    setError(null);

    try {
      const data = await api.get(`/tasks/${activeTaskId}/review`) as TaskReviewResponse;
      setPayload(data);

      const sheetId = data.sheets[0]?.sheet_id ?? null;
      setSelectedSheetId(sheetId);

      if (sheetId != null) {
        const sheet = data.sheets.find((s) => s.sheet_id === sheetId);
        if (sheet) loadDraftSheet(sheet, {});
      }
    } catch (e) {
      const msg = e instanceof ApiError ? e.detail : e instanceof Error ? e.message : "\u52a0\u8f7d\u5931\u8d25";
      setError(msg);
      setPayload(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void fetchReview();
  }, [activeTaskId]);

  return {
    payload,
    selectedSheetId,
    selectedSheet,
    draftSheets,
    loading,
    error,
    setPayload,
    setSelectedSheetId,
    setDraftSheets,
    setError,
  };
}
