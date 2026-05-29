import { useState } from "react";
import { UploadPage } from "./pages/UploadPage";
import { TaskReviewPage } from "./pages/TaskReviewPage";
import { ResultsPage } from "./pages/ResultsPage";
import { ErrorBoundary } from "./components/ErrorBoundary";

type Phase = "upload" | "review" | "results";

export function App() {
  const [phase, setPhase] = useState<Phase>("upload");
  const [activeTaskId, setActiveTaskId] = useState<string>("1");
  const [resultsTaskId, setResultsTaskId] = useState("1");

  if (phase === "upload") {
    return (
      <ErrorBoundary>
      <UploadPage
        onTaskReady={(taskId) => {

          setActiveTaskId(String(taskId));
          setResultsTaskId(String(taskId));
          setPhase("review");
        }}
      />
      </ErrorBoundary>
    );
  }

  if (phase === "results") {
    return (
      <ErrorBoundary>
      <ResultsPage
        taskId={resultsTaskId}
        onBack={() => setPhase("review")}
      />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
    <TaskReviewPage
      taskId={activeTaskId}
      onViewResults={() => {

        setResultsTaskId(activeTaskId);
        setPhase("results");
      }}
    />
    </ErrorBoundary>
  );
}