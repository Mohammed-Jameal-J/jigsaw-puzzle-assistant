"""
Internal dataclasses for puzzle state kept in the file-based store.

Distinct from app/schemas/puzzle.py (API contracts) — this is the shape we
persist to disk as JSON. Kept intentionally close to the schemas for the MVP
since we have no ORM/DB layer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class PuzzleRecord:
    puzzle_id: str
    original_filename: str
    image_path: str  # absolute path to the stored original image
    image_width: int
    image_height: int
    status: str = "uploaded"  # uploaded | processing | completed | failed
    pieces_count: int = 0
    border_count: int = 0
    interior_count: int = 0
    corner_count: int = 0
    processing_time_ms: Optional[float] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    pieces: list[dict[str, Any]] = field(default_factory=list)  # list of piece dicts

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PuzzleRecord":
        return cls(**data)
