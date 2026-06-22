"""URL 정규화 기반 중복 제거.

트래킹 파라미터 제거 · http→https · www 제거 · trailing slash/fragment 정리 후
정규화 URL을 키로 병합한다. 동일 글이 여러 소스에서 오면 최고 점수를 유지한다.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ..adapters.base import NormalizedResult

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "igshid", "ref", "referrer", "spm", "trk", "from",
    "source", "src",
}


def normalize_url(url: str) -> str:
    """중복 판정용 정규화 URL을 만든다."""
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        return url.strip()

    scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path.rstrip("/") or "/"
    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in TRACKING_PARAMS
    ]
    kept.sort()
    query = urlencode(kept)
    return urlunsplit((scheme, netloc, path, query, ""))


def dedupe_results(results: list[NormalizedResult]) -> list[NormalizedResult]:
    """정규화 URL로 병합. 더 높은 점수를 유지하고 출처를 merged_sources로 기록한다."""
    best: dict[str, NormalizedResult] = {}
    order: list[str] = []
    for r in results:
        key = normalize_url(r.url) or r.url or r.title
        existing = best.get(key)
        if existing is None:
            best[key] = r
            order.append(key)
            continue
        keep, drop = (r, existing) if r.score > existing.score else (existing, r)
        merged = set(keep.extra.get("merged_sources", []))
        merged.update(drop.extra.get("merged_sources", []))
        merged.update({keep.source, drop.source})
        keep.extra["merged_sources"] = sorted(merged)
        best[key] = keep
    return [best[k] for k in order]
