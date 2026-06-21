import type { ResultItem, SearchResponse } from "./types";

type Attrs = Record<string, string | number | boolean | undefined>;

/** XSS 안전한 엘리먼트 생성 헬퍼 (텍스트는 textContent로만 주입). */
export function el(
  tag: string,
  attrs: Attrs = {},
  children: (Node | string)[] = [],
): HTMLElement {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === false) continue;
    if (k === "text") {
      node.textContent = String(v);
    } else if (k === "class") {
      node.className = String(v);
    } else {
      node.setAttribute(k, String(v));
    }
  }
  for (const c of children) {
    node.append(typeof c === "string" ? document.createTextNode(c) : c);
  }
  return node;
}

/** source 키 → 배지 종류(색상) 매핑. */
export function sourceKind(source: string): string {
  if (source.includes("blog")) return "blog";
  if (source.includes("cafe")) return "cafe";
  if (source.includes("news")) return "news";
  if (source.includes("web")) return "web";
  if (source === "serper" || source === "google_cse") return "google";
  return "demo";
}

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return iso.replaceAll("-", ".");
}

export interface CardOptions {
  bookmarked: boolean;
  onToggleBookmark: (item: ResultItem, btn: HTMLButtonElement) => void;
}

export function renderCard(item: ResultItem, opts: CardOptions): HTMLElement {
  const kind = sourceKind(item.source);

  const badge = el("span", { class: `badge badge-${kind}`, text: item.source_label });

  const bmBtn = el("button", {
    class: "bm-btn",
    type: "button",
    "aria-pressed": opts.bookmarked,
    "aria-label": opts.bookmarked ? "북마크 해제" : "북마크 추가",
    title: opts.bookmarked ? "북마크 해제" : "북마크 추가",
    text: opts.bookmarked ? "★" : "☆",
  }) as HTMLButtonElement;
  bmBtn.addEventListener("click", () => opts.onToggleBookmark(item, bmBtn));

  const headChildren: Node[] = [badge];
  const dateStr = formatDate(item.posted_at);
  if (dateStr) headChildren.push(el("time", { class: "card-date", datetime: item.posted_at ?? "", text: dateStr }));
  headChildren.push(el("span", { class: "spacer" }));
  headChildren.push(bmBtn);
  const head = el("div", { class: "card-head" }, headChildren);

  const titleLink = el("a", {
    href: item.url,
    target: "_blank",
    rel: "noopener noreferrer",
    text: item.title,
  });
  const title = el("h3", { class: "card-title" }, [titleLink]);

  const snippet = el("p", { class: "card-snippet", text: item.snippet || "(요약 없음)" });

  const score = el("span", {
    class: "score-pill",
    title: "관련성 점수(가중합)",
    text: `관련성 ${item.score.toFixed(1)}`,
  });
  const link = el("a", {
    class: "card-link",
    href: item.url,
    target: "_blank",
    rel: "noopener noreferrer",
    text: "원문 보기 ↗",
  });
  const foot = el("div", { class: "card-foot" }, [score, link]);

  return el("article", { class: "card", "data-source": kind }, [head, title, snippet, foot]);
}

export function renderSkeletons(n = 4): DocumentFragment {
  const frag = document.createDocumentFragment();
  for (let i = 0; i < n; i++) {
    frag.append(
      el("div", { class: "card skeleton" }, [
        el("div", { class: "sk-line sk-badge" }),
        el("div", { class: "sk-line sk-title" }),
        el("div", { class: "sk-line" }),
        el("div", { class: "sk-line sk-short" }),
      ]),
    );
  }
  return frag;
}

export function renderState(
  kind: "initial" | "empty" | "error",
  message: string,
  detail?: string,
): HTMLElement {
  const icon = kind === "error" ? "⚠️" : kind === "empty" ? "🔍" : "🗂️";
  const children: Node[] = [
    el("div", { class: "state-icon", text: icon }),
    el("p", { class: "state-title", text: message }),
  ];
  if (detail) children.push(el("p", { class: "state-detail", text: detail }));
  return el("div", { class: `state state-${kind}` }, children);
}

export function renderResultMeta(resp: SearchResponse): HTMLElement {
  const sortLabel = resp.sort === "date" ? "최신순" : "관련성순";
  const parts = [`총 ${resp.total.toLocaleString()}건`, sortLabel];
  if (resp.cached) parts.push("캐시");
  const summary = el("span", { class: "meta-summary", text: parts.join(" · ") });
  const variants = el("span", {
    class: "meta-variants",
    title: "실제 질의한 검색 변형",
    text: `질의: ${resp.variants.join(" / ")}`,
  });
  return el("div", { class: "result-meta-inner" }, [summary, variants]);
}
