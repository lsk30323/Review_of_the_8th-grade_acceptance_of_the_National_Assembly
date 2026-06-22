"""보조 소스 어댑터 (2차, 선택).

v1 기본은 네이버 단독이다. 결과 폭이 부족할 때 키를 설정하면 아래 어댑터가
자동 활성화되어 오케스트레이터에 plug-in 된다. 키가 없으면 enabled=False로
우아하게 비활성화(빈 리스트 반환)된다.

- SerperAdapter      : 옵션 b) 서드파티 SERP API (serper.dev)
- GoogleCSEAdapter   : 옵션 a) 레거시 Google Custom Search (2027-01-01 종료, 신규 발급 불가)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import httpx

from ..core.text import strip_html
from .base import NormalizedResult, SourceAdapter

log = logging.getLogger(__name__)

# Serper의 date 필드는 형식이 보장되지 않는다(예: "2025-01-01", "Jan 1, 2025").
# 랭킹의 recency 계산은 ISO(YYYY-MM-DD)를 기대하므로 정규화하고, 파싱 실패 시 None.
_SERPER_DATE_FORMATS = ("%Y-%m-%d", "%b %d, %Y", "%d %b %Y", "%Y.%m.%d", "%Y/%m/%d")


def _to_iso_date(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in _SERPER_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


class SerperAdapter(SourceAdapter):
    name = "serper"
    is_secondary = True
    ENDPOINT = "https://google.serper.dev/search"

    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 8.0,
    ) -> None:
        self._api_key = api_key
        self._client = client
        self._timeout = timeout
        self.enabled = bool(api_key)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        sort: str = "sim",
        categories: Optional[list[str]] = None,
    ) -> list[NormalizedResult]:
        if not self.enabled:
            return []
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(
                self.ENDPOINT,
                headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                json={"q": query, "gl": "kr", "hl": "ko", "num": max(1, min(10, limit))},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            log.warning("Serper 호출 실패: %r", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()

        out: list[NormalizedResult] = []
        for item in data.get("organic", []):
            link = item.get("link", "")
            title = strip_html(item.get("title", ""))
            if not link or not title:
                continue
            out.append(
                NormalizedResult(
                    title=title,
                    url=link,
                    snippet=strip_html(item.get("snippet", "")),
                    source="serper",
                    source_label="구글(Serper)",
                    posted_at=_to_iso_date(item.get("date")),
                    matched_query=query,
                    extra={"position": item.get("position")},
                )
            )
        return out


class GoogleCSEAdapter(SourceAdapter):
    name = "google_cse"
    is_secondary = True
    ENDPOINT = "https://www.googleapis.com/customsearch/v1"

    def __init__(
        self,
        api_key: str,
        cx: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 8.0,
    ) -> None:
        self._api_key = api_key
        self._cx = cx
        self._client = client
        self._timeout = timeout
        self.enabled = bool(api_key and cx)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        sort: str = "sim",
        categories: Optional[list[str]] = None,
    ) -> list[NormalizedResult]:
        if not self.enabled:
            return []
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.get(
                self.ENDPOINT,
                params={
                    "key": self._api_key,
                    "cx": self._cx,
                    "q": query,
                    "num": max(1, min(10, limit)),
                    "hl": "ko",
                    "gl": "kr",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            log.warning("Google CSE 호출 실패: %r", exc)
            return []
        finally:
            if owns_client:
                await client.aclose()

        out: list[NormalizedResult] = []
        for item in data.get("items", []):
            link = item.get("link", "")
            title = strip_html(item.get("title", ""))
            if not link or not title:
                continue
            out.append(
                NormalizedResult(
                    title=title,
                    url=link,
                    snippet=strip_html(item.get("snippet", "")),
                    source="google_cse",
                    source_label="구글(CSE)",
                    posted_at=None,
                    matched_query=query,
                )
            )
        return out
