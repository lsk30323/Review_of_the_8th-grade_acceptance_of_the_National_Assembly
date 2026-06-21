"""데모 어댑터.

API 키가 없을 때(DEMO_MODE=1) UI와 /api/search 흐름을 키 없이 시연하기 위한
샘플 데이터 소스. 실제 검색 결과가 아니며 오프라인 개발/데모 전용이다.
"""
from __future__ import annotations

from typing import Optional

from .base import NormalizedResult, SourceAdapter

# (title, url, snippet, category, source_label, posted_at)
_FIXTURES: list[tuple[str, str, str, str, str, str]] = [
    (
        "국회직 8급 일반행정 최종합격 후기 (필기·면접 총정리)",
        "https://blog.naver.com/demo-user/223000000001",
        "2년 준비 끝에 국회직 8급 일반행정 최종합격했습니다. 과목별 공부법과 면접 후기를 정리했어요.",
        "blog", "네이버 블로그", "2025-03-12",
    ),
    (
        "국회사무처 8급 합격수기 — 헌법/경제학 공부 순서",
        "https://blog.naver.com/demo-user/223000000002",
        "국회사무처 8급 합격수기입니다. 헌법과 경제학을 어떤 순서로 공부했는지 공유합니다.",
        "blog", "네이버 블로그", "2024-11-02",
    ),
    (
        "[카페글] 국회직 8급 필기 합격 컷과 체감 난이도",
        "https://cafe.naver.com/gosipass/123456",
        "올해 국회직 8급 필기 합격 컷 정리와 과목별 체감 난이도 후기 모음입니다.",
        "cafe", "네이버 카페", "2025-05-20",
    ),
    (
        "국회 8급 공무원 면접 후기 — 질문 리스트와 복장",
        "https://cafe.naver.com/gosipass/123999",
        "국회 8급 공무원 면접 후기. 실제 받은 질문 리스트와 분위기, 복장 팁을 적어둡니다.",
        "cafe", "네이버 카페", "2024-12-15",
    ),
    (
        "국회직 8급 합격후기와 1년 스터디 플랜",
        "https://example-blog.tistory.com/42",
        "직장 병행으로 국회직 8급 합격후기. 1년 스터디 플랜과 인강 활용법을 정리했습니다.",
        "web", "네이버 웹문서", "2025-01-08",
    ),
    (
        "국회사무처 8급 최종합격 — 영어/국어 점수 관리",
        "https://blog.naver.com/demo-user/223000000003",
        "국회사무처 8급 최종합격 후기. 영어와 국어 점수를 안정적으로 관리한 방법.",
        "blog", "네이버 블로그", "2023-09-30",
    ),
    (
        "국회직 8급 합격 공부법 — 과목별 회독 전략",
        "https://blog.naver.com/demo-user/223000000004",
        "국회직 8급 합격 공부법. 과목별 회독 수와 오답노트 관리 전략을 공유합니다.",
        "web", "네이버 웹문서", "2024-06-18",
    ),
    (
        "국회직 8급 채용 일정 및 합격자 발표 안내",
        "https://news.example.com/article/9988",
        "국회사무처가 8급 공무원 채용 일정과 합격자 발표 일정을 안내했다.",
        "news", "네이버 뉴스", "2025-02-01",
    ),
]


class DemoAdapter(SourceAdapter):
    name = "demo"

    def __init__(self) -> None:
        self.enabled = True

    def supported_categories(self) -> list[str]:
        return ["blog", "cafe", "web", "news"]

    async def search(
        self,
        query: str,
        *,
        limit: int = 20,
        sort: str = "sim",
        categories: Optional[list[str]] = None,
    ) -> list[NormalizedResult]:
        cats = set(categories or ["blog", "cafe", "web"])
        out: list[NormalizedResult] = []
        for title, url, snippet, category, label, posted in _FIXTURES:
            if category not in cats:
                continue
            out.append(
                NormalizedResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="demo",
                    source_label=label,
                    posted_at=posted,
                    matched_query=query,
                    extra={"category": category, "demo": True},
                )
            )
        return out[:limit]
