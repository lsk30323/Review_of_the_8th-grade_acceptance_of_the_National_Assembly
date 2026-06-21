# HANDOFF.md

페이즈 종료 시 3~7줄로 기록한다: 무엇을 만들었는지 / 다음 에이전트가 알아야 할
인터페이스·경로·주의점 / 미해결 이슈.

---

## P0 스캐폴딩 + P1~P5 (초기 일괄 구축)
- **만든 것**: FastAPI 백엔드(`app/`)와 Vite+Vanilla TS PWA(`web/`) 전체. 네이버 어댑터,
  쿼리 전략·랭킹·중복제거·캐시·쿼터, `/api/search`·`/api/meta`·`/api/health` 엔드포인트,
  반응형 PWA UI(검색/필터/정렬/북마크/오프라인 캐시), 데모 모드, Docker.
- **공통 인터페이스**: `app/adapters/base.py`
  - `NormalizedResult(title, url, snippet, source, source_label, posted_at, score, matched_query, extra)`
  - `SourceAdapter.search(query, *, limit, sort, categories) -> list[NormalizedResult]`
- **소스 키**: `naver_blog` / `naver_cafe` / `naver_web` / `naver_news` / `serper` / `google_cse` / `demo`.
- **카테고리 키**(네이버/데모): `blog` / `cafe` / `web` / `news`. API `sources` 파라미터는 쉼표 구분.
- **오케스트레이터**: `app/orchestrator.py`의 `SearchOrchestrator`. 활성 어댑터만 사용하며
  쿼리 변형 × 어댑터를 병렬 호출 → 중복제거 → 랭킹 → 캐시 → 페이지네이션.
- **API 응답 모델**: `app/main.py`의 `SearchResponse`(`results[]`, `variants`, `total`, `cached`,
  `quota_remaining` 등). 프론트 타입은 `web/src/types.ts`와 1:1로 맞춰져 있음.
- **프론트 진입점**: `web/src/main.ts`. 빌드 산출물 `web/dist`가 있으면 FastAPI가 `/`에서 직접 서빙.
- **주의점**:
  - 키는 백엔드 `.env`에만. 응답·프론트·깃에 노출 금지.
  - `QuotaGuard`는 카테고리 수만큼 호출 직전 예약. 한도 초과 시 `QuotaExceededError`→HTTP 429.
  - 캐시 TTL=0이면 캐시 비활성(테스트에서 사용).
  - 외부 호출 테스트는 `respx`로 모킹 — 실제 쿼터 0 소모.
- **테스트**: `pytest`(51개) 전부 통과. `app/tests/`.
- **미해결/향후**:
  - 보조 소스(SERPER/GOOGLE_CSE) 어댑터는 구현되어 있으나 v1 기본 비활성(키 설정 시 자동 활성).
  - 캐시 SQLite 영속화는 `Cache` 프로토콜만 충족하면 교체 가능(미구현).
  - PWA 서비스워커는 프로덕션 빌드에서만 등록(dev HMR 충돌 방지).
