import { useCallback, useRef, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type UploadState = "idle" | "uploading" | "success" | "error";

type UploadResult = {
  file_id: number;
  task_id: number;
  status: string;
} | null;

export function useFileUpload() {
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<UploadResult>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const xhrRef = useRef<XMLHttpRequest | null>(null);

  const upload = useCallback((file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;

    setUploadState("uploading");
    setProgress(0);
    setResult(null);
    setErrorMessage(null);

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        setProgress(Math.round((event.loaded / event.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const data = JSON.parse(xhr.responseText) as {
          file_id: number;
          task_id: number;
          status: string;
        };
        setResult(data);
        setUploadState("success");
        setProgress(100);
      } else {
        let msg = "Upload failed";
        try {
          const err = JSON.parse(xhr.responseText) as { detail?: string };
          if (err.detail) msg = err.detail;
        } catch {
          // use default
        }
        setErrorMessage(msg);
        setUploadState("error");
      }
    });

    xhr.addEventListener("error", () => {
      setErrorMessage("Network error - is the backend running?");
      setUploadState("error");
    });

    xhr.addEventListener("abort", () => {
      setUploadState("idle");
    });

    xhr.open("POST", `${API_BASE_URL}/files/upload`);
    xhr.send(formData);
  }, []);

  const reset = useCallback(() => {
    xhrRef.current?.abort();
    xhrRef.current = null;
    setUploadState("idle");
    setProgress(0);
    setResult(null);
    setErrorMessage(null);
  }, []);

  return { uploadState, progress, result, errorMessage, upload, reset };
}
