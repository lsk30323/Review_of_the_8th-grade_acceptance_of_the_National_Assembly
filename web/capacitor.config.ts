import type { CapacitorConfig } from "@capacitor/cli";

// Capacitor: 빌드된 PWA(dist)를 Android 네이티브 앱으로 감싼다.
//
// 모바일 앱의 웹뷰는 capacitor://localhost(또는 https://localhost) 오리진에서 뜨므로
// 상대경로 /api 가 자체 백엔드로 가지 않는다. 따라서 web을 빌드할 때 백엔드 절대 URL을
// VITE_API_BASE 로 지정해야 한다. 예:
//   VITE_API_BASE="https://your-backend.example.com" npm run build
// 그리고 백엔드 CORS_ORIGINS 에 capacitor://localhost, https://localhost 를 허용한다.
const config: CapacitorConfig = {
  appId: "com.assembly8.reviewfinder",
  appName: "8급 합격후기 검색",
  webDir: "dist",
  // 백엔드를 HTTP(비-TLS)로 호스팅하는 경우에만 주석을 해제한다(개발용).
  // android: { allowMixedContent: true },
  // server: { cleartext: true },
};

export default config;
