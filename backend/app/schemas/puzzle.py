"""
Pydantic schemas — the API-facing shapes.

These mirror the JIGSAW_CONTEXT_COMPLETE.md endpoint contracts exactly so the
frontend types (frontend/src/types/puzzle.ts) can be generated 1:1 from these.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PuzzleStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EdgeType(str, Enum):
    TAB = "tab"
    HOLE = "hole"
    FLAT = "flat"
    UNKNOWN = "unknown"


class PieceClassification(str, Enum):
    CORNER = "corner"
    BORDER = "border"
    INTERIOR = "interior"
    UNKNOWN = "unknown"


# ---------- Phase 1: Upload ----------

class UploadResponse(BaseModel):
    puzzle_id: str
    pieces_count: int = 0
    image_dims: tuple[int, int]  # (width, height)
    status: PuzzleStatus = PuzzleStatus.UPLOADED


# ---------- Puzzle summary ----------

class PuzzleSummary(BaseModel):
    puzzle_id: str
    status: PuzzleStatus
    pieces_count: int
    border_count: int = 0
    interior_count: int = 0
    corner_count: int = 0
    processing_time_ms: Optional[float] = None
    error: Optional[str] = None


# ---------- Phase 3/4/5/6: Piece metadata ----------

class EdgeSignature(BaseModel):
    top: EdgeType = EdgeType.UNKNOWN
    right: EdgeType = EdgeType.UNKNOWN
    bottom: EdgeType = EdgeType.UNKNOWN
    left: EdgeType = EdgeType.UNKNOWN


class PieceMetadata(BaseModel):
    piece_id: str  # "P001".."P1000"
    bbox: tuple[int, int, int, int]  # x, y, w, h
    centroid: tuple[float, float]  # cx, cy
    rotation: float = 0.0  # degrees, detected orientation
    edges: EdgeSignature = Field(default_factory=EdgeSignature)
    classification: PieceClassification = PieceClassification.UNKNOWN
    confidence: float = 0.0
    area: float = 0.0


class PieceDetailResponse(PieceMetadata):
    piece_image_base64: Optional[str] = None


# ---------- Debug ----------

class DebugResponse(BaseModel):
    segmentation_mask_base64: Optional[str] = None
    contours_overlay_base64: Optional[str] = None
    edges_overlay_base64: Optional[str] = None
    piece_count: int
    processing_time_ms: float


# ---------- Analyze ----------

class AnalyzeRequest(BaseModel):
    phases: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5, 6])


class AnalyzeResponse(BaseModel):
    status: str  # "processing" | "completed"
    progress: int = 0  # 0-100
