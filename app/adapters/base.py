"""정규화 결과 모델과 소스 어댑터 공통 인터페이스.

새 보조 소스(서드파티 SERP, 레거시 Google CSE 등)는 SourceAdapter를 구현하면
오케스트레이터에 plug-in 처럼 끼울 수 있다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class NormalizedResult:
    """모든 소스가 공통으로 반환하는 정규화된 검색 결과."""

    title: str
    url: str
    snippet: str
    source: str          # 머신용 키: naver_blog / naver_cafe / naver_web / naver_news / serper / google_cse / demo
    source_label: str    # 사람용 라벨: "네이버 블로그" 등
    posted_at: Optional[str] = None  # ISO 'YYYY-MM-DD' 또는 None
    score: float = 0.0
    matched_query: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "source_label": self.source_label,
            "posted_at": self.posted_at,
            "score": round(self.score, 4),
            "matched_query": self.matched_query,
            "extra": self.extra,
        }


class SourceAdapter(ABC):
    """검색 소스 어댑터 공통 인터페이스."""

    name: str = "base"
    enabled: bool = False

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        sort: str = "sim",
        categories: Optional[list[str]] = None,
    ) -> list[NormalizedResult]:
        """쿼리를 검색해 정규화 결과 리스트를 반환한다.

        - 비활성(enabled=False) 어댑터는 빈 리스트를 반환해 우아하게 비활성화된다.
        - categories는 네이버처럼 하위 카테고리가 있는 소스만 사용하고, 그 외는 무시한다.
        """
        raise NotImplementedError

    def supported_categories(self) -> list[str]:
        """이 어댑터가 이해하는 카테고리 목록(없으면 빈 리스트)."""
        return []
