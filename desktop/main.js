// Electron 메인 프로세스.
// FastAPI 백엔드(uvicorn)를 자식 프로세스로 띄우고, 헬스체크 후 그 화면을 로드한다.
// 백엔드가 /api 와 정적 프론트(web/dist)를 함께 서빙하므로 단일 창으로 완결된다.
"use strict";

const { app, BrowserWindow, shell } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const http = require("http");
const net = require("net");

let backend = null;
let backendPort = 0;

const REPO_ROOT = path.resolve(__dirname, "..");

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const { port } = srv.address();
      srv.close(() => resolve(port));
    });
  });
}

// 백엔드 실행 명령을 결정한다.
//  1) A8_BACKEND_CMD 환경변수(셸 명령)
//  2) 패키징된 백엔드 바이너리(resources/backend/a8backend[.exe], PyInstaller 등)
//  3) 개발: 저장소 .venv 또는 시스템 파이썬으로 uvicorn 실행
function resolveBackend(port) {
  if (process.env.A8_BACKEND_CMD) {
    return { cmd: process.env.A8_BACKEND_CMD, args: [], cwd: REPO_ROOT, shell: true };
  }
  const isWin = process.platform === "win32";
  const exe = isWin ? "a8backend.exe" : "a8backend";
  const bundled = path.join(process.resourcesPath || REPO_ROOT, "backend", exe);
  if (fs.existsSync(bundled)) {
    return { cmd: bundled, args: ["--host", "127.0.0.1", "--port", String(port)], cwd: path.dirname(bundled) };
  }
  const venvPy = isWin
    ? path.join(REPO_ROOT, ".venv", "Scripts", "python.exe")
    : path.join(REPO_ROOT, ".venv", "bin", "python");
  const py = fs.existsSync(venvPy) ? venvPy : isWin ? "python" : "python3";
  return {
    cmd: py,
    args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
    cwd: REPO_ROOT,
  };
}

function startBackend(port) {
  const { cmd, args, cwd, shell: useShell } = resolveBackend(port);
  // 키가 없을 때를 대비해 기본 데모 모드. 사용자가 .env/환경변수로 덮어쓸 수 있다.
  const env = Object.assign({}, process.env, { DEMO_MODE: process.env.DEMO_MODE || "1" });
  console.log("[desktop] launching backend:", cmd, args.join(" "));
  backend = spawn(cmd, args, { cwd, env, shell: !!useShell });
  backend.stdout.on("data", (d) => console.log("[backend]", String(d).trimEnd()));
  backend.stderr.on("data", (d) => console.log("[backend]", String(d).trimEnd()));
  backend.on("error", (e) => console.error("[desktop] backend spawn error:", e));
  backend.on("exit", (code) => console.log("[desktop] backend exited:", code));
}

function waitForHealth(port, timeoutMs = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(
        { host: "127.0.0.1", port, path: "/api/health", timeout: 1500 },
        (res) => {
          res.resume();
          if (res.statusCode === 200) resolve();
          else retry();
        },
      );
      req.on("error", retry);
      req.on("timeout", () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (Date.now() - start > timeoutMs) reject(new Error("backend health timeout"));
      else setTimeout(attempt, 400);
    };
    attempt();
  });
}

function errorPage(message) {
  const html = `<!doctype html><html lang="ko"><meta charset="utf-8">
  <body style="font-family:system-ui;background:#0e0f13;color:#eef1f6;margin:0;
  display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center;padding:24px">
  <div><h2>백엔드를 시작하지 못했습니다</h2>
  <p style="color:#9aa3b2;max-width:520px;line-height:1.6">${message}</p>
  <p style="color:#9aa3b2">저장소 루트에서 <code>python -m venv .venv</code> 후
  <code>pip install -r requirements.txt</code> 를 실행했는지 확인하세요.</p></div></body></html>`;
  return "data:text/html;charset=utf-8," + encodeURIComponent(html);
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 820,
    minWidth: 360,
    minHeight: 480,
    title: "국회직 8급 합격후기 검색",
    backgroundColor: "#0e0f13",
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // 결과 카드의 외부 링크(target=_blank)는 기본 브라우저로 연다.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });

  try {
    backendPort = await getFreePort();
    startBackend(backendPort);
    await waitForHealth(backendPort);
    await win.loadURL(`http://127.0.0.1:${backendPort}/`);
  } catch (e) {
    await win.loadURL(errorPage(String(e && e.message ? e.message : e)));
  }
}

function stopBackend() {
  if (backend && !backend.killed) {
    try { backend.kill(); } catch (_) { /* noop */ }
    backend = null;
  }
}

app.whenReady().then(createWindow);
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
app.on("window-all-closed", () => {
  stopBackend();
  if (process.platform !== "darwin") app.quit();
});
app.on("before-quit", stopBackend);
process.on("exit", stopBackend);
