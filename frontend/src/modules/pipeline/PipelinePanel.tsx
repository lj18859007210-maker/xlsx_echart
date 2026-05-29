import type { PipelineStep } from "./usePipeline";

type Props = {
  steps: PipelineStep[];
  running: boolean;
  allDone: boolean;
  hasFailure: boolean;
  onViewResults?: () => void;
};

const statusIcon: Record<string, string> = {
  pending: "○",
  running: "◉",
  done: "✓",
  failed: "✗",
  skipped: "→",
};

export function PipelinePanel({ steps, running, allDone, hasFailure, onViewResults }: Props) {
  if (steps.every((s) => s.status === "pending")) return null;

  return (
    <div className="pipeline-panel">
      <div className="pipeline-heading">
        <p className="mini-label">处理管线</p>
        <h2>
          {running ? "正在处理..." : hasFailure ? "处理中断" : allDone ? "处理完成" : "等待执行"}
        </h2>
      </div>

      <ol className="pipeline-steps">
        {steps.map((step) => (
          <li
            key={step.key}
            className={`pipeline-step ${step.status}`}
          >
            <span className="pipeline-step-icon">{statusIcon[step.status] ?? "○"}</span>
            <span className="pipeline-step-label">{step.label}</span>
            {step.message && (
              <span className="pipeline-step-msg">{step.message}</span>
            )}
          </li>
        ))}
      </ol>

      {allDone && onViewResults && (
        <button className="pipeline-action primary" onClick={onViewResults}>
          查看分析结果 →
        </button>
      )}
    </div>
  );
}
