"""쿼리 변형 전략 (지시서 7.1).

핵심어 x 의도어 조합으로 합격후기 글을 좁힌다. 사용자가 입력한 base 쿼리의
상태(핵심어/의도어 포함 여부)에 따라 보강 규칙을 다르게 적용한다.
"""
from __future__ import annotations

import re

# 핵심어 / 의도어 (표준 표기)
CORE_TERMS = ["국회직 8급", "국회사무처 8급", "국회 8급 공무원"]
INTENT_TERMS = ["합격후기", "합격수기", "최종합격", "합격 공부법", "면접 후기", "필기 합격"]

# 신호 판정용 토큰 (띄어쓰기 변형 흡수 위해 공백 제거 후 비교)
CORE_SIGNAL_TOKENS = ["국회직", "국회사무처", "국회8급"]
INTENT_SIGNAL_TOKENS = ["합격", "후기", "수기", "최종합격", "공부법", "면접", "필기"]

# 신뢰 출처 (site 제한용 — 보조 소스/구글 사용 시)
TRUSTED_SITES = ["blog.naver.com", "cafe.naver.com", "tistory.com"]

_WS_RE = re.compile(r"\s+")


def _norm(s: str | None) -> str:
    return _WS_RE.sub(" ", s or "").strip()


def _has_any(text: str, tokens: list[str]) -> bool:
    compact = (text or "").replace(" ", "")
    return any(tok.replace(" ", "") in compact for tok in tokens)


def has_core_signal(text: str) -> bool:
    return _has_any(text, CORE_SIGNAL_TOKENS)


def has_intent_signal(text: str) -> bool:
    return _has_any(text, INTENT_SIGNAL_TOKENS)


def build_query_variants(
    base_query: str,
    *,
    max_variants: int = 4,
    include_base: bool = True,
) -> list[str]:
    """base 쿼리로부터 검색 변형 세트를 만든다(최대 max_variants개)."""
    base = _norm(base_query)
    variants: list[str] = []

    def add(q: str) -> None:
        q = _norm(q)
        if q and q not in variants:
            variants.append(q)

    if include_base and base:
        add(base)

    if base:
        base_core = has_core_signal(base)
        base_intent = has_intent_signal(base)
        if base_core and not base_intent:
            # 핵심어만 → 의도어를 덧붙여 합격후기 글로 좁힌다
            for intent in ("합격후기", "합격수기", "최종합격"):
                add(f"{base} {intent}")
        elif not base_core:
            # 핵심어가 없으면 대표 핵심어를 보강한다
            add(f"국회직 8급 {base}")
            add(f"국회사무처 8급 {base}")

    # 표준 조합으로 폭 보강 (항상 후보로 둔다)
    for core in CORE_TERMS:
        add(f"{core} 합격후기")
    add("국회직 8급 합격수기")

    if not variants:
        add("국회직 8급 합격후기")

    return variants[:max_variants]


def with_site_restriction(query: str, site: str) -> str:
    return f"{_norm(query)} site:{site}"


def site_restricted_variants(query: str, sites: list[str] | None = None) -> list[str]:
    """보조 소스(구글/SERP)용 site 제한 변형."""
    sites = sites or TRUSTED_SITES
    return [with_site_restriction(query, s) for s in sites]
