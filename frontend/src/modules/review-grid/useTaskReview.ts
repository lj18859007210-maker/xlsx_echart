import { startTransition, useEffect, useMemo, useState } from "react";

import { buildDraftSheet } from "./draftEditing";
import type { DraftReviewSheet, ReviewSheetSnapshot, TaskReviewResponse } from "../../types/review";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export function useTaskReview(activeTaskId: string) {
  const [payload, setPayload] = useState<TaskReviewResponse | null>(null);
  const [selectedSheetId, setSelectedSheetId] = useState<number | null>(null);
  const [draftSheets, setDraftSheets] = useState<Record<number, DraftReviewSheet>>({});
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
          const review = data as TaskReviewResponse;
          setPayload(review);
          startTransition(() => {
            setSelectedSheetId(review.sheets[0]?.sheet_id ?? null);
          });
          setDraftSheets(
            Object.fromEntries(
              review.sheets.map((sheet) => [sheet.sheet_id, buildDraftSheet(sheet)]),
            ),
          );
        }
      } catch (requestError) {
        if (!cancelled) {
          setPayload(null);
          setSelectedSheetId(null);
          setDraftSheets({});
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

  return {
    payload,
    setPayload,
    selectedSheetId,
    setSelectedSheetId,
    selectedSheet,
    draftSheets,
    setDraftSheets,
    loading,
    error,
    setError,
  };
}

