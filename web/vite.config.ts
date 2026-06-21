import { defineConfig } from "vite";

// 프론트는 자체 백엔드의 /api/* 만 호출한다(키는 백엔드 전담).
// dev 서버에서는 /api 를 FastAPI(localhost:8000)로 프록시한다.
export default defineConfig({
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
