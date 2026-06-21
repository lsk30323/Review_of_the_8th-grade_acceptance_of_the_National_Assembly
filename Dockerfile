# --- Stage 1: 프론트엔드(PWA) 빌드 ---
FROM node:22-alpine AS frontend
WORKDIR /web
COPY web/package*.json ./
RUN npm install
COPY web/ ./
RUN npm run build

# --- Stage 2: 백엔드 런타임 (API + 정적 프론트 서빙) ---
FROM python:3.11-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY app/ ./app/
# 빌드된 프론트를 web/dist 로 복사 → FastAPI가 "/"에서 직접 서빙
COPY --from=frontend /web/dist ./web/dist

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
