import { useState } from "react";
import { TaskReviewPage } from "./pages/TaskReviewPage";
import { ResultsPage } from "./pages/ResultsPage";

type Phase = "review" | "results";

export function App() {
  const [phase, setPhase] = useState<Phase>("review");
  const [taskIdInput, setTaskIdInput] = useState("1");
  const [resultsTaskId, setResultsTaskId] = useState("1");

  if (phase === "results") {
    return (
      <ResultsPage
        taskId={resultsTaskId}
        onBack={() => setPhase("review")}
      />
    );
  }

  return (
    <div>
      <TaskReviewPage />
      <div className="phase-switch-bar">
        <label className="phase-switch-label">
          <span>Task ID</span>
          <input
            className="phase-switch-input"
            value={taskIdInput}
            onChange={(e) => setTaskIdInput(e.target.value)}
            placeholder="输入 Task ID"
          />
        </label>
        <button
          type="button"
          className="phase-switch-button"
          onClick={() => {
            setResultsTaskId(taskIdInput);
            setPhase("results");
          }}
        >
          查看分析结果 →
        </button>
      </div>
    </div>
  );
}