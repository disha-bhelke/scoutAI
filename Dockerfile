# ==============================================================================
# Scout AI - Production Dockerfile (Render Backend Service)
# ==============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime system dependencies for health checks and security certs
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies first (caches Docker layers for faster re-builds)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only the backend source code into the image
COPY backend/ ./backend/

# Set working directory to backend so main.py and relative imports resolve cleanly
WORKDIR /app/backend

# Render automatically assigns $PORT at runtime
EXPOSE 8000

# Health check to ensure FastAPI is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start Uvicorn binding to 0.0.0.0 and dynamic $PORT
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}