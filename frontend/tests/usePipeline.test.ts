import { describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePipeline } from "../src/modules/pipeline/usePipeline";

describe("usePipeline", () => {
  it("starts with all steps pending", () => {
    const { result } = renderHook(() => usePipeline());
    expect(result.current.steps).toHaveLength(7);
    expect(result.current.steps.every((s) => s.status === "pending")).toBe(true);
    expect(result.current.running).toBe(false);
  });

  it("has correct step keys", () => {
    const { result } = renderHook(() => usePipeline());
    const keys = result.current.steps.map((s) => s.key);
    expect(keys).toEqual(["infer", "rules", "validate", "anomaly", "summarize", "analyze", "chart"]);
  });

  it("allDone is false initially", () => {
    const { result } = renderHook(() => usePipeline());
    expect(result.current.allDone).toBe(false);
  });
});
