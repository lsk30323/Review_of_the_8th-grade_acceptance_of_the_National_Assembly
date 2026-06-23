"""FastAPI 앱 — /api/search 오케스트레이션 엔드포인트.

프론트엔드는 이 백엔드의 /api/* 만 호출한다. API 키를 쥐고 외부 API를 부르는
일은 백엔드가 전담한다(키는 절대 프론트/응답에 노출하지 않음).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .adapters.demo import DemoAdapter
from .adapters.naver import NaverSearchAdapter
from .adapters.secondary import GoogleCSEAdapter, SerperAdapter
from .config import get_settings
from .core.cache import TTLCache
from .core.quota import QuotaExceededError, QuotaGuard
from .orchestrator import SearchOrchestrator

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("assembly8")

# 프론트 빌드 산출물 경로 (web/dist). 존재하면 정적 서빙으로 단일 서버 배포 가능.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


# --------------------------------------------------------------------------- #
#  응답 모델
# --------------------------------------------------------------------------- #
class ResultItem(BaseModel):
    """검색 결과 한 건(제목·링크·스니펫·출처·점수)."""
    title: str
    url: str
    snippet: str
    source: str
    source_label: str
    posted_at: Optional[str] = None
    score: float
    matched_query: Optional[str] = None


class SearchResponse(BaseModel):
    """/api/search 응답(결과 목록 + 변형·총계·캐시·쿼터 메타)."""
    query: str
    variants: list[str]
    total: int
    page: int
    page_size: int
    sort: str
    categories: list[str]
    cached: bool
    quota_remaining: Optional[int] = None
    results: list[ResultItem]


class SourceInfo(BaseModel):
    """소스 칩 한 개(키 + 표시 라벨)."""
    key: str
    label: str


class MetaResponse(BaseModel):
    """/api/meta 응답(활성 소스·카테고리·쿼터 잔량 등)."""
    naver_configured: bool
    demo_mode: bool
    secondary_available: bool
    active_adapters: list[str]
    categories: list[SourceInfo]
    quota_remaining: Optional[int] = None


# --------------------------------------------------------------------------- #
#  앱 수명주기: 공유 httpx 클라이언트 · 쿼터 · 캐시 · 오케스트레이터 구성
# --------------------------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    """공유 httpx 클라이언트·쿼터·캐시·오케스트레이터를 구성/정리한다."""
    settings = get_settings()
    client = httpx.AsyncClient(timeout=8.0)
    quota = QuotaGuard(settings.naver_daily_quota_guard)
    cache = TTLCache(settings.search_cache_ttl)

    adapters: list = []
    if settings.naver_configured:
        adapters.append(
            NaverSearchAdapter(
                settings.naver_client_id,
                settings.naver_client_secret,
                quota=quota,
                display=settings.naver_display,
                client=client,
            )
        )
    if settings.serper_configured:
        adapters.append(SerperAdapter(settings.serper_api_key, client=client))
    if settings.google_cse_configured:
        adapters.append(GoogleCSEAdapter(settings.google_cse_key, settings.google_cse_cx, client=client))

    # 실 소스가 하나도 없고 데모 모드면 샘플 데이터로 동작
    if not adapters and settings.demo_mode:
        adapters.append(DemoAdapter())
        log.info("DEMO_MODE: 샘플 데이터 어댑터로 기동합니다.")

    orchestrator = SearchOrchestrator(
        adapters=adapters,
        cache=cache,
        quota=quota,
        max_variants=settings.max_query_variants,
        naver_display=settings.naver_display,
    )

    app.state.client = client
    app.state.quota = quota
    app.state.cache = cache
    app.state.orchestrator = orchestrator
    app.state.settings = settings
    log.info("활성 어댑터: %s", [a.name for a in orchestrator.adapters] or "(없음)")
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title="assembly8-review-finder",
    version="0.1.0",
    description="국회직 8급 공무원 합격후기 검색 엔진 (검색 API 오케스트레이션)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
#  API 라우트
# --------------------------------------------------------------------------- #
@app.get("/api/health")
async def health(request: Request) -> dict:
    """헬스체크: 상태·설정 여부·활성 어댑터·쿼터 잔량."""
    settings = request.app.state.settings
    orch: SearchOrchestrator = request.app.state.orchestrator
    return {
        "status": "ok",
        "naver_configured": settings.naver_configured,
        "demo_mode": settings.demo_mode,
        "active_adapters": [a.name for a in orch.adapters],
        "quota_remaining": request.app.state.quota.remaining,
    }


@app.get("/api/meta", response_model=MetaResponse)
async def meta(request: Request) -> MetaResponse:
    """프론트 초기화용 메타데이터(선택 가능한 소스 칩 등)를 반환한다."""
    settings = request.app.state.settings
    orch: SearchOrchestrator = request.app.state.orchestrator
    secondary_available = any(getattr(a, "is_secondary", False) for a in orch.adapters)
    # 공개 URL만 노출하는 정책 → 회원 전용 글이 많은 카페는 선택 칩에서 제외한다.
    categories = [
        SourceInfo(key="blog", label="블로그"),
        SourceInfo(key="web", label="웹문서"),
        SourceInfo(key="news", label="뉴스"),
    ]
    # 보조 소스(구글/SERP)가 활성일 때만 선택 가능한 칩으로 노출
    if secondary_available:
        categories.append(SourceInfo(key="google", label="구글"))
    return MetaResponse(
        naver_configured=settings.naver_configured,
        demo_mode=settings.demo_mode,
        secondary_available=secondary_available,
        active_adapters=[a.name for a in orch.adapters],
        categories=categories,
        quota_remaining=request.app.state.quota.remaining,
    )


@app.get("/api/search", response_model=SearchResponse)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="검색 키워드"),
    sources: str = Query(
        "blog,web",
        description="쉼표 구분: blog,web,news (+ google = 보조 SERP 소스, 키 설정 시). 카페는 회원 전용 글이 많아 제외.",
    ),
    sort: str = Query("sim", pattern="^(sim|date)$", description="sim(관련성) | date(최신순)"),
    page: int = Query(1, ge=1, le=50),
    page_size: int = Query(20, ge=1, le=50),
) -> SearchResponse:
    """합격후기 검색 엔드포인트(소스 미설정 503, 쿼터 초과 429)."""
    orch: SearchOrchestrator = request.app.state.orchestrator
    if not orch.adapters:
        raise HTTPException(
            status_code=503,
            detail="검색 소스가 설정되지 않았습니다. .env에 NAVER_CLIENT_ID/SECRET을 설정하거나 DEMO_MODE=1로 실행하세요.",
        )

    src_list = [s.strip().lower() for s in sources.split(",") if s.strip()]
    try:
        res = await orch.search(q, sources=src_list, sort=sort, page=page, page_size=page_size)
    except QuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    return SearchResponse(
        query=res.query,
        variants=res.variants,
        total=res.total,
        page=res.page,
        page_size=res.page_size,
        sort=res.sort,
        categories=res.categories,
        cached=res.from_cache,
        quota_remaining=res.quota_remaining,
        results=[
            ResultItem(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                source=r.source,
                source_label=r.source_label,
                posted_at=r.posted_at,
                score=round(r.score, 4),
                matched_query=r.matched_query,
            )
            for r in res.items
        ],
    )


# --------------------------------------------------------------------------- #
#  정적 프론트 서빙 (web/dist 존재 시) — 단일 서버 배포용
# --------------------------------------------------------------------------- #
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    async def root_placeholder() -> str:
        """프론트 빌드(web/dist)가 없을 때 안내 HTML을 반환한다."""
        return (
            "<!doctype html><html lang='ko'><meta charset='utf-8'>"
            "<title>assembly8-review-finder</title>"
            "<body style='font-family:system-ui;max-width:640px;margin:64px auto;padding:0 16px;line-height:1.6'>"
            "<h1>assembly8-review-finder</h1>"
            "<p>백엔드가 실행 중입니다. API 문서는 <a href='/docs'>/docs</a> 를 참고하세요.</p>"
            "<p>프론트엔드는 개발 모드(<code>cd web; npm run dev</code>)로 실행하거나, "
            "<code>npm run build</code> 후 <code>web/dist</code>가 생기면 이 서버가 직접 서빙합니다.</p>"
            "</body></html>"
        )
