import { type DragEvent, useRef, useState } from "react";
import { useFileUpload } from "../modules/upload/useFileUpload";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type UploadPageProps = {
  onTaskReady: (taskId: number) => void;
};

export function UploadPage({ onTaskReady }: UploadPageProps) {
  const { uploadState, progress, result, errorMessage, upload, reset } =
    useFileUpload();
  const [dragOver, setDragOver] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);
  const dropCounter = useRef(0);

  const handleEnterReview = async () => {
    if (!result) return;
    setParsing(true);
    setParseError(null);
    try {
      const res = await fetch(`${API_BASE}/tasks/${result.task_id}/parse`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? "解析失败");
      }
      onTaskReady(result.task_id);
    } catch (e) {
      setParseError(e instanceof Error ? e.message : "解析失败");
    } finally {
      setParsing(false);
    }
  };

  const dragEvents = {
    onDragEnter: (e: DragEvent) => {
      e.preventDefault(); e.stopPropagation();
      dropCounter.current += 1;
      setDragOver(true);
    },
    onDragLeave: (e: DragEvent) => {
      e.preventDefault(); e.stopPropagation();
      dropCounter.current -= 1;
      if (dropCounter.current <= 0) { dropCounter.current = 0; setDragOver(false); }
    },
    onDragOver: (e: DragEvent) => { e.preventDefault(); e.stopPropagation(); },
    onDrop: (e: DragEvent) => {
      e.preventDefault(); e.stopPropagation();
      setDragOver(false); dropCounter.current = 0;
      const file = e.dataTransfer.files[0];
      if (!file) return;
      if (!file.name.endsWith(".xlsx")) { alert("仅支持 .xlsx 文件"); return; }
      upload(file);
    },
  };

  return (
    <div className="upload-page">
      <div className="upload-hero">
        <p className="upload-kicker">表格分析 · 图表系统</p>
        <h1 className="upload-heading">
          上传 Excel · 自动解析 · 一键出图
        </h1>
        <p className="upload-desc">
          拖入一个 .xlsx 文件，系统会自动完成结构识别、公式校验、异常检测、AI 分析与图表渲染
        </p>
      </div>

      <div className="upload-stage">
        {uploadState === "idle" && (
          <label
            className={`upload-dropzone${dragOver ? " drag-over" : ""}`}
            {...dragEvents}
          >
            <input type="file" accept=".xlsx" className="upload-input-hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); }} />
            <span className="upload-dropzone-mark">+</span>
            <span className="upload-dropzone-main">拖拽 .xlsx 文件到此处</span>
            <span className="upload-dropzone-sub">或点击选择文件</span>
          </label>
        )}

        {uploadState === "uploading" && (
          <div className="upload-progress">
            <div className="upload-progress-rail">
              <div className="upload-progress-track" style={{ width: `${progress}%` }} />
            </div>
            <span className="upload-progress-label">上传中 {progress}%</span>
          </div>
        )}

        {uploadState === "success" && result && (
          <div className="upload-outcome">
            <div className="upload-outcome-badge success">
              <span className="upload-outcome-icon">{String.fromCharCode(0x2713)}</span>
              <span>上传成功</span>
            </div>
            <dl className="upload-outcome-meta">
              <div><dt>任务编号</dt><dd>{result.task_id}</dd></div>
              <div><dt>状态</dt><dd>{result.status}</dd></div>
            </dl>

            {parsing && (
              <div className="upload-progress">
                <div className="upload-progress-rail">
                  <div className="upload-progress-track parsing" />
                </div>
                <span className="upload-progress-label">正在解析表格...</span>
              </div>
            )}

            {parseError && (
              <p className="upload-outcome-reason">{parseError}</p>
            )}

            <div className="upload-outcome-actions">
              <button
                className="upload-btn primary"
                onClick={handleEnterReview}
                disabled={parsing}
              >
                {parsing ? "解析中..." : "进入结构确认 →"}
              </button>
              <button className="upload-btn ghost" onClick={reset} disabled={parsing}>
                上传另一个文件
              </button>
            </div>
          </div>
        )}

        {uploadState === "error" && (
          <div className="upload-outcome">
            <div className="upload-outcome-badge error">
              <span className="upload-outcome-icon">{String.fromCharCode(0x2717)}</span>
              <span>上传失败</span>
            </div>
            <p className="upload-outcome-reason">{errorMessage}</p>
            <button className="upload-btn ghost" onClick={reset}>重试</button>
          </div>
        )}
      </div>
    </div>
  );
}
