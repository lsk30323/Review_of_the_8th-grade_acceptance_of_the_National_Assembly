# assembly8-review-finder

> 국회직 8급 공무원 **합격후기·합격수기**를 키워드 검색 한 번으로 한곳에 모아 보여주는 도구.
> 검색 API 오케스트레이션(전략 A) · 1차 소스 네이버 · 반응형 PWA + 경량 FastAPI 백엔드.

흩어진 합격후기는 정해진 출처(네이버 블로그·카페, 티스토리, 공시 커뮤니티 등)에 집중되어 있다.
이 도구는 일반 크롤러 대신 **검색 API를 오케스트레이션**해 해당 결과만 수집·정제·랭킹한다.
데스크톱과 모바일에서 동일하게 동작하도록 설치형 PWA(반응형)로 만들었다.

---

## ✨ 기능 (v1)

- 키워드 검색 → 다중 소스(네이버 blog/cafe/web/news) **병렬 질의**
- **쿼리 변형**(핵심어 × 의도어) 자동 생성 → 합격후기 글로 좁힘
- **중복 제거**(URL 정규화) + 설명 가능한 **관련성 랭킹**(가중합)
- 소스 필터 · 정렬(관련성/최신) · **더 보기** 페이지네이션
- 결과 **북마크**(로컬 저장) · 라이트/다크 테마
- **PWA**: 설치 가능, 오프라인 앱 셸 캐시, API 네트워크 우선·캐시 폴백
- **데모 모드**: API 키 없이 샘플 데이터로 즉시 시연

> 저작권: 후기 본문을 저장·재배포하지 않는다. **제목 + 짧은 스니펫 + 원문 링크**만 제공한다.

---

## 🏗 아키텍처

```text
[모바일/데스크톱 브라우저]  ──(PWA · 반응형)──▶  GET /api/search?q=...&sources=...&sort=...
                                                       │
                                          ┌────────────▼─────────────┐
                                          │  Orchestrator Backend     │  ← API 키 보관(서버 측)
                                          │  쿼리 변형 · 병렬 호출     │
                                          │  중복 제거 · 관련성 랭킹    │
                                          │  캐시(TTL) · 쿼터 가드      │
                                          └──────┬───────────┬────────┘
                                            네이버 검색 API   보조 소스(선택, 어댑터)
                                          (blog/cafe/web/news) (serper / google_cse)
```

- **보안 핵심**: 키는 백엔드 `.env`에만. 프론트는 자체 백엔드의 `/api/*`만 호출하고,
  외부 API 호출은 백엔드가 전담한다. 키는 응답·프론트·깃에 절대 노출하지 않는다.

---

## 📁 디렉터리 구조

```text
assembly8-review-finder/
├─ CLAUDE.md / HANDOFF.md / .env.example / .gitignore
├─ Dockerfile / docker-compose.yml / .dockerignore
├─ requirements.txt / requirements-dev.txt / pyproject.toml
├─ .claude/agents/            # 멀티 에이전트 정의(8개)
├─ app/                       # 백엔드 (FastAPI)
│  ├─ main.py                 # /api/search · /api/meta · /api/health · 정적 서빙
│  ├─ config.py               # 환경설정(키는 서버에만)
│  ├─ orchestrator.py         # 병렬 호출 · 캐시 · 페이지네이션
│  ├─ adapters/               # base / naver / secondary / demo
│  ├─ core/                   # query_strategy · ranking · dedupe · cache · quota · text
│  └─ tests/                  # pytest + respx (외부 호출 모킹, 쿼터 0 소모)
└─ web/                       # 프론트엔드 (Vite + Vanilla TS PWA)
   ├─ index.html / src/ / public/(manifest·sw·icons)
   └─ scripts/gen_icons.py    # PWA 아이콘 생성기(의존성 없음)
```

---

## 🚀 빠른 시작

### 1) 백엔드 (FastAPI)

