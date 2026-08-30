# ====================================
# Stage 1: Build the Frontend
# ====================================
FROM node:24-alpine as frontend-builder
WORKDIR /frontend

# Copy package files first for better caching
COPY frontend/package*.json ./
RUN npm ci || npm install

# Copy the rest of the frontend source code
COPY frontend/ .

# Build the app, then smartly locate the output directory and force it into final_dist
RUN npm run build && \
    mkdir -p /frontend/final_dist && \
    if [ -d "dist" ] && [ "$(ls -A dist)" ]; then \
        cp -a dist/. /frontend/final_dist/; \
    elif [ -d "build" ] && [ "$(ls -A build)" ]; then \
        cp -a build/. /frontend/final_dist/; \
    elif [ -d "out" ] && [ "$(ls -A out)" ]; then \
        cp -a out/. /frontend/final_dist/; \
    else \
        echo "COULD NOT FIND BUILD OUTPUT! Printing files to Render logs:" && \
        ls -la; \
    fi

# ====================================
# Stage 2: Build the Python Backend
# ====================================
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc

# Copy the backend code
COPY app/ ./app/

# Copy the successfully built frontend directly into the Python static folder
COPY --from=frontend-builder /frontend/final_dist/ ./app/static/

# Security: Run as non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Expose the API port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
