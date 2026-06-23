"""네이버 검색 API 어댑터 (1차 소스).

인증(X-Naver-Client-Id/Secret) · blog/cafearticle/webkr/news 호출 · 쿼터 가드 ·
HTML strip · postdate 정규화를 담당한다. 외부 호출은 httpx로 수행하므로 respx로
모킹해 쿼터 소모 없이 테스트할 수 있다.
"""
from __future__ import annotations

import asyncio
import logging
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx

from ..core.quota import QuotaGuard
from ..core.text import strip_html
from .base import NormalizedResult, SourceAdapter

log = logging.getLogger(__name__)

# 카테고리 -> (엔드포인트, source 키, 사람용 라벨)
CATEGORY_ENDPOINTS: dict[str, tuple[str, str, str]] = {
    "blog": ("https://openapi.naver.com/v1/search/blog.json", "naver_blog", "네이버 블로그"),
    "cafe": ("https://openapi.naver.com/v1/search/cafearticle.json", "naver_cafe", "네이버 카페"),
    "web": ("https://openapi.naver.com/v1/search/webkr.json", "naver_web", "네이버 웹문서"),
    "news": ("https://openapi.naver.com/v1/search/news.json", "naver_news", "네이버 뉴스"),
}
# 기본 카테고리는 공개 URL이 보장되는 블로그·웹문서만 사용한다.
# 카페(cafearticle)는 회원 전용 글이 많아 기본에서 제외(명시 요청 시에만 호출 가능).
DEFAULT_CATEGORIES = ["blog", "web"]


def _parse_naver_date(item: dict) -> Optional[str]:
    """블로그/카페 postdate(YYYYMMDD) 또는 뉴스 pubDate(RFC822) → ISO 날짜."""
    postdate = item.get("postdate")
    if postdate and len(postdate) == 8 and postdate.isdigit():
        return f"{postdate[0:4]}-{postdate[4:6]}-{postdate[6:8]}"
    pub = item.get("pubDate")
    if pub:
        try:
            return parsedate_to_datetime(pub).date().isoformat()
        except (TypeError, ValueError):
            return None
    return None


class NaverSearchAdapter(SourceAdapter):
    """네이버 검색 API 어댑터 (blog/cafe/web/news, 인증·쿼터·정규화)."""
    name = "naver"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        quota: QuotaGuard,
        display: int = 20,
        client: httpx.AsyncClient | None = None,
        timeout: float = 8.0,
    ) -> None:
        """Init."""
        self._client_id = client_id
        self._client_secret = client_secret
        self._quota = quota
        self._display = max(1, min(100, int(display)))
        self._client = client
        self._timeout = timeout
        self.enabled = bool(client_id and client_secret)

    def supported_categories(self) -> list[str]:
        """Supported categories."""
        return list(CATEGORY_ENDPOINTS.keys())

    @property
    def _headers(self) -> dict[str, str]:
        """Headers."""
        return {
            "X-Naver-Client-Id": self._client_id,
            "X-Naver-Client-Secret": self._client_secret,
        }

    async def search(
        self,
        query: str,
        *,
        limit: int = 20,
        sort: str = "sim",
        categories: Optional[list[str]] = None,
    ) -> list[NormalizedResult]:
        """선택한 카테고리를 병렬 검색해 정규화 결과를 반환한다."""
        if not self.enabled:
            return []
        cats = [c for c in (categories or DEFAULT_CATEGORIES) if c in CATEGORY_ENDPOINTS]
        if not cats:
            return []

        # 쿼터 가드: 호출 직전 카테고리 수만큼 한 번에 예약(초과 시 QuotaExceededError).
        self._quota.reserve(len(cats))

        display = min(self._display, max(1, limit))
        sort_param = "date" if sort == "date" else "sim"

        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            groups = await asyncio.gather(
                *(self._search_category(client, c, query, display, sort_param) for c in cats),
                return_exceptions=True,
            )
        finally:
            if owns_client:
                await client.aclose()

        results: list[NormalizedResult] = []
        for g in groups:
            if isinstance(g, Exception):
                log.warning("네이버 카테고리 호출 실패: %r", g)
                continue
            results.extend(g)
        return results

    async def _search_category(
        self,
        client: httpx.AsyncClient,
        category: str,
        query: str,
        display: int,
        sort_param: str,
    ) -> list[NormalizedResult]:
        """단일 카테고리를 호출해 항목을 정규화한다(HTML strip·날짜)."""
        endpoint, source_key, source_label = CATEGORY_ENDPOINTS[category]
        params = {"query": query, "display": display, "start": 1, "sort": sort_param}
        resp = await client.get(endpoint, params=params, headers=self._headers)
        resp.raise_for_status()
        data = resp.json()

        out: list[NormalizedResult] = []
        for item in data.get("items", []):
            title = strip_html(item.get("title", ""))
            link = item.get("link") or item.get("originallink") or ""
            snippet = strip_html(item.get("description", ""))
            if not title or not link:
                continue
            out.append(
                NormalizedResult(
                    title=title,
                    url=link,
                    snippet=snippet,
                    source=source_key,
                    source_label=source_label,
                    posted_at=_parse_naver_date(item),
                    matched_query=query,
                    extra={"category": category},
                )
            )
        return out
