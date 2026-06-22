# 앱으로 빌드하기 (데스크톱 · Android)

이 프로젝트는 기본이 **설치형 PWA**입니다(브라우저에서 "설치/홈 화면에 추가"). 그 위에
두 가지 네이티브 래퍼를 제공합니다.

- **데스크톱(Electron)** — Windows/Mac/Linux. FastAPI 백엔드를 자식 프로세스로 동봉 → 단독 실행.
- **Android(Capacitor)** — 빌드된 PWA를 네이티브 앱으로 래핑. 원격 백엔드를 호출.

> 셸 호환: 아래 명령은 PowerShell 5.1/7.x와 bash 모두에서 동작하도록 `&&` 없이 줄 단위로 적습니다.

---

## 1) 데스크톱 앱 (Electron)

백엔드(`app/`)가 `/api` 와 정적 프론트(`web/dist`)를 함께 서빙하므로, Electron은 백엔드를
띄우고 그 화면을 로드하기만 합니다. 키가 없으면 자동으로 데모 모드로 뜹니다.

### 개발 실행

먼저 백엔드 의존성과 프론트 빌드를 준비합니다(최초 1회).

```bash
python -m venv .venv
. .venv/bin/activate          # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm --prefix web install
npm --prefix web run build    # web/dist 생성
```

데스크톱 앱 실행:

```bash
npm --prefix desktop install
npm --prefix desktop start
```

- 실제 검색을 하려면 저장소 루트 `.env` 에 `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` 를 넣습니다.
- 데모로 보려면 그대로 실행하면 됩니다(`DEMO_MODE`가 기본 1로 주입됨).
- 결과 카드의 외부 링크는 기본 브라우저로 열립니다.

### 백엔드 실행 방식(자동 탐색 순서)

`desktop/main.js` 는 다음 순서로 백엔드를 찾습니다.

1. 환경변수 `A8_BACKEND_CMD` (셸 명령)
2. 패키징된 바이너리 `resources/backend/a8backend[.exe]` (PyInstaller 등으로 동봉 시)
3. 저장소 `.venv` 파이썬 → 없으면 시스템 `python`/`python3` 로 `uvicorn app.main:app`

### 설치 파일 빌드(.exe/.dmg/AppImage)

```bash
npm --prefix desktop run dist
```

> 완전 자립형(파이썬 미설치 PC 배포)으로 만들려면 백엔드를 PyInstaller로 단일 실행파일
> (`a8backend`)로 묶어 `desktop/build/backend/` 에 넣고 `extraResources` 로 동봉하세요.
> 현재 구성은 개발 실행과 Electron 셸 패키징까지 제공합니다.

---

## 2) Android 앱 (Capacitor)

빌드된 PWA(`web/dist`)를 네이티브 Android 앱으로 감쌉니다. **모바일 앱의 웹뷰는
`capacitor://localhost` 오리진**이라 상대경로 `/api` 가 자체 백엔드로 가지 않습니다.
따라서 **백엔드를 어딘가에 호스팅**하고, 그 절대 URL을 빌드시 주입해야 합니다.

### 준비물
- Node.js, Android Studio(SDK 포함), JDK 17
- 호스팅된 백엔드 URL (예: `https://your-backend.example.com`)

### 절차

```bash
npm --prefix web install

# 1) 백엔드 절대 URL을 주입해 PWA 빌드
#    PowerShell:  $env:VITE_API_BASE="https://your-backend.example.com"; npm --prefix web run build
VITE_API_BASE="https://your-backend.example.com" npm --prefix web run build

# 2) Android 네이티브 프로젝트 생성(최초 1회)
npm --prefix web run cap:add:android

# 3) 빌드 산출물 동기화
npm --prefix web run cap:sync

# 4) Android Studio 열기 → 기기/에뮬레이터에서 Run, 또는 APK/AAB 빌드
npx --prefix web cap open android
```

이후 프론트를 수정하면 `npm --prefix web run app:android` 한 번으로
빌드 → 동기화 → Android Studio 열기까지 진행됩니다.

### 백엔드 CORS / 보안
- 백엔드 `.env` 의 `CORS_ORIGINS` 에 `capacitor://localhost`, `https://localhost` 가
  기본 포함되어 있습니다(앱이 바로 호출 가능).
- 백엔드는 **HTTPS** 호스팅을 권장합니다. 부득이 HTTP면 `web/capacitor.config.ts` 의
  `server.cleartext`/`android.allowMixedContent` 주석을 해제하세요(개발용).
- 앱 아이콘은 `web/public/icons/icon-512.png` 를 사용해 `@capacitor/assets` 로 생성할 수 있습니다.

---

## 3) CI 자동 빌드 (GitHub Actions)

로컬 환경 없이도 GitHub Actions가 설치 파일을 대신 만들어 줍니다.

- `.github/workflows/build-desktop.yml` — Windows/macOS/Linux 러너에서 각각
  `.exe`(NSIS) / `.dmg` / `AppImage` 를 빌드. 미서명 산출물.
- `.github/workflows/build-android.yml` — Ubuntu 러너에서 Capacitor로 디버그 `.apk` 빌드.

### 실행 방법
1. **수동**: GitHub → Actions 탭 → 해당 워크플로 → "Run workflow".
   - Android는 실행 시 `백엔드 URL`(VITE_API_BASE)을 입력할 수 있습니다(미입력 시 빈 값/저장소 변수).
2. **태그 릴리스**: `v1.0.0` 처럼 `v*` 태그를 푸시하면 두 워크플로가 모두 돌고,
   같은 태그의 GitHub **Release** 에 산출물(.exe/.dmg/AppImage/.apk)이 자동 첨부됩니다.

   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

### 산출물 받기
- 수동 실행: 워크플로 실행 페이지 하단의 **Artifacts** 에서 내려받습니다
  (`desktop-windows` / `desktop-macos` / `desktop-linux` / `android-debug-apk`).
- 태그 실행: 저장소 **Releases** 페이지의 첨부 파일.

### Android 백엔드 URL 기본값(선택)
태그 릴리스에서도 항상 같은 백엔드를 쓰려면 저장소 **Settings → Secrets and variables →
Actions → Variables** 에 `VITE_API_BASE` 변수를 추가하세요(예: `https://your-backend.example.com`).
미설정 시 빈 값으로 빌드되어 앱이 백엔드를 찾지 못합니다(디버그 산출물 용도).

> 참고: 데스크톱 CI 산출물은 Electron 셸 + `web/dist` 까지만 포함합니다. 파이썬 미설치 PC용
> 완전 자립형 배포는 백엔드를 PyInstaller로 묶어 `extraResources` 로 동봉하는 추가 작업이 필요합니다.

---

## iOS (참고)
동일하게 `npx cap add ios` 후 `npx cap open ios` 로 진행하며, 빌드/배포에는 macOS + Xcode가
필요합니다. (현재 저장소는 Android 구성을 기본 제공합니다.)
