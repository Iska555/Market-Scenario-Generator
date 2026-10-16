FROM node:22-bookworm-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_URL=""
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PUBLIC_RELEASE_MODE=1 FRONTEND_DIST=/app/frontend-dist ENABLE_DEMO_PREVIEW=0 ENABLE_PRIVATE_SIMULATIONS=0 LOKY_MAX_CPU_COUNT=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/src ./src
COPY backend/main.py backend/alembic.ini ./
COPY backend/migrations ./migrations
COPY backend/demo ./demo
COPY --from=frontend /frontend/dist ./frontend-dist
RUN useradd --uid 10001 --create-home release
USER release
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--limit-concurrency", "16"]
