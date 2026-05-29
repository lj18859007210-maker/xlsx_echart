import { useState } from "react";
import type { IssueItem } from "../../types/results";

type Props = {
  issues: IssueItem[];
  onIssueClick?: (issue: IssueItem) => void;
};

const SEVERITY_COLORS: Record<string, string> = {
  error: "#e74c3c",
  critical: "#e74c3c",
  high: "#e67e22",
  warning: "#f39c12",
  medium: "#f39c12",
  info: "#3498db",
  low: "#95a5a6",
};

const SEVERITY_ORDER: Record<string, number> = {
  error: 0,
  critical: 0,
  high: 1,
  warning: 2,
  medium: 2,
  info: 3,
  low: 4,
};

export function IssueList({ issues, onIssueClick }: Props) {
  const [sortBy, setSortBy] = useState<"severity" | "type" | "sheet">("severity");
  const [filterSource, setFilterSource] = useState<"all" | "validation" | "anomaly">("all");

  const filtered = issues.filter((i) => {
    if (filterSource === "validation") return i.detection_source === "validation";
    if (filterSource === "anomaly") return i.detection_source !== "validation";
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "severity") {
      return (SEVERITY_ORDER[a.severity] ?? 99) - (SEVERITY_ORDER[b.severity] ?? 99);
    }
    if (sortBy === "type") return a.issue_type.localeCompare(b.issue_type);
    return (a.sheet_id ?? 0) - (b.sheet_id ?? 0);
  });

  if (issues.length === 0) {
    return (
      <section className="issue-list-section">
        <h2>问题列表</h2>
        <div className="empty-state">
          <p>暂无问题 👏</p>
        </div>
      </section>
    );
  }

  return (
    <section className="issue-list-section">
      <div className="issue-list-header">
        <h2>问题列表 ({filtered.length})</h2>
        <div className="issue-list-controls">
          <select value={filterSource} onChange={(e) => setFilterSource(e.target.value as typeof filterSource)}>
            <option value="all">全部</option>
            <option value="validation">校验问题</option>
            <option value="anomaly">业务异常</option>
          </select>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
            <option value="severity">按严重度</option>
            <option value="type">按类型</option>
            <option value="sheet">按 Sheet</option>
          </select>
        </div>
      </div>

      <div className="issue-list">
        {sorted.map((issue, idx) => (
          <div
            key={issue.id ?? idx}
            className="issue-row"
            onClick={() => onIssueClick?.(issue)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") onIssueClick?.(issue);
            }}
          >
            <span
              className="issue-severity-dot"
              style={{ background: SEVERITY_COLORS[issue.severity] ?? "#95a5a6" }}
            />
            <div className="issue-row-content">
              <div className="issue-row-top">
                <span className="issue-type">{issue.issue_type}</span>
                <span className="issue-severity-label">{issue.severity}</span>
                {issue.detection_source && (
                  <span className="issue-source">
                    {issue.detection_source === "validation" ? "校验" : "异常检测"}
                  </span>
                )}
              </div>
              <p className="issue-reason">{issue.reason}</p>
              <div className="issue-row-meta">
                {issue.metric_name && <span>{issue.metric_name}</span>}
                <span>
                  [{issue.row_index}, {issue.col_index}]
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}