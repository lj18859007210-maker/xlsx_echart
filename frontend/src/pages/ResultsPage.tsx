import { useCallback, useEffect, useState } from "react";
import { useResultsData } from "../modules/results/useResultsData";
import { OverviewCards } from "../modules/results/OverviewCards";
import { IssueList } from "../modules/results/IssueList";
import { ChartCanvas } from "../modules/results/ChartCanvas";
import { SourceTable } from "../modules/results/SourceTable";
import type { IssueItem } from "../types/results";
import type { ReviewSheetSnapshot } from "../types/review";

type Props = {
  taskId: string;
  onBack: () => void;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

export function ResultsPage({ taskId, onBack }: Props) {
  const data = useResultsData(taskId);
  const [highlightRow, setHighlightRow] = useState<number | null>(null);
  const [highlightCol, setHighlightCol] = useState<number | null>(null);
  const [reviewGrid, setReviewGrid] = useState<Array<Array<string | null>>>([]);
  const [reviewSheetName, setReviewSheetName] = useState("");

  // Load first sheet's aligned_grid for source table
  useEffect(() => {
    let cancelled = false;
    void fetch(`${API_BASE}/tasks/${taskId}/review`)
      .then((r) => r.json())
      .then((d: { sheets?: ReviewSheetSnapshot[] }) => {
        if (!cancelled) {
          const first = d.sheets?.[0];
          if (first) {
            setReviewGrid(first.aligned_grid);
            setReviewSheetName(first.sheet_name);
          }
        }
      });
    return () => { cancelled = true; };
  }, [taskId]);

  const handleIssueClick = useCallback((issue: IssueItem) => {
    setHighlightRow(issue.row_index);
    setHighlightCol(issue.col_index);
  }, []);

  const handleChartClick = useCallback((_seriesIndex: number, dataIndex: number) => {
    setHighlightRow(dataIndex + 1);
    setHighlightCol(null);
  }, []);

  if (data.loading) {
    return (
      <main className="results-page">
        <div className="results-skeleton">
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
          <div className="skeleton-card" />
        </div>
      </main>
    );
  }

  if (data.error) {
    return (
      <main className="results-page">
        <div className="error-banner">{data.error}</div>
        <button onClick={onBack} type="button" className="back-button">
          鈫?杩斿洖
        </button>
      </main>
    );
  }

  return (
    <main className="results-page">
      <header className="results-header">
        <button onClick={onBack} type="button" className="back-button">
          鈫?杩斿洖缁撴瀯缂栬緫
        </button>
        <h1>鍒嗘瀽缁撴灉 鈥?Task #{taskId}</h1>
      </header>

      <OverviewCards data={data} />

      <div className="results-grid">
        <ChartCanvas
          charts={data.chartSpecs?.charts ?? []}
          onDataPointClick={handleChartClick}
        />
        <IssueList
          issues={data.mergedIssues}
          onIssueClick={handleIssueClick}
        />
      </div>

      <SourceTable
        grid={reviewGrid}
        sheetName={reviewSheetName}
        highlightRow={highlightRow}
        highlightCol={highlightCol}
      />
    </main>
  );
}