const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  let res: Response;
  try {
    res = await fetch(url, {
      ...options,
      headers: {
        ...(options.method === "POST" ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new ApiError(0, "无法连接服务器，请确认后端已启动");
  }

  if (!res.ok) {
    let detail = "";
    try {
      const errBody = await res.json();
      detail = (errBody as { detail?: string }).detail ?? res.statusText;
    } catch {
      detail = res.statusText || `HTTP ${res.status}`;
    }

    if (res.status >= 500) {
      detail = `服务器内部错误：${detail}`;
    }

    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  get: <T = unknown>(path: string) => request<T>(path),
  post: <T = unknown>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : "{}" }),
};

export { ApiError };
