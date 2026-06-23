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

## P5 보조 소스(SERP) 활성화
- **만든 것**: 보조 소스를 **opt-in 1급 소스**로 통합. `SourceAdapter.is_secondary` 플래그 추가,
  `serper`/`google_cse`는 `is_secondary=True`. 오케스트레이터는 `sources`에 `google`(별칭
  serper/google_cse)이 있을 때만 보조 소스를 호출(쿼터 절약). `/api/meta`는 보조 소스 활성 시
  `secondary_available=true`와 `google` 카테고리를 노출 → 프론트가 "구글" 칩을 자동 표시.
- **주의점**: 키 미설정 시 보조 소스 미등록 → 기존 네이버 단독 동작 그대로(기본 sources에 google 없음).
  캐시 키에 보조소스 포함여부가 반영됨.
- **테스트**: 56개 통과(보조소스 opt-in/skip, 구글 선택 시 호출, meta 노출 포함).
- **라이브 검증 보류 사유**: 원격 샌드박스의 네트워크 egress 허용목록이 `openapi.naver.com`·
  `google.serper.dev`를 차단(`host_not_allowed`) → 실 키 라이브 호출은 호스트 허용목록 추가 후 가능.

## P7 앱 래퍼 (데스크톱 Electron + Android Capacitor)
- **만든 것**:
  - `desktop/` — Electron 앱. `main.js`가 빈 포트를 잡아 FastAPI(uvicorn)를 자식 프로세스로
    띄우고 `/api/health` 확인 후 `http://127.0.0.1:<port>/` 로드. 외부 링크는 기본 브라우저로.
    백엔드 탐색 순서: `A8_BACKEND_CMD` → 번들 바이너리 → `.venv`/시스템 파이썬. electron-builder 설정 포함.
  - `web/capacitor.config.ts` + `web/package.json` 의존성/스크립트 — Capacitor Android 래퍼.
- **주의점**:
  - 데스크톱은 `web/dist` 빌드가 있어야 한다(백엔드가 정적 서빙). 키 없으면 데모 모드 자동.
  - 모바일 웹뷰는 `capacitor://localhost` 오리진 → 상대 `/api` 안 됨. **빌드 시 `VITE_API_BASE`로
    백엔드 절대 URL 주입** 필요. 백엔드 CORS 기본값에 capacitor/localhost 오리진 추가됨.
  - `main.ts`는 Capacitor 네이티브에서 서비스워커 등록을 건너뛴다.
  - 네이티브 프로젝트(`web/android`)·Electron 산출물(`desktop/dist`)은 `.gitignore` 처리.
- **빌드/실행**: `APP.md` 참고. 최종 바이너리(APK/설치파일)는 사용자 PC(Android Studio/electron-builder)에서.
- **검증 한계**: 이 샌드박스에선 Electron/Android SDK 바이너리 다운로드가 egress로 막혀 최종 빌드는 미실행.
  JS 문법(`node --check`)·설정 JSON·프론트 빌드·백엔드 테스트는 통과 확인.
  - 캐시 SQLite 영속화는 `Cache` 프로토콜만 충족하면 교체 가능(미구현).
  - PWA 서비스워커는 프로덕션 빌드에서만 등록(dev HMR 충돌 방지).

## P8 CI 자동 빌드 (GitHub Actions)
- **만든 것**: `.github/workflows/`에 두 워크플로 추가.
  - `build-desktop.yml` — OS 매트릭스(ubuntu/windows/macos)에서 `web` 빌드 후 electron-builder로
    AppImage/`.exe`(nsis)/`.dmg` 생성. 미서명(`CSC_IDENTITY_AUTO_DISCOVERY=false`), `--publish never`.
  - `build-android.yml` — JDK 17 + Android SDK에서 `web` 빌드 → `cap add/sync android` →
    `gradlew assembleDebug` 로 디버그 APK 생성.
- **트리거**: `workflow_dispatch`(수동) + `push` 태그 `v*`. 태그면 `softprops/action-gh-release@v2`로
  같은 태그 Release에 산출물 첨부. `permissions: contents: write` 필요.
