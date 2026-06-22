export interface ResultItem {
  title: string;
  url: string;
  snippet: string;
  source: string;
  source_label: string;
  posted_at: string | null;
  score: number;
  matched_query?: string | null;
}

export interface SearchResponse {
  query: string;
  variants: string[];
  total: number;
  page: number;
  page_size: number;
  sort: string;
  categories: string[];
  cached: boolean;
  quota_remaining: number | null;
  results: ResultItem[];
}

export interface SourceInfo {
  key: string;
  label: string;
}

export interface MetaResponse {
  naver_configured: boolean;
  demo_mode: boolean;
  secondary_available: boolean;
  active_adapters: string[];
  categories: SourceInfo[];
  quota_remaining: number | null;
}

export type SortKey = "sim" | "date";

export interface SearchParams {
  q: string;
  sources: string[];
  sort: SortKey;
  page: number;
  pageSize: number;
}
