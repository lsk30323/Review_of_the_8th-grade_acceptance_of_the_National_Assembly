import pytest

from app.adapters.base import NormalizedResult, SourceAdapter
from app.core.cache import TTLCache
from app.core.quota import QuotaExceededError
from app.orchestrator import SearchOrchestrator


class FakeAdapter(SourceAdapter):
    name = "fake"

    def __init__(self, factory):
        self._factory = factory
        self.enabled = True
        self.calls: list[str] = []

    async def search(self, query, *, limit=20, sort="sim", categories=None):
        self.calls.append(query)
        return self._factory(query)


class QuotaBlockedAdapter(SourceAdapter):
    name = "blocked"

    def __init__(self):
        self.enabled = True

    async def search(self, query, *, limit=20, sort="sim", categories=None):
        raise QuotaExceededError("blocked")


def _one_result(_query):
    return [
        NormalizedResult(
            title="국회직 8급 합격후기",
            url="https://blog.naver.com/u/1",
            snippet="국회직 8급 합격수기 공부법",
            source="naver_blog",
            source_label="네이버 블로그",
            posted_at="2025-03-01",
        )
    ]


async def test_dedupe_across_variants():
    fake = FakeAdapter(_one_result)
    orch = SearchOrchestrator(adapters=[fake], cache=TTLCache(0), max_variants=3)
    res = await orch.search("국회직 8급")
    assert res.total == 1                 # 여러 변형이 같은 URL → 1건으로 병합
    assert len(fake.calls) >= 2           # 변형마다 호출됨
    assert res.variants                   # 변형 리스트 노출


async def test_cache_prevents_refetch():
    fake = FakeAdapter(_one_result)
    orch = SearchOrchestrator(adapters=[fake], cache=TTLCache(100), max_variants=2)
    first = await orch.search("국회직 8급")
    assert first.from_cache is False
    n = len(fake.calls)
    second = await orch.search("국회직 8급")
    assert second.from_cache is True
    assert len(fake.calls) == n           # 캐시 히트 → 재호출 없음


async def test_disabled_adapters_ignored():
    fake = FakeAdapter(_one_result)
    fake.enabled = False
    orch = SearchOrchestrator(adapters=[fake], cache=TTLCache(0))
    assert orch.adapters == []


async def test_quota_exhaustion_propagates():
    orch = SearchOrchestrator(adapters=[QuotaBlockedAdapter()], cache=TTLCache(0), max_variants=1)
    with pytest.raises(QuotaExceededError):
        await orch.search("국회직 8급")


async def test_pagination():
    def many(_q):
        return [
            NormalizedResult(
                title=f"국회직 8급 합격후기 {i}",
                url=f"https://blog.naver.com/u/{i}",
                snippet="국회직 8급 합격 공부법",
                source="naver_blog",
                source_label="네이버 블로그",
                posted_at="2025-03-01",
            )
            for i in range(10)
        ]

    orch = SearchOrchestrator(adapters=[FakeAdapter(many)], cache=TTLCache(0), max_variants=1)
    page1 = await orch.search("국회직 8급", page=1, page_size=4)
    assert page1.total == 10
    assert len(page1.items) == 4
    page3 = await orch.search("국회직 8급", page=3, page_size=4)
    assert len(page3.items) == 2
