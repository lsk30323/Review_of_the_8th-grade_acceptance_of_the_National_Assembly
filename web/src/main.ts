import "./styles.css";
import { ApiError, fetchMeta, search } from "./api";
import { isBookmarked, loadBookmarks, toggleBookmark } from "./bookmarks";
import {
  el,
  renderCard,
  renderResultMeta,
  renderSkeletons,
  renderState,
} from "./render";
import type { ResultItem, SortKey, SourceInfo } from "./types";

const DEFAULT_SOURCES = ["blog", "cafe", "web"];
const PAGE_SIZE = 20;
const PREFS_KEY = "a8finder.prefs.v1";

interface Prefs {
  sources: string[];
  sort: SortKey;
  theme: "light" | "dark";
}

const $ = <T extends HTMLElement>(sel: string): T => {
  const node = document.querySelector<T>(sel);
  if (!node) throw new Error(`missing element: ${sel}`);
  return node;
};

const form = $<HTMLFormElement>("#search-form");
const input = $<HTMLInputElement>("#search-input");
const sourceChips = $("#source-chips");
const sortToggle = $("#sort-toggle");
const resultsEl = $("#results");
const resultMetaEl = $("#result-meta");
const loadMoreWrap = $("#load-more-wrap");
const bookmarksEl = $("#bookmarks");
const bmCountEl = $("#bm-count");
const statusChip = $("#status-chip");
const themeToggle = $<HTMLButtonElement>("#theme-toggle");
const tabsEl = $("#tabs");
const viewResults = $("#view-results");
const viewBookmarks = $("#view-bookmarks");

let selectedSources = new Set<string>(DEFAULT_SOURCES);
let sort: SortKey = "sim";
let currentQuery = "";
let currentPage = 1;
let totalResults = 0;
let accumulated: ResultItem[] = [];
let loading = false;
let categories: SourceInfo[] = [
  { key: "blog", label: "블로그" },
  { key: "cafe", label: "카페" },
  { key: "web", label: "웹문서" },
  { key: "news", label: "뉴스" },
];

// --------------------------------------------------------------------- prefs
function loadPrefs(): Partial<Prefs> {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}");
  } catch {
    return {};
  }
}

function savePrefs(): void {
  const prefs: Prefs = {
    sources: [...selectedSources],
    sort,
    theme: (document.documentElement.dataset.theme as "light" | "dark") ?? "light",
  };
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* ignore */
  }
}

// --------------------------------------------------------------------- theme
function applyTheme(theme: "light" | "dark"): void {
  document.documentElement.dataset.theme = theme;
  themeToggle.textContent = theme === "dark" ? "☀️" : "🌙";
  themeToggle.setAttribute("aria-label", theme === "dark" ? "라이트 모드" : "다크 모드");
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", theme === "dark" ? "#0e0f13" : "#1f3a8a");
}

// --------------------------------------------------------------------- chips
function buildSourceChips(): void {
  sourceChips.replaceChildren();
  for (const cat of categories) {
    const active = selectedSources.has(cat.key);
    const chip = el("button", {
      class: `chip${active ? " is-active" : ""}`,
      type: "button",
      "aria-pressed": active,
      "data-key": cat.key,
      text: cat.label,
    }) as HTMLButtonElement;
    chip.addEventListener("click", () => {
      if (selectedSources.has(cat.key)) {
        if (selectedSources.size === 1) return; // 최소 1개 유지
        selectedSources.delete(cat.key);
      } else {
        selectedSources.add(cat.key);
      }
      chip.classList.toggle("is-active");
      chip.setAttribute("aria-pressed", String(selectedSources.has(cat.key)));
      savePrefs();
      if (currentQuery) void runSearch(true);
    });
    sourceChips.append(chip);
  }
}

function buildSortToggle(): void {
  sortToggle.replaceChildren();
  const options: { key: SortKey; label: string }[] = [
    { key: "sim", label: "관련성순" },
    { key: "date", label: "최신순" },
  ];
  for (const opt of options) {
    const btn = el("button", {
      class: `seg${sort === opt.key ? " is-active" : ""}`,
      type: "button",
      "aria-pressed": sort === opt.key,
      "data-sort": opt.key,
      text: opt.label,
    }) as HTMLButtonElement;
    btn.addEventListener("click", () => {
      if (sort === opt.key) return;
      sort = opt.key;
      buildSortToggle();
      savePrefs();
      if (currentQuery) void runSearch(true);
    });
    sortToggle.append(btn);
  }
}

// ------------------------------------------------------------------- search
async function runSearch(reset: boolean): Promise<boolean> {
  if (loading) return false;
  if (reset) {
    currentPage = 1;
    accumulated = [];
    resultsEl.replaceChildren(renderSkeletons(4));
    resultMetaEl.replaceChildren();
    loadMoreWrap.replaceChildren();
  }
  loading = true;
  try {
    const resp = await search({
      q: currentQuery,
      sources: [...selectedSources],
      sort,
      page: currentPage,
      pageSize: PAGE_SIZE,
    });
    totalResults = resp.total;
    accumulated = reset ? resp.results : accumulated.concat(resp.results);
    resultMetaEl.replaceChildren(renderResultMeta(resp));
    if (resp.quota_remaining !== null && resp.quota_remaining !== undefined) {
      setStatus(`잔여 호출 ${resp.quota_remaining.toLocaleString()}`, "", false);
    }
    renderResults();
    return true;
  } catch (err) {
    const message =
      err instanceof ApiError && err.status === 503
        ? "검색 소스가 설정되지 않았습니다."
        : err instanceof ApiError && err.status === 429
          ? "오늘 호출 한도를 초과했습니다."
          : "검색 중 문제가 발생했습니다.";
    const detail = err instanceof Error ? err.message : String(err);
    resultsEl.replaceChildren(renderState("error", message, detail));
    resultMetaEl.replaceChildren();
    loadMoreWrap.replaceChildren();
    return false;
  } finally {
    loading = false;
  }
}

