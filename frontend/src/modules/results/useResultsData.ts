import { useEffect, useState } from "react";
import type {
  SummaryRecord,
  InsightRecord,
  ChartSpecRecord,
  ValidationIssueItem,
  AnomalyIssueItem,
  IssueItem,
} from "../../types/results";

import { api, ApiError } from "../api-client";

export type ResultsData = {
  summary: SummaryRecord | null;
  insight: InsightRecord | null;
  chartSpecs: ChartSpecRecord | null;
  validationIssues: ValidationIssueItem[];
  anomalyIssues: AnomalyIssueItem[];
  mergedIssues: IssueItem[];
  loading: boolean;
  error: string | null;
};

export function useResultsData(taskId: string): ResultsData {
  const [summary, setSummary] = useState<SummaryRecord | null>(null);
  const [insight, setInsight] = useState<InsightRecord | null>(null);
  const [chartSpecs, setChartSpecs] = useState<ChartSpecRecord | null>(null);
  const [validationIssues, setValidationIssues] = useState<ValidationIssueItem[]>([]);
  const [anomalyIssues, setAnomalyIssues] = useState<AnomalyIssueItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchAll() {
      setLoading(true);
      setError(null);

      try {
        const [
          sumRes, insRes, chartRes, valRes, anoRes,
        ] = await Promise.all([
          api.get(`/tasks/${taskId}/summary`),
          api.get(`/tasks/${taskId}/insights`),
          api.get(`/tasks/${taskId}/chart-specs`),
          api.get(`/tasks/${taskId}/validation-issues`),
          api.get(`/tasks/${taskId}/anomaly-issues`),
        ]);

        if (!cancelled) {
          if (sumRes.ok) setSummary(await sumRes.json());
          if (insRes.ok) setInsight(await insRes.json());
          if (chartRes.ok) setChartSpecs(await chartRes.json());

          if (valRes.ok) {
            const v = await valRes.json();
            setValidationIssues(v.issues ?? []);
          }
          if (anoRes.ok) {
            const a = await anoRes.json();
            setAnomalyIssues(a.issues ?? []);
          }
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load results");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void fetchAll();
    return () => { cancelled = true; };
  }, [taskId]);

  // Merge validation + anomaly issues into unified list
  const mergedIssues: IssueItem[] = [
    ...validationIssues.map((v) => ({
      id: v.id,
      sheet_id: v.sheet_id,
      row_index: v.row_index,
      col_index: v.col_index,
      issue_type: v.issue_type,
      severity: v.severity,
      reason: v.formula_text
        ? `${v.formula_text}: expected ${v.expected_value}, actual ${v.actual_value}`
        : v.issue_type,
      expected_value: v.expected_value,
      actual_value: v.actual_value,
      detection_source: "validation",
    })),
    ...anomalyIssues.map((a) => ({
      id: a.id,
      sheet_id: a.sheet_id,
      row_index: a.row_index,
      col_index: a.col_index,
      issue_type: a.issue_type,
      severity: a.severity,
      reason: a.reason,
      metric_name: a.metric_name ?? undefined,
      detection_source: a.detection_source,
      score: a.score ?? undefined,
    })),
  ];

  return {
    summary,
    insight,
    chartSpecs,
    validationIssues,
    anomalyIssues,
    mergedIssues,
    loading,
    error,
  };
}