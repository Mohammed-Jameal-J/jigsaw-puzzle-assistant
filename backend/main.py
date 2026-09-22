"""
Jigsaw Puzzle Assistant — FastAPI entrypoint.

Monolithic MVP: one process serves both the JSON API and the built React
app, so `docker-compose up` needs exactly one container and one port. In
local dev, run this on :8000 and the Vite dev server separately on :5173
(vite.config.ts proxies /api to :8000) — the block below only activates
once frontend/dist exists, i.e. after `npm run build`.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.routes import router
from app.core.config import settings
from app.core.logging import logger

app = FastAPI(
    title=settings.APP_NAME,
    description="Computer-vision assistant for solving physical jigsaw puzzles.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


@app.on_event("startup")
async def on_startup() -> None:
    settings.ensure_dirs()
    logger.info(f"{settings.APP_NAME} backend started. Uploads dir: {settings.UPLOADS_DIR}")


# --- Serve the built frontend (backend and frontend are siblings under /app
# in the Docker image, and under the repo root locally) ---
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    logger.info(f"Serving built frontend from {FRONTEND_DIST}")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str) -> FileResponse:
        """
        Any path not matched by an /api route above falls through to here.
        Serves the matching static file (JS/CSS/images) if it exists, or
        index.html otherwise — the standard SPA fallback so React Router
        routes like /results/{id} work on a hard refresh, not just on
        client-side navigation.
        """
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    logger.info(f"No built frontend at {FRONTEND_DIST} — API-only mode (fine for local dev with `npm run dev`).")