function renderResults(): void {
  resultsEl.replaceChildren();
  if (accumulated.length === 0) {
    resultsEl.append(
      renderState("empty", "검색 결과가 없습니다.", "다른 키워드나 소스 필터를 시도해 보세요."),
    );
    loadMoreWrap.replaceChildren();
    return;
  }
  for (const item of accumulated) {
    resultsEl.append(
      renderCard(item, {
        bookmarked: isBookmarked(item.url),
        onToggleBookmark: handleToggleBookmark,
      }),
    );
  }
  renderLoadMore();
}

function renderLoadMore(): void {
  loadMoreWrap.replaceChildren();
  if (accumulated.length >= totalResults) return;
  const btn = el("button", {
    class: "btn-secondary load-more",
    type: "button",
    text: `더 보기 (${accumulated.length} / ${totalResults})`,
  }) as HTMLButtonElement;
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    btn.textContent = "불러오는 중…";
    currentPage += 1;
    const ok = await runSearch(false);
    if (!ok) currentPage -= 1; // 실패 시 페이지 인덱스 되돌림
  });
  loadMoreWrap.append(btn);
}

// ---------------------------------------------------------------- bookmarks
function handleToggleBookmark(item: ResultItem, btn: HTMLButtonElement): void {
  const added = toggleBookmark(item);
  btn.setAttribute("aria-pressed", String(added));
  btn.textContent = added ? "★" : "☆";
  btn.title = added ? "북마크 해제" : "북마크 추가";
  btn.setAttribute("aria-label", btn.title);
  updateBookmarkCount();
  if (!viewBookmarks.hidden) renderBookmarks();
}

function updateBookmarkCount(): void {
  bmCountEl.textContent = String(loadBookmarks().length);
}

function renderBookmarks(): void {
  const list = loadBookmarks();
  bookmarksEl.replaceChildren();
  if (list.length === 0) {
    bookmarksEl.append(
      renderState("initial", "저장한 북마크가 없습니다.", "결과 카드의 ☆ 를 눌러 후기를 보관하세요."),
    );
    return;
  }
  for (const item of list) {
    bookmarksEl.append(
      renderCard(item, { bookmarked: true, onToggleBookmark: handleToggleBookmark }),
    );
  }
}

// ------------------------------------------------------------------- status
function setStatus(text: string, detail: string, warn: boolean): void {
  statusChip.textContent = text;
  statusChip.title = detail;
  statusChip.classList.toggle("warn", warn);
  statusChip.hidden = !text;
}

// --------------------------------------------------------------------- tabs
function switchTab(tab: string): void {
  for (const btn of tabsEl.querySelectorAll<HTMLButtonElement>(".tab")) {
    btn.classList.toggle("is-active", btn.dataset.tab === tab);
    btn.setAttribute("aria-selected", String(btn.dataset.tab === tab));
  }
  viewResults.hidden = tab !== "results";
  viewBookmarks.hidden = tab !== "bookmarks";
  if (tab === "bookmarks") renderBookmarks();
}

// --------------------------------------------------------------------- init
async function loadMeta(): Promise<void> {
  try {
    const meta = await fetchMeta();
    if (meta.categories?.length) {
      categories = meta.categories;
      // 사라진 카테고리 정리
      selectedSources = new Set([...selectedSources].filter((s) => categories.some((c) => c.key === s)));
      if (selectedSources.size === 0) selectedSources = new Set(DEFAULT_SOURCES);
      buildSourceChips();
    }
    if (meta.demo_mode) {
      setStatus("데모 데이터", "API 키 없이 샘플 데이터로 동작 중입니다.", true);
    } else if (!meta.naver_configured) {
      setStatus("키 미설정", "백엔드 .env에 NAVER_CLIENT_ID/SECRET을 설정하세요.", true);
    }
  } catch {
    setStatus("백엔드 오프라인", "백엔드(/api)에 연결할 수 없습니다.", true);
  }
}

function init(): void {
  const prefs = loadPrefs();
  if (prefs.sources?.length) selectedSources = new Set(prefs.sources);
  if (prefs.sort === "date" || prefs.sort === "sim") sort = prefs.sort;

  const initialTheme =
    prefs.theme ??
    (window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(initialTheme);

  buildSourceChips();
  buildSortToggle();
  updateBookmarkCount();
  resultsEl.replaceChildren(
    renderState("initial", "합격후기를 검색해 보세요.", "예) 국회직 8급 면접 후기 · 국회사무처 8급 합격수기"),
  );

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    currentQuery = q;
    void runSearch(true);
  });

  themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(next);
    savePrefs();
  });

  tabsEl.addEventListener("click", (e) => {
    const target = (e.target as HTMLElement).closest<HTMLButtonElement>(".tab");
    if (target?.dataset.tab) switchTab(target.dataset.tab);
  });

  void loadMeta();
  input.focus();
}

// PWA: 프로덕션 빌드에서만 서비스워커 등록 (dev HMR과 충돌 방지)
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* SW 등록 실패는 무시 */
    });
  });
}

init();
