import { useState } from "react";
import type { ResultsData } from "./useResultsData";

type Props = {
  data: ResultsData;
};

export function OverviewCards({ data }: Props) {
  const { summary, insight, chartSpecs, mergedIssues } = data;
  const [expanded, setExpanded] = useState(false);

  const validationCount = mergedIssues.filter(
    (i) => i.detection_source === "validation",
  ).length;
  const anomalyCount = mergedIssues.filter(
    (i) => i.detection_source !== "validation",
  ).length;
  const chartCount = chartSpecs?.total ?? 0;
  const execSummary = insight?.executive_summary ?? "暂无分析结论";

  const cards = [
    { label: "校验问题", value: validationCount, color: "#e74c3c" },
    { label: "业务异常", value: anomalyCount, color: "#e67e22" },
    { label: "图表", value: chartCount, color: "#2ecc71" },
    { label: "AI 分析", value: insight ? "已完成" : "未完成", color: "#3498db" },
  ];

  return (
    <section className="overview-section">
      <div className="overview-cards">
        {cards.map((card) => (
          <div className="overview-card" key={card.label}>
            <span className="overview-card-value" style={{ color: card.color }}>
              {card.value}
            </span>
            <span className="overview-card-label">{card.label}</span>
          </div>
        ))}
      </div>

      {insight && (
        <div className="exec-summary">
          <div
            className="exec-summary-header"
            onClick={() => setExpanded(!expanded)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") setExpanded(!expanded);
            }}
          >
            <p className="exec-summary-label">
              AI 分析摘要 {expanded ? "▲" : "▼"}
            </p>
            <p className="exec-summary-text">{execSummary}</p>
            {insight.model_name && (
              <span className="exec-summary-model">Model: {insight.model_name}</span>
            )}
          </div>

          {expanded && (
            <div className="insight-detail">
              {insight.key_findings.length > 0 && (
                <div className="insight-group">
                  <h3>关键发现 ({insight.key_findings.length})</h3>
                  {insight.key_findings.map((f, i) => (
                    <div key={i} className="insight-item">
                      <div className="insight-item-header">
                        <span className={`severity-badge severity-${f.severity}`}>
                          {f.severity}
                        </span>
                        <strong>{f.title}</strong>
                      </div>
                      <p>{f.description}</p>
                      {f.evidence && f.evidence.length > 0 && (
                        <div className="evidence-list">
                          {f.evidence.map((e, j) => (
                            <span key={j} className="evidence-tag">
                              {e.sheet} {e.metric} [{e.row},{e.col}] = {e.value}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {insight.risks.length > 0 && (
                <div className="insight-group">
                  <h3>风险 ({insight.risks.length})</h3>
                  {insight.risks.map((r, i) => (
                    <div key={i} className="insight-item">
                      <strong>{r.title}</strong>
                      <p>{r.description}</p>
                      {r.mitigation && (
                        <p className="mitigation">对策: {r.mitigation}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {insight.recommendations.length > 0 && (
                <div className="insight-group">
                  <h3>建议 ({insight.recommendations.length})</h3>
                  {insight.recommendations.map((r, i) => (
                    <div key={i} className="insight-item">
                      <span className={`priority-badge priority-${r.priority}`}>
                        {r.priority}
                      </span>
                      <strong> {r.title}</strong>
                      <p>{r.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}