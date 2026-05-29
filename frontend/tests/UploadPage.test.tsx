import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { UploadPage } from "../src/pages/UploadPage";

describe("UploadPage", () => {
  it("renders heading", () => {
    render(<UploadPage onTaskReady={() => {}} />);
    expect(screen.getByRole("heading", { level: 1 })).toBeTruthy();
  });

  it("renders dropzone text", () => {
    render(<UploadPage onTaskReady={() => {}} />);
    const items = screen.getAllByText(/拖拽|或点击选择文件/);
    expect(items.length).toBeGreaterThan(0);
  });
});
