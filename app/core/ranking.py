"""관련성 스코어링 · 노이즈 필터 · 정렬 (지시서 7.2 / 7.3).

점수식은 설명 가능한 가중합으로 시작한다. 각 결과의 extra["score_breakdown"]에
세부 가점/감점을 기록한다.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlsplit

from ..adapters.base import NormalizedResult
from .dedupe import dedupe_results
from .query_strategy import has_core_signal, has_intent_signal

# 광고·모객성 노이즈 키워드
AD_KEYWORDS = [
    "수강", "수강료", "수강신청", "할인", "등록금", "프리패스", "환급",
    "이벤트", "쿠폰", "특강", "무료특강", "설명회", "상담문의", "0원", "수강혜택",
]
# 대표 학원/광고 도메인 일부 (부분일치)
AD_DOMAINS = [
    "eduwill", "hackers", "willbes", "megagong", "etoos", "pmg", "gongdori",
]
# 회원 가입/로그인 없이는 본문을 볼 수 없는 게이트(접근 제한) 도메인.
# 공개 URL만 노출하기 위해 제외한다. 네이버 카페 글 다수가 회원 전용이며,
# 웹문서(webkr) 검색에 섞여 들어오는 카페 링크도 여기서 함께 걸러진다.
GATED_DOMAINS = ("cafe.naver.com",)
# 신뢰 출처 가점
TRUSTED_SOURCE_BONUS = {
    "naver_blog": 0.6,
    "naver_web": 0.2,
    "naver_news": 0.3,
    "serper": 0.2,
    "google_cse": 0.2,
    "demo": 0.4,
}


def _is_gated(dom: str) -> bool:
    """게이트(회원 전용) 도메인인가. m.cafe.naver.com 등 서브도메인도 포함."""
    return any(dom == g or dom.endswith("." + g) for g in GATED_DOMAINS)


def _domain(url: str) -> str:
    """Domain."""
    try:
        return urlsplit(url).netloc.lower()
    except ValueError:
        return ""


def is_noise(r: NormalizedResult) -> bool:
    """노이즈(제외 대상) 여부. (지시서 7.2 −제외 규칙)"""
    text = f"{r.title} {r.snippet}"
    dom = _domain(r.url)
    # 회원 전용(게이트) 도메인은 공개 URL이 아니므로 제외한다.
    if _is_gated(dom):
        return True
    if any(d in dom for d in AD_DOMAINS):
        return True
    # 핵심어가 제목·본문 어디에도 없으면 제외
    if not has_core_signal(text):
        return True
    # 광고 키워드가 2개 이상이고 제목에 후기 의도 신호가 없으면 제외
    ad_hits = sum(1 for k in AD_KEYWORDS if k in text)
    if ad_hits >= 2 and not has_intent_signal(r.title):
        return True
    return False


def _recency_bonus(posted_at: str | None, today: date) -> float:
    """Recency bonus."""
    if not posted_at:
        return 0.0
    try:
        y, m, d = (int(x) for x in posted_at.split("-"))
        posted = date(y, m, d)
    except (ValueError, TypeError):
        return 0.0
    days = (today - posted).days
    if days < 0:
        return 0.0
    if days <= 365:
        return 1.0
    if days <= 365 * 3:
        return 0.5
    if days <= 365 * 5:
        return 0.2
    return 0.0


def score_result(r: NormalizedResult, *, today: date | None = None) -> float:
    """가중합 관련성 점수. (지시서 7.2 +가중 규칙)"""
    today = today or date.today()
    title = r.title
    snippet = r.snippet
    both = f"{title} {snippet}"
    score = 0.0
    breakdown: dict[str, float] = {}

    title_core = has_core_signal(title)
    title_intent = has_intent_signal(title)
    if title_core and title_intent:
        score += 2.0
        breakdown["title_core_and_intent"] = 2.0
    else:
        if title_core:
            score += 1.0
            breakdown["title_core"] = 1.0
        if title_intent:
            score += 0.8
            breakdown["title_intent"] = 0.8

    if has_core_signal(snippet):
        score += 0.4
        breakdown["snippet_core"] = 0.4
    if has_intent_signal(snippet):
        score += 0.3
        breakdown["snippet_intent"] = 0.3

    rb = _recency_bonus(r.posted_at, today)
    if rb:
        score += rb
        breakdown["recency"] = rb

    sb = TRUSTED_SOURCE_BONUS.get(r.source, 0.0)
    if sb:
        score += sb
        breakdown["source_trust"] = sb

    ad_hits = sum(1 for k in AD_KEYWORDS if k in both)
    if ad_hits:
        penalty = -0.5 * ad_hits
        score += penalty
        breakdown["ad_penalty"] = penalty

    r.extra["score_breakdown"] = {k: round(v, 3) for k, v in breakdown.items()}
    return score


def rank_results(
    results: list[NormalizedResult],
    *,
    sort: str = "sim",
    today: date | None = None,
    drop_noise: bool = True,
) -> list[NormalizedResult]:
    """노이즈 제거 → 점수 계산 → 중복 제거 → 정렬."""
    today = today or date.today()
    kept: list[NormalizedResult] = []
    for r in results:
        if drop_noise and is_noise(r):
            continue
        r.score = score_result(r, today=today)
        kept.append(r)

    deduped = dedupe_results(kept)

    if sort == "date":
        deduped.sort(key=lambda x: (x.posted_at or "", x.score), reverse=True)
    else:  # "sim" (관련성)
        deduped.sort(key=lambda x: (x.score, x.posted_at or ""), reverse=True)
    return deduped
