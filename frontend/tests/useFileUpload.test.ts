import { describe, expect, it } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useFileUpload } from "../src/modules/upload/useFileUpload";

describe("useFileUpload", () => {
  it("starts in idle state", () => {
    const { result } = renderHook(() => useFileUpload());
    expect(result.current.uploadState).toBe("idle");
    expect(result.current.progress).toBe(0);
    expect(result.current.result).toBeNull();
  });

  it("resets to idle", () => {
    const { result } = renderHook(() => useFileUpload());
    act(() => { result.current.reset(); });
    expect(result.current.uploadState).toBe("idle");
  });

  it("has upload function", () => {
    const { result } = renderHook(() => useFileUpload());
    expect(typeof result.current.upload).toBe("function");
  });
});
