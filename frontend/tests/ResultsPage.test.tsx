import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ResultsPage } from "../src/pages/ResultsPage";

vi.mock("../src/modules/results/useResultsData", () => ({
  useResultsData: () => ({
    loading: false,
    error: null,
    summary: null,
    insights: null,
    chartSpecs: null,
    validationIssues: null,
    anomalyIssues: null,
    mergedIssues: [],
  }),
}));

vi.mock("../src/modules/api-client", () => ({
  api: { get: vi.fn(() => Promise.resolve({ sheets: [] })) },
}));

describe("ResultsPage", () => {
  it("renders task id in header", () => {
    render(<ResultsPage taskId="1" onBack={() => {}} />);
    expect(screen.getByText(/Task #1/)).toBeTruthy();
  });

  it("renders overview cards section", () => {
    const { container } = render(<ResultsPage taskId="1" onBack={() => {}} />);
    expect(container.querySelector(".results-page")).toBeTruthy();
  });
});
