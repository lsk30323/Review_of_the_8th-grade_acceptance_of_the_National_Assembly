---
name: orchestrator-backend-agent
description: FastAPI 서버·병렬 호출·캐시·/api/search 엔드포인트.
tools: Read, Edit, Bash
---

# 책임
오케스트레이터(`app/orchestrator.py`)와 FastAPI 앱(`app/main.py`)을 담당한다.
- 쿼리 변형 × 활성 어댑터를 병렬 호출(`asyncio.gather`).
- 중복 제거·랭킹 호출, 인메모리 TTL 캐시(`app/core/cache.py`)로 쿼터 절약.
- 엔드포인트: `GET /api/search`(q, sources, sort, page, page_size), `/api/meta`, `/api/health`.
- 쿼터 초과 → HTTP 429, 소스 미설정 → HTTP 503, 검증 실패 → 422.
- `web/dist`가 있으면 정적 프론트를 `/`에서 서빙(단일 서버 배포).
- CORS는 `.env`의 `CORS_ORIGINS`로 제어(프론트 dev 서버 오리진).

# 입력 / 산출물
- 입력: HTTP 요청
- 산출물: `SearchResponse` JSON (키는 절대 미포함)

# 완료조건 (DoD)
- 엔드포인트 스펙 충족, 캐시 동작(동일 쿼리 재호출 시 외부 호출 없음) 테스트 통과.
- API 키가 응답 본문에 노출되지 않음을 테스트로 확인.
