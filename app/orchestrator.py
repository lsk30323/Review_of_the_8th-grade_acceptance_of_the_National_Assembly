"""검색 오케스트레이터.

쿼리 변형 → 소스 어댑터 병렬 호출 → 중복 제거 · 관련성 랭킹 → 캐시 → 페이지네이션.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from .adapters.base import NormalizedResult, SourceAdapter
from .core.cache import Cache
from .core.quota import QuotaExceededError, QuotaGuard
from .core.query_strategy import build_query_variants
from .core.ranking import rank_results

log = logging.getLogger(__name__)

# 네이버/데모가 이해하는 카테고리
NAVER_CATEGORIES = ("blog", "cafe", "web", "news")
# 보조 소스(구글/SERP)를 가리키는 UI source 키 (별칭 포함)
SECONDARY_SOURCE_KEYS = {"google", "serper", "google_cse"}


@dataclass(slots=True)
class SearchResult:
    query: str
    variants: list[str]
    total: int
    page: int
    page_size: int
    sort: str
    categories: list[str]
    from_cache: bool
    quota_remaining: int | None
    items: list[NormalizedResult] = field(default_factory=list)


class SearchOrchestrator:
    def __init__(
        self,
        *,
        adapters: list[SourceAdapter],
        cache: Cache,
        quota: QuotaGuard | None = None,
        max_variants: int = 4,
        default_categories: tuple[str, ...] = ("blog", "cafe", "web"),
        naver_display: int = 20,
    ) -> None:
        self.adapters = [a for a in adapters if getattr(a, "enabled", False)]
        self.cache = cache
        self.quota = quota
        self.max_variants = max_variants
        self.default_categories = list(default_categories)
        self.naver_display = naver_display

    def _resolve_sources(self, sources: list[str] | None) -> tuple[list[str], bool]:
        """요청 sources → (네이버 카테고리, 보조소스 포함여부).

        - sources 미지정: 기본 카테고리, 보조소스 미포함(v1 네이버 단독 기본).
        - "google"(또는 serper/google_cse) 포함 시에만 보조소스를 호출(쿼터 절약).
        """
        if not sources:
            return list(self.default_categories), False
        categories = [s for s in sources if s in NAVER_CATEGORIES]
        include_secondary = any(s in SECONDARY_SOURCE_KEYS for s in sources)
        if not categories and not include_secondary:
            categories = list(self.default_categories)
        return categories, include_secondary

    @staticmethod
    def _cache_key(query: str, categories: list[str], include_secondary: bool, sort: str) -> str:
        sec = "g" if include_secondary else "-"
        return f"{query.strip().lower()}|{','.join(sorted(categories))}|{sec}|{sort}"

    async def search(
        self,
        q: str,
        *,
        sources: list[str] | None = None,
        sort: str = "sim",
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResult:
        categories, include_secondary = self._resolve_sources(sources)
        variants = build_query_variants(q, max_variants=self.max_variants)
        key = self._cache_key(q, categories, include_secondary, sort)

        cached = self.cache.get(key)
        if cached is not None:
            ranked = cached
            from_cache = True
        else:
            from_cache = False
            ranked = await self._fetch_and_rank(variants, categories, include_secondary, sort)
            self.cache.set(key, ranked)

        total = len(ranked)
        start = (page - 1) * page_size
        items = ranked[start : start + page_size]
        reported = list(categories) + (["google"] if include_secondary else [])
        return SearchResult(
            query=q,
            variants=variants,
            total=total,
            page=page,
            page_size=page_size,
            sort=sort,
            categories=reported,
            from_cache=from_cache,
            quota_remaining=(self.quota.remaining if self.quota else None),
            items=items,
        )

    async def _fetch_and_rank(
        self,
        variants: list[str],
        categories: list[str],
        include_secondary: bool,
        sort: str,
    ) -> list[NormalizedResult]:
        tasks = []
        for adapter in self.adapters:
            if getattr(adapter, "is_secondary", False):
                if not include_secondary:
                    continue
                for variant in variants:
                    tasks.append(adapter.search(variant, limit=self.naver_display, sort=sort))
            else:
                if not categories:
                    continue
                for variant in variants:
                    tasks.append(
                        adapter.search(variant, limit=self.naver_display, sort=sort, categories=categories)
                    )
        groups = await asyncio.gather(*tasks, return_exceptions=True)

        raw: list[NormalizedResult] = []
        quota_hit = False
        for g in groups:
            if isinstance(g, QuotaExceededError):
                quota_hit = True
                continue
            if isinstance(g, Exception):
                log.warning("소스 호출 실패: %r", g)
                continue
            raw.extend(g)

        # 한 건도 못 모았는데 쿼터 때문이라면 상위로 전파(429 처리)
        if not raw and quota_hit:
            raise QuotaExceededError("일일 호출 한도를 초과해 검색을 수행할 수 없습니다.")

        return rank_results(raw, sort=sort)
