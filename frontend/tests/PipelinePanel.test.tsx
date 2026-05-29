import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { PipelinePanel } from "../src/modules/pipeline/PipelinePanel";
import type { PipelineStep } from "../src/modules/pipeline/usePipeline";

describe("PipelinePanel", () => {
  it("renders nothing when all pending", () => {
    const steps: PipelineStep[] = [
      { key: "a", label: "A", status: "pending", message: "" },
    ];
    const { container } = render(
      <PipelinePanel steps={steps} running={false} allDone={false} hasFailure={false} />
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders steps when some done", () => {
    const steps: PipelineStep[] = [
      { key: "a", label: "Step A", status: "done", message: "ok" },
      { key: "b", label: "Step B", status: "running", message: "" },
    ];
    render(
      <PipelinePanel steps={steps} running={true} allDone={false} hasFailure={false} />
    );
    expect(screen.getByText("Step A")).toBeTruthy();
  });

  it("shows view results button when all done", () => {
    const steps: PipelineStep[] = [
      { key: "a", label: "Step A", status: "done", message: "" },
    ];
    render(
      <PipelinePanel steps={steps} running={false} allDone={true} hasFailure={false} onViewResults={() => {}} />
    );
    expect(screen.getByText(/查看分析结果/)).toBeTruthy();
  });
});
