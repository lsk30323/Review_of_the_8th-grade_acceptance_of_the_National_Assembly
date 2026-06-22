import httpx
import respx

from app.adapters.secondary import GoogleCSEAdapter, SerperAdapter


async def test_serper_disabled_without_key():
    """Serper disabled without key 동작을 검증한다."""
    a = SerperAdapter("")
    assert a.enabled is False
    assert await a.search("국회직 8급") == []


async def test_google_cse_disabled_without_config():
    """Google cse disabled without config 동작을 검증한다."""
    a = GoogleCSEAdapter("", "")
    assert a.enabled is False
    assert await a.search("국회직 8급") == []


async def test_serper_parses_organic():
    """Serper parses organic 동작을 검증한다."""
    payload = {
        "organic": [
            {
                "title": "국회직 8급 합격후기",
                "link": "https://blog.naver.com/x/1",
                "snippet": "국회직 8급 합격 공부법",
                "date": "2025-01-01",
                "position": 1,
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=payload)
        )
        adapter = SerperAdapter("serper-key")
        results = await adapter.search("국회직 8급 합격후기")
    assert len(results) == 1
    assert results[0].source == "serper"
    assert route.calls.last.request.headers["X-API-KEY"] == "serper-key"


async def test_google_cse_parses_items():
    """Google cse parses items 동작을 검증한다."""
    payload = {
        "items": [
            {
                "title": "국회직 8급 합격수기",
                "link": "https://tistory.com/1",
                "snippet": "국회직 8급 합격 후기",
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.googleapis.com/customsearch/v1").mock(
            return_value=httpx.Response(200, json=payload)
        )
        adapter = GoogleCSEAdapter("cse-key", "cx-id")
        results = await adapter.search("국회직 8급 합격수기")
    assert results[0].source == "google_cse"


async def test_google_cse_extracts_published_date():
    """Google cse extracts published date 동작을 검증한다."""
    payload = {
        "items": [
            {
                "title": "국회직 8급 합격후기",
                "link": "https://blog.naver.com/x/7",
                "snippet": "국회직 8급 합격 공부법",
                "pagemap": {
                    "metatags": [
                        {"article:published_time": "2025-03-12T09:00:00+09:00"}
                    ]
                },
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        mock.get("https://www.googleapis.com/customsearch/v1").mock(
            return_value=httpx.Response(200, json=payload)
        )
        adapter = GoogleCSEAdapter("cse-key", "cx-id")
        results = await adapter.search("국회직 8급 합격후기")
    assert results[0].posted_at == "2025-03-12"
