import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
// api-client available as: import { api } from "../api-client";

export type StepStatus = "pending" | "running" | "done" | "failed" | "skipped";

export type PipelineStep = {
  key: string;
  label: string;
  status: StepStatus;
  message: string;
};

const STEP_DEFS: { key: string; label: string; endpoint?: string; method?: string; deps: string[] }[] = [
  { key: "infer",     label: "推导公式", endpoint: "/infer-formulas",    method: "POST", deps: [] },
  { key: "rules",     label: "规则检查", endpoint: "/formula-rules",      method: "GET",  deps: ["infer"] },
  { key: "validate",  label: "公式校验", endpoint: "/validate",           method: "POST", deps: ["rules"] },
  { key: "anomaly",   label: "异常检测", endpoint: "/detect-anomalies",   method: "POST", deps: [] },
  { key: "summarize", label: "摘要压缩", endpoint: "/summarize",          method: "POST", deps: [] },
  { key: "analyze",   label: "AI 分析",           endpoint: "/analyze",           method: "POST", deps: [] },
  { key: "chart",     label: "图表推荐", endpoint: "/recommend-charts",   method: "POST", deps: [] },
];

export function usePipeline() {
  const [steps, setSteps] = useState<PipelineStep[]>(
    STEP_DEFS.map((s) => ({ ...s, status: "pending" as StepStatus, message: "" }))
  );

  const [running, setRunning] = useState(false);

  const run = async (taskId: string) => {
    if (running) return;
    setRunning(true);

    const updated: PipelineStep[] = STEP_DEFS.map((s) => ({ ...s, status: "pending" as StepStatus, message: "" }));
    setSteps([...updated]);

    let hasGap = false;

    for (let i = 0; i < updated.length; i++) {
      const step = updated[i];
      if (!step.endpoint) continue;

      // Check if any dependency failed
      const failedDeps = (step as typeof STEP_DEFS[number] & { deps?: string[] }).deps?.filter(
        (depKey) => updated.find((s) => s.key === depKey)?.status === "failed"
      );
      if (failedDeps && failedDeps.length > 0) {
        step.status = "skipped";
        step.message = `依赖步骤失败：${failedDeps.join(", ")}`;
        setSteps([...updated]);
        continue;
      }

      // Check gap condition for validate
      if (step.key === "validate" && hasGap) {
        step.status = "skipped";
        step.message = "无可用公式规则，跳过校验";
        setSteps([...updated]);
        continue;
      }

      step.status = "running";
      step.message = "";
      setSteps([...updated]);

      try {
        if (step.key === "rules") {
          const res = await fetch(`${API_BASE}/tasks/${taskId}${step.endpoint}`);
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          const filtered = data.filtered ?? 0;
          if (filtered > 0) {
            hasGap = true;
            step.message = `通过 ${data.passed ?? 0} 条，过滤 ${filtered} 条，待确认后续操作`;
          } else {
            step.message = `通过 ${data.passed ?? 0} 条规则`;
          }
        } else {
          const res = await fetch(`${API_BASE}/tasks/${taskId}${step.endpoint}`, {
            method: step.method,
            headers: step.method === "POST" ? { "Content-Type": "application/json" } : undefined,
            body: step.method === "POST" ? "{}" : undefined,
          });
          if (!res.ok) throw new Error(await res.text());
          const data = await res.json();
          step.message = data.total_issues !== undefined
            ? `发现 ${data.total_issues} 个问题`
            : data.charts !== undefined
              ? `生成 ${data.charts.length} 个图表`
              : "完成";
        }
        step.status = "done";
      } catch (e) {
        step.status = "failed";
        step.message = e instanceof Error ? e.message : "执行失败";
        // DON'T break - continue to next step
      }

      setSteps([...updated]);
    }

    setRunning(false);
  };

  const allDone = steps.length > 0 && steps.every((s) => s.status === "done" || s.status === "skipped");
  const hasFailure = steps.some((s) => s.status === "failed");

  return { steps, running, allDone, hasFailure, run };
}
