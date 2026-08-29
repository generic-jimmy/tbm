# ── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:24-alpine AS frontend-builder

WORKDIR /frontend

# Install dependencies without NODE_ENV restriction to ensure devDependencies (Vite) resolve
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

# Build frontend and normalize output directory to guarantee COPY command succeeds
COPY frontend/ .
RUN npm run build && \
    if [ -d "build" ] && [ ! -d "dist" ]; then mv build dist; fi

# ── Stage 2: Python runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Python container optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# System dependencies (gcc added for wheel compilation, removed post-install)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc

# Application source
COPY app/ ./app/

# Ingest compiled React assets from normalized 'dist' directory
COPY --from=frontend-builder /frontend/dist ./app/static/

# Security: Strict least privilege execution
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser \
    && chown -R appuser:appgroup /app

USER appuser
EXPOSE ${PORT}

# Resilient health validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Execute using high-performance bindings
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --loop uvloop --http httptools"]
