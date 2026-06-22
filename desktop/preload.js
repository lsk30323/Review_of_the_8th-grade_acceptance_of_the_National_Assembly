// 최소 preload. 렌더러는 백엔드의 /api 만 호출하므로 노출할 브리지는 없다.
// contextIsolation을 켠 상태에서 안전하게 앱 메타데이터만 제공한다.
"use strict";

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("desktopApp", {
  platform: process.platform,
  version: process.versions.electron,
});