- **주의점**:
  - Android `VITE_API_BASE`: 수동 입력 → 저장소 변수 `vars.VITE_API_BASE` → 빈 값 순. 빈 값이면 앱이
    백엔드를 못 찾음(디버그 산출물 용도). 영구 기본값은 저장소 Actions Variables에 등록.
  - 데스크톱 산출물은 Electron 셸 + `web/dist`까지만. 완전 자립형은 백엔드 PyInstaller 동봉 별도 필요.
  - 산출물 이름: `desktop-windows`/`desktop-macos`/`desktop-linux`/`android-debug-apk`.
- **검증 한계**: 워크플로 자체는 GitHub Actions에서 실행되며, 이 샌드박스에선 YAML 유효성만 확인.

## P9 공개 URL 정책 (게이트 소스 제외)
- **만든 것**: 검색 결과를 **회원 가입/로그인 없이 열람 가능한 공개 URL로 제한**.
  - 기본 카테고리에서 `cafe` 제거 → `blog`+`web`. (`naver.DEFAULT_CATEGORIES`, `orchestrator.default_categories`,
    `main.py` `/api/search` 기본값, `/api/meta` 칩, 프론트 `DEFAULT_SOURCES`/칩 모두 일치.)
  - `orchestrator.NAVER_CATEGORIES`에서 `cafe` 제외 → API `sources=cafe`는 무시(기본으로 폴백).
  - **도메인 필터**(`ranking.GATED_DOMAINS = ("cafe.naver.com",)` + `is_noise`): 어느 카테고리로
    들어오든(특히 webkr에 섞이는) `cafe.naver.com`/`m.cafe.naver.com` 링크를 제외. 이게 실질 차단 지점.
  - `ranking.TRUSTED_SOURCE_BONUS`에서 `naver_cafe` 가점 제거, `query_strategy.TRUSTED_SITES`에서
    `cafe.naver.com` 제거(보조 소스 site 제한 대상에서도 빠짐). 데모 픽스처의 카페 URL → 공개 URL로 교체.
- **주의점**: 네이버 어댑터의 `CATEGORY_ENDPOINTS`에는 `cafe`가 남아 있어(명시 호출 시 동작) 하위호환
  유지. 게이트 도메인을 늘리려면 `GATED_DOMAINS`에 추가만 하면 됨. 공개 카페까지 일괄 제외되는 한계는
  검색 API만으로 공개/비공개 판별이 불가하기 때문(자체 크롤 금지 원칙).
- **테스트**: `pytest` 60개 통과(게이트 도메인 `is_noise`/랭킹 제외 케이스 추가). 프론트 `tsc` 통과.

## P10 공개 카페 허용목록 (P9 일부 갱신)
- **만든 것**: P9에서 카페를 전면 제외했으나, **허용목록에 등록한 공개 카페 글은 통과**하도록 변경.
  검색 API만으로 공개/비공개 자동 판별이 불가하므로 명시적 allowlist 방식.
  - `is_noise(..., cafe_allowlist)` / `rank_results(..., cafe_allowlist)`: `cafe.naver.com` 링크는
    URL의 카페 slug(`cafe.naver.com/<slug>/...`)가 허용목록에 있을 때만 통과. 신형 `ca-fe/...`는
    slug 식별 불가 → 게이트 처리. webkr에 섞인 카페 링크도 동일 규칙.
  - 설정 `PUBLIC_CAFE_ALLOWLIST`(env, 쉼표 구분 slug) → `settings.public_cafe_allowlist_set`(frozenset).
    비면 P9와 동일(모든 카페 제외).
  - `SearchOrchestrator(cafe_allowlist=...)`: 허용목록 있으면 기본 카테고리에 `cafe` 추가·조회 허용,
    없으면 `_resolve_sources`가 `cafe` 제거(쿼터 절약). `NAVER_CATEGORIES`에 `cafe` 복원.
  - `/api/meta`는 허용목록 설정 시에만 "카페" 칩 노출. 프론트 `DEFAULT_SOURCES`에 `cafe` 포함
    (메타에 없으면 `loadMeta`가 자동 정리).
- **운영**: 카페 추가 = Render/.env의 `PUBLIC_CAFE_ALLOWLIST`에 slug 추가 후 재시작(코드 재빌드 불필요).
  slug = 카페 주소 `cafe.naver.com/<slug>`의 `<slug>`. 카페 단위 판별이라 개별 '멤버공개' 글은 예외.
- **테스트**: `pytest` 63개 통과(허용목록 is_noise·랭킹·오케스트레이터 케이스 추가). 프론트 `tsc` 통과.
