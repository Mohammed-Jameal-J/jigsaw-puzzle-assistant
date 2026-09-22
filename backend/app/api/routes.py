"""
API routes — mirrors the endpoint contract in JIGSAW_CONTEXT_COMPLETE.md.

Phase 1 (upload) and Phase 2/3 (detect + ID pieces) are fully implemented.
Phase 4/5/6 (border/corner, edge classification, rotation refinement) are
wired into /analyze's response shape already but return "unknown" /
placeholder values until those services are built next.
"""
from __future__ import annotations

import base64
import time

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging import logger
from app.database import storage
from app.models.puzzle import PuzzleRecord
from app.schemas.puzzle import (
    AnalyzeRequest,
    AnalyzeResponse,
    DebugResponse,
    PieceDetailResponse,
    PuzzleStatus,
    PuzzleSummary,
    UploadResponse,
)
from app.services.image_processor import (
    UploadValidationError,
    decode_and_validate_image,
    save_original_image,
    validate_and_read_upload,
)
from app.services.piece_detector import detect_pieces, save_debug_images, save_piece_crops

router = APIRouter(prefix=settings.API_V1_PREFIX)


def _get_record_or_404(puzzle_id: str) -> PuzzleRecord:
    record = storage.load_record(puzzle_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Puzzle '{puzzle_id}' not found")
    return record


# ---------- Phase 1: Upload ----------

@router.post("/puzzle/upload", response_model=UploadResponse)
async def upload_puzzle(image: UploadFile = File(...)) -> UploadResponse:
    try:
        data = await validate_and_read_upload(image)
        img, width, height = decode_and_validate_image(data)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    puzzle_id = storage.new_puzzle_id()
    storage.create_puzzle_dirs(puzzle_id)
    image_path = save_original_image(img, storage.puzzle_dir(puzzle_id))

    record = PuzzleRecord(
        puzzle_id=puzzle_id,
        original_filename=image.filename or "upload.jpg",
        image_path=str(image_path),
        image_width=width,
        image_height=height,
        status=PuzzleStatus.UPLOADED.value,
    )
    storage.save_record(record)
    logger.info(f"Uploaded puzzle {puzzle_id}: {width}x{height} from '{image.filename}'")

    return UploadResponse(
        puzzle_id=puzzle_id,
        pieces_count=0,
        image_dims=(width, height),
        status=PuzzleStatus.UPLOADED,
    )


# ---------- Analyze (runs the CV pipeline) ----------

@router.post("/puzzle/{puzzle_id}/analyze", response_model=AnalyzeResponse)
async def analyze_puzzle(puzzle_id: str, body: AnalyzeRequest) -> AnalyzeResponse:
    record = _get_record_or_404(puzzle_id)
    record.status = PuzzleStatus.PROCESSING.value
    storage.save_record(record)

    try:
        # Phase 2 + 3: detection is required for any of the requested phases
        # to mean anything; later phases (4/5/6) will read from this result
        # once their services exist.
        if any(p in body.phases for p in (2, 3, 4, 5, 6)):
            t0 = time.perf_counter()
            result = detect_pieces(record.image_path)
            save_piece_crops(record.image_path, result.pieces, storage.pieces_dir(puzzle_id))
            save_debug_images(result, storage.debug_dir(puzzle_id))
            total_ms = (time.perf_counter() - t0) * 1000

            record.pieces = result.pieces
            record.pieces_count = result.piece_count
            record.processing_time_ms = total_ms
            # classification counts default to 0 until Phase 4 lands; kept
            # explicit here rather than silently stale.
            record.corner_count = sum(1 for p in result.pieces if p["classification"] == "corner")
            record.border_count = sum(1 for p in result.pieces if p["classification"] == "border")
            record.interior_count = sum(1 for p in result.pieces if p["classification"] == "interior")

        record.status = PuzzleStatus.COMPLETED.value
        record.error = None
    except Exception as exc:  # noqa: BLE001 — surfaced to the client as a failed status, not a 500
        logger.exception(f"analyze failed for puzzle {puzzle_id}")
        record.status = PuzzleStatus.FAILED.value
        record.error = str(exc)

    storage.save_record(record)
    return AnalyzeResponse(
        status="completed" if record.status == PuzzleStatus.COMPLETED.value else "processing",
        progress=100 if record.status == PuzzleStatus.COMPLETED.value else 0,
    )


# ---------- Puzzle summary ----------

@router.get("/puzzle/{puzzle_id}", response_model=PuzzleSummary)
async def get_puzzle(puzzle_id: str) -> PuzzleSummary:
    record = _get_record_or_404(puzzle_id)
    return PuzzleSummary(
        puzzle_id=record.puzzle_id,
        status=PuzzleStatus(record.status),
        pieces_count=record.pieces_count,
        border_count=record.border_count,
        interior_count=record.interior_count,
        corner_count=record.corner_count,
        processing_time_ms=record.processing_time_ms,
        error=record.error,
    )


# ---------- Pieces ----------

@router.get("/puzzle/{puzzle_id}/image")
async def get_original_image(puzzle_id: str) -> FileResponse:
    """
    Serves the original uploaded photo. Not in the original spec's endpoint
    list, but small and useful: it lets the frontend render piece thumbnails
    by cropping client-side (one request) instead of one request per piece.
    """
    record = _get_record_or_404(puzzle_id)
    return FileResponse(record.image_path, media_type="image/jpeg")


@router.get("/puzzle/{puzzle_id}/pieces")
async def list_pieces(puzzle_id: str) -> list[dict]:
    record = _get_record_or_404(puzzle_id)
    return record.pieces


@router.get("/puzzle/{puzzle_id}/pieces/{piece_id}", response_model=PieceDetailResponse)
async def get_piece(puzzle_id: str, piece_id: str) -> PieceDetailResponse:
    record = _get_record_or_404(puzzle_id)
    piece = next((p for p in record.pieces if p["piece_id"] == piece_id), None)
    if piece is None:
        raise HTTPException(status_code=404, detail=f"Piece '{piece_id}' not found")

    crop_path = storage.pieces_dir(puzzle_id) / f"{piece_id}.png"
    image_b64 = None
    if crop_path.exists():
        image_b64 = base64.b64encode(crop_path.read_bytes()).decode("ascii")

    return PieceDetailResponse(**piece, piece_image_base64=image_b64)


# ---------- Debug ----------

@router.get("/puzzle/{puzzle_id}/debug", response_model=DebugResponse)
async def get_debug(puzzle_id: str) -> DebugResponse:
    record = _get_record_or_404(puzzle_id)
    debug_dir = storage.debug_dir(puzzle_id)

    def encode(path):
        if not path.exists():
            return None
        return base64.b64encode(path.read_bytes()).decode("ascii")

    return DebugResponse(
        segmentation_mask_base64=encode(debug_dir / "mask.png"),
        contours_overlay_base64=encode(debug_dir / "contours.png"),
        edges_overlay_base64=encode(debug_dir / "edges.png"),  # Phase 5, not generated yet
        piece_count=record.pieces_count,
        processing_time_ms=record.processing_time_ms or 0.0,
    )
