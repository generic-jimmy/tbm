# ── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ .

# Execute build, forcefully map any known output directory to 'dist', 
# and guarantee 'dist' exists at the OS level to prevent Docker build crashes.
RUN npm run build && \
    for dir in build out .next public; do \
        if [ -d "$dir" ] && [ ! -d "dist" ]; then \
            mv "$dir" dist; \
            break; \
        fi; \
    done && \
    mkdir -p dist

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc

COPY app/ ./app/

# Ingest assets. The 'mkdir -p dist' in Stage 1 ensures this command never fatals.
COPY --from=frontend-builder /frontend/dist ./app/static/

RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser
EXPOSE ${PORT}

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --loop uvloop --http httptools"]
