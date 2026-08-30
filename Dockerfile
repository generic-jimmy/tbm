# ── Stage 1: build React SPA ──────────────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --prefer-offline

COPY frontend/ ./
# Outputs to /frontend/dist (Vite default; do NOT override outDir)
RUN npm run build


# ── Stage 2: Python API server ────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install backend deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY app/ ./app/

# Copy the compiled frontend into app/static so FastAPI serves it
COPY --from=frontend-builder /frontend/dist ./app/static/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
