import httpx
import pytest
import respx

from app.adapters.naver import NaverSearchAdapter
from app.core.quota import QuotaExceededError, QuotaGuard

BLOG_JSON = {
    "items": [
        {
            "title": "국회직 8급 <b>합격후기</b>",
            "link": "https://blog.naver.com/u/1",
            "description": "<b>국회직</b> 8급 합격수기 &amp; 공부법",
            "postdate": "20250101",
        }
    ]
}
NEWS_JSON = {
    "items": [
        {
            "title": "국회사무처 8급 채용 발표",
            "link": "https://news.x.com/a",
            "description": "국회직 8급 합격자 발표",
            "pubDate": "Mon, 03 Mar 2025 09:00:00 +0900",
        }
    ]
}


async def test_disabled_when_no_credentials():
    a = NaverSearchAdapter("", "", quota=QuotaGuard(10))
    assert a.enabled is False
    assert await a.search("국회직 8급") == []


async def test_blog_strip_normalize_and_auth_header():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get("https://openapi.naver.com/v1/search/blog.json").mock(
            return_value=httpx.Response(200, json=BLOG_JSON)
        )
        adapter = NaverSearchAdapter("myid", "mysecret", quota=QuotaGuard(100), display=10)
        results = await adapter.search("국회직 8급", categories=["blog"])

    assert len(results) == 1
    r = results[0]
    assert r.title == "국회직 8급 합격후기"          # 태그 제거
    assert "합격수기 & 공부법" in r.snippet           # 엔티티 디코드
    assert r.posted_at == "2025-01-01"               # postdate 정규화
    assert r.source == "naver_blog"
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["X-Naver-Client-Id"] == "myid"
    assert sent.headers["X-Naver-Client-Secret"] == "mysecret"


async def test_news_pubdate_parsed():
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://openapi.naver.com/v1/search/news.json").mock(
            return_value=httpx.Response(200, json=NEWS_JSON)
        )
        adapter = NaverSearchAdapter("id", "sec", quota=QuotaGuard(100))
        results = await adapter.search("국회직 8급", categories=["news"])
    assert results[0].posted_at == "2025-03-03"
    assert results[0].source == "naver_news"


async def test_quota_guard_blocks_before_http_call():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get("https://openapi.naver.com/v1/search/blog.json").mock(
            return_value=httpx.Response(200, json=BLOG_JSON)
        )
        adapter = NaverSearchAdapter("id", "sec", quota=QuotaGuard(0))
        with pytest.raises(QuotaExceededError):
            await adapter.search("국회직 8급", categories=["blog"])
        assert route.called is False  # 호출 전에 차단


async def test_multiple_categories_reserve_quota():
    quota = QuotaGuard(100)
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://openapi.naver.com/v1/search/blog.json").mock(
            return_value=httpx.Response(200, json=BLOG_JSON)
        )
        mock.get("https://openapi.naver.com/v1/search/cafearticle.json").mock(
            return_value=httpx.Response(200, json=BLOG_JSON)
        )
        adapter = NaverSearchAdapter("id", "sec", quota=quota)
        await adapter.search("국회직 8급", categories=["blog", "cafe"])
    assert quota.used == 2  # 카테고리 수만큼 예약
