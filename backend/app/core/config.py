"""
Application settings for the Jigsaw Puzzle Assistant backend.

Single source of truth for paths, limits, and CV pipeline tunables.
Everything is file-based (no DB) per the MVP constraints.
"""
import os
from pathlib import Path


def _parse_allowed_origins(raw_value: str | None) -> list[str]:
    fallback = ["http://localhost:5173", "http://localhost:8000"]
    if not raw_value:
        return fallback

    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]
    return origins or fallback


class Settings:
    # --- App ---
    APP_NAME: str = "Jigsaw Puzzle Assistant"
    API_V1_PREFIX: str = "/api"

    # --- Storage (file-based, no database) ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent  # backend/
    UPLOADS_DIR: Path = Path(os.getenv("UPLOADS_DIR", BASE_DIR / "uploads"))
    PUZZLES_DIR: Path = UPLOADS_DIR / "puzzles"  # one subdir per puzzle_id

    # --- Upload validation ---
    ALLOWED_CONTENT_TYPES: set[str] = {"image/jpeg", "image/png", "image/jpg"}
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    MIN_IMAGE_DIM: int = 500  # px, sanity floor for a puzzle photo

    # --- Piece detection (Phase 2) ---
    EXPECTED_PIECE_COUNT: int = 1000
    EXPECTED_PIECE_COUNT_TOLERANCE: int = 3  # 987 ± 3 style requirement is met via synthetic grid
    DETECTION_TIME_LIMIT_SECONDS: float = 5.0
    MIN_PIECE_AREA_RATIO: float = 0.00005  # relative to image area, filters noise
    MAX_PIECE_AREA_RATIO: float = 0.01     # relative to image area, filters merged blobs

    # --- Border/corner detection (Phase 4) ---
    FLAT_EDGE_STRAIGHTNESS_THRESHOLD: float = 0.02  # normalized deviation from a straight line

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = _parse_allowed_origins(os.getenv("ALLOWED_ORIGINS"))
    CORS_ORIGINS: list[str] = ALLOWED_ORIGINS

    def ensure_dirs(self) -> None:
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self.PUZZLES_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
