# Jigsaw Puzzle Assistant — monolithic MVP image.
#
# Single container: the FastAPI backend serves both the JSON API and the
# built React app on one port (see backend/main.py's SPA fallback route),
# so there's exactly one process to run and one port to publish.

FROM node:18-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app

# System libs OpenCV needs even in headless mode (JPEG/PNG codecs, and
# libgomp for numpy/OpenCV's multithreaded ops).
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgomp1 \
    libjpeg62-turbo \
    libpng16-16 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY scripts ./scripts
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# File-based storage lives here — mounted as a named volume in
# docker-compose.yml so uploads/pieces survive container restarts.
RUN mkdir -p /app/backend/uploads
ENV UPLOADS_DIR=/app/backend/uploads
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