PowerShell (5.1 / 7.x):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # 키 입력 또는 데모 모드 사용
uvicorn app.main:app --reload --port 8000
```

bash:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

- 키 없이 바로 보고 싶다면 `.env`에 `DEMO_MODE=1`을 설정한다(샘플 데이터).
- API 문서: <http://localhost:8000/docs>

### 2) 프론트엔드 (PWA, dev)

PowerShell:
```powershell
Set-Location web
npm install
npm run dev
```

bash:
```bash
cd web
npm install
npm run dev
```

- dev 서버: <http://localhost:5173> (`/api`는 자동으로 `localhost:8000`로 프록시)

### 3) 단일 서버로 실행 (프론트 빌드 → 백엔드가 서빙)

```bash
cd web
npm run build        # web/dist 생성
cd ..
uvicorn app.main:app --port 8000
```

`web/dist`가 있으면 FastAPI가 `/`에서 PWA를 직접 서빙한다. 브라우저로 <http://localhost:8000> 접속.

### 4) Docker (로컬 배포)

```bash
docker compose up --build
```

- 단일 컨테이너가 프론트(정적)와 API를 함께 8000 포트로 서빙한다.
- `.env`가 있으면 자동 로드, 없으면 데모 모드로 기동한다.

### 5) 앱 (데스크톱 · Android)

설치형 PWA에 더해 네이티브 래퍼를 제공한다 — 자세한 빌드법은 **[APP.md](APP.md)** 참고.

- **데스크톱(Electron)**: `npm --prefix web run build` 후 `npm --prefix desktop install; npm --prefix desktop start`
  (FastAPI 백엔드를 자식 프로세스로 동봉 → 단독 실행, 키 없으면 데모 모드)
- **Android(Capacitor)**: 백엔드 호스팅 후 `VITE_API_BASE=<url> npm --prefix web run build`
  → `npm --prefix web run cap:add:android` → `cap sync` → Android Studio에서 빌드

---

## 🔑 환경변수 (`.env.example` 참고)

| 변수 | 설명 |
|---|---|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 검색 API 키([developers.naver.com](https://developers.naver.com/)) |
| `SERPER_API_KEY` | (선택) 서드파티 SERP. 설정 시 보조 소스 자동 활성 |
| `GOOGLE_CSE_KEY` / `GOOGLE_CSE_CX` | (선택) 레거시 Google CSE. 2027-01-01 종료·신규 발급 불가 |
| `SEARCH_CACHE_TTL` | 캐시 TTL(초). 기본 86400(24h), `0`이면 비활성 |
| `NAVER_DAILY_QUOTA_GUARD` | 네이버 일일 호출 한도 가드. 기본 24000 |
| `MAX_QUERY_VARIANTS` | 쿼리당 변형 최대 수. 기본 4 |
| `NAVER_DISPLAY` | 변형당 카테고리에서 받아올 결과 수(≤100). 기본 20 |
| `DEMO_MODE` | `1`이면 키 없이 샘플 데이터로 동작 |
| `CORS_ORIGINS` | 프론트 dev 오리진(쉼표 구분) |

---

## 🔌 API

`GET /api/search`
- `q` (필수): 검색 키워드
- `sources`: 쉼표 구분 `blog,cafe,web,news` (기본 `blog,cafe,web`).
  `SERPER_API_KEY`/`GOOGLE_CSE_*`가 설정되면 `google`을 추가해 보조 SERP 결과를 포함할 수 있다(opt-in).
- `sort`: `sim`(관련성) | `date`(최신) (기본 `sim`)
- `page`, `page_size`
- 응답: `{ query, variants[], total, page, page_size, sort, categories[], cached, quota_remaining, results[] }`
- 상태코드: `200` / `422`(검증) / `429`(쿼터 초과) / `503`(소스 미설정)

`GET /api/meta` — 활성 어댑터·카테고리·쿼터 잔량 / `GET /api/health` — 헬스체크

---

## 🧪 테스트

PowerShell:
```powershell
pip install -r requirements-dev.txt
python -m pytest
```

bash:
```bash
pip install -r requirements-dev.txt
python -m pytest
```

- 외부 API는 `respx`로 모킹 → **실제 쿼터 0 소모**.
- 어댑터·쿼리 전략·랭킹·중복제거·캐시·쿼터·오케스트레이터·엔드포인트(키 비노출 포함) 커버.

---

## ⚖️ 리스크 & 법적 고려

- API 약관·일일 쿼터 준수(쿼터 가드 필수). 캐시로 호출량 절감.
- 후기 본문 전체를 저장·재배포하지 않는다(제목 + 스니펫 + 링크만).
- Google CSE는 신규 발급 불가·2027-01-01 종료 → 보조 소스는 네이버 단독 또는 SERP 권장.
- 개인정보: 후기에 포함된 개인 식별정보의 수집·노출에 주의.

## 🗺 향후(Out of v1)

- 보조 소스(SERP) 결과 폭 확장 · 캐시 SQLite 영속화 · 서버리스 배포 옵션.
