import type { ResultItem } from "./types";

const KEY = "a8finder.bookmarks.v1";

function isBookmark(value: unknown): value is ResultItem {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.url === "string" &&
    typeof v.title === "string" &&
    typeof v.snippet === "string" &&
    typeof v.source === "string" &&
    typeof v.source_label === "string"
  );
}

export function loadBookmarks(): ResultItem[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isBookmark) : [];
  } catch {
    return [];
  }
}

function save(list: ResultItem[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {
    /* 저장 실패(용량 등)는 무시 */
  }
}

export function isBookmarked(url: string): boolean {
  return loadBookmarks().some((b) => b.url === url);
}

/** 북마크 토글. 추가되면 true, 제거되면 false 반환. */
export function toggleBookmark(item: ResultItem): boolean {
  const list = loadBookmarks();
  const idx = list.findIndex((b) => b.url === item.url);
  if (idx >= 0) {
    list.splice(idx, 1);
    save(list);
    return false;
  }
  list.unshift(item);
  save(list);
  return true;
}

export function removeBookmark(url: string): void {
  save(loadBookmarks().filter((b) => b.url !== url));
}
