import { useState } from "react";

import {
  applyDraftSheetsToReview,
  buildStructureVersionSaveRequest,
} from "./structureVersionPayload";
import type {
  ConfirmStructureVersionResponse,
  DraftReviewSheet,
  StructureVersionSaveResponse,
  TaskReviewResponse,
} from "../../types/review";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export function useStructureVersion(opts: {
  payload: TaskReviewResponse | null;
  setPayload: React.Dispatch<React.SetStateAction<TaskReviewResponse | null>>;
  draftSheets: Record<number, DraftReviewSheet>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  onConfirmed?: () => void;
}) {
  const { payload, setPayload, draftSheets, setError, onConfirmed } = opts;

  const [saving, setSaving] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function saveDraft(): Promise<number | null> {
    if (!payload) {
      return null;
    }

    setSaving(true);
    setError(null);
    setActionMessage(null);

    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${payload.task_id}/structure-versions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildStructureVersionSaveRequest(payload, draftSheets)),
      });
      const data = (await response.json()) as StructureVersionSaveResponse | { detail?: string };

      if (!response.ok) {
        throw new Error(
          typeof data === "object" && data && "detail" in data && data.detail
            ? data.detail
            : "Failed to save structure draft",
        );
      }

      const result = data as StructureVersionSaveResponse;

      setPayload((current) =>
        current
          ? applyDraftSheetsToReview(
              current,
              draftSheets,
              result.structure_version,
              result.status,
            )
          : current,
      );
      setActionMessage(`Saved structure v${result.structure_version}`);
      return result.structure_version;
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Failed to save structure draft",
      );
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function confirmStructure() {
    if (!payload) {
      return;
    }

    const latestStructureVersion = await saveDraft();
    if (latestStructureVersion === null) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${payload.task_id}/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ structure_version: latestStructureVersion }),
      });
      const data = (await response.json()) as ConfirmStructureVersionResponse | { detail?: string };

      if (!response.ok) {
        throw new Error(
          typeof data === "object" && data && "detail" in data && data.detail
            ? data.detail
            : "Failed to confirm structure",
        );
      }

      const result = data as ConfirmStructureVersionResponse;

      setPayload((current) =>
        current
          ? applyDraftSheetsToReview(
              current,
              draftSheets,
              result.structure_version,
              result.status,
            )
          : current,
      );
      setActionMessage(`Confirmed structure v${result.confirmed_structure_version}`);
      onConfirmed?.();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Failed to confirm structure",
      );
    } finally {
      setSaving(false);
    }
  }

  return {
    saving,
    actionMessage,
    saveDraft,
    confirmStructure,
  };
}