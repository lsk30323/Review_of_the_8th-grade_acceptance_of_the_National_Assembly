import type { MetaResponse, SearchParams, SearchResponse } from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson<T>(url: string): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new ApiError(0, "네트워크에 연결할 수 없습니다. 백엔드가 실행 중인지 확인하세요.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* ignore parse error */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export function fetchMeta(): Promise<MetaResponse> {
  return getJson<MetaResponse>(`${BASE}/api/meta`);
}

export function search(p: SearchParams): Promise<SearchResponse> {
  const qs = new URLSearchParams({
    q: p.q,
    sources: p.sources.join(","),
    sort: p.sort,
    page: String(p.page),
    page_size: String(p.pageSize),
  });
  return getJson<SearchResponse>(`${BASE}/api/search?${qs.toString()}`);
}
