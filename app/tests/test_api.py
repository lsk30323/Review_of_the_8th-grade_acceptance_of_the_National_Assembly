import httpx
import respx
from fastapi.testclient import TestClient

from app.config import get_settings

NAVER_ITEMS = {
    "items": [
        {
            "title": "국회직 8급 <b>합격후기</b>",
            "link": "https://blog.naver.com/u/1",
            "description": "국회직 8급 합격수기 공부법",
            "postdate": "20250301",
        }
    ]
}

SECRET = "super-secret-value-xyz"


def _register_naver(mock):
    for cat in ("blog", "cafearticle", "webkr", "news"):
        mock.get(f"https://openapi.naver.com/v1/search/{cat}.json").mock(
            return_value=httpx.Response(200, json=NAVER_ITEMS)
        )


def _fresh_app(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from app.main import app
    return app


def test_search_endpoint_with_naver(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="client-id-123",
        NAVER_CLIENT_SECRET=SECRET,
        DEMO_MODE="0",
        SEARCH_CACHE_TTL="0",
    )
    with respx.mock(assert_all_called=False) as mock:
        _register_naver(mock)
        with TestClient(app) as client:
            r = client.get("/api/search", params={"q": "국회직 8급", "sources": "blog,cafe", "sort": "sim"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["results"][0]["title"] == "국회직 8급 합격후기"
    assert data["results"][0]["source"] in ("naver_blog", "naver_cafe")
    # 키가 응답에 노출되지 않아야 한다
    assert SECRET not in r.text


def test_health_endpoint(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="id",
        NAVER_CLIENT_SECRET="sec",
        DEMO_MODE="0",
    )
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["naver_configured"] is True
    assert "naver" in body["active_adapters"]


def test_meta_exposes_secondary_when_configured(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="id",
        NAVER_CLIENT_SECRET="sec",
        SERPER_API_KEY="serper-key",
        DEMO_MODE="0",
    )
    with TestClient(app) as client:
        r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["secondary_available"] is True
    assert any(c["key"] == "google" for c in body["categories"])
    assert "serper" in body["active_adapters"]


def test_search_includes_secondary_when_google_selected(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="id",
        NAVER_CLIENT_SECRET="sec",
        SERPER_API_KEY="serper-key",
        DEMO_MODE="0",
        SEARCH_CACHE_TTL="0",
    )
    serper_payload = {
        "organic": [
            {
                "title": "국회직 8급 합격후기 모음",
                "link": "https://tistory.com/x/9",
                "snippet": "국회직 8급 합격 공부법 정리",
                "date": "2025-04-01",
                "position": 1,
            }
        ]
    }
    with respx.mock(assert_all_called=False) as mock:
        _register_naver(mock)
        mock.post("https://google.serper.dev/search").mock(
            return_value=httpx.Response(200, json=serper_payload)
        )
        with TestClient(app) as client:
            r = client.get("/api/search", params={"q": "국회직 8급", "sources": "blog,google"})
    assert r.status_code == 200
    sources_seen = {item["source"] for item in r.json()["results"]}
    assert "serper" in sources_seen


def test_search_demo_mode_without_keys(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="",
        NAVER_CLIENT_SECRET="",
        SERPER_API_KEY="",
        GOOGLE_CSE_KEY="",
        GOOGLE_CSE_CX="",
        DEMO_MODE="1",
        SEARCH_CACHE_TTL="0",
    )
    with TestClient(app) as client:
        r = client.get("/api/search", params={"q": "국회직 8급"})
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_search_503_when_no_sources(monkeypatch):
    app = _fresh_app(
        monkeypatch,
        NAVER_CLIENT_ID="",
        NAVER_CLIENT_SECRET="",
        SERPER_API_KEY="",
        GOOGLE_CSE_KEY="",
        GOOGLE_CSE_CX="",
        DEMO_MODE="0",
    )
    with TestClient(app) as client:
        r = client.get("/api/search", params={"q": "국회직 8급"})
    assert r.status_code == 503


def test_search_validates_sort(monkeypatch):
    app = _fresh_app(monkeypatch, NAVER_CLIENT_ID="id", NAVER_CLIENT_SECRET="sec")
    with TestClient(app) as client:
        r = client.get("/api/search", params={"q": "국회직 8급", "sort": "bogus"})
    assert r.status_code == 422
