"""
Phase 2 (piece detection) + Phase 3 (ID assignment) orchestration.

Pipeline: load -> HSV -> CLAHE (lighting correction) -> background
threshold -> morphological open/close -> external contours -> area
filter -> per-piece features -> row-major sort -> P0001..P{N} IDs ->
crop + save each piece -> debug overlays.

Kept as one function per phase requirement ("Detection time: <5 seconds
REQUIRED") so timing is easy to reason about and log.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.cv.edge_analysis import EdgeClassification, classify_piece
from app.cv.feature_extraction import RawPiece, extract_crop, extract_piece_features, sort_row_major
from app.cv.preprocessing import apply_clahe_to_value_channel, morphological_clean, resize_max_dim, to_hsv
from app.cv.rotation import extract_core_shape
from app.cv.segmentation import (
    draw_contours_overlay,
    estimate_background_color,
    filter_contours_by_area,
    find_piece_contours,
    foreground_mask,
)


@dataclass
class DetectionResult:
    pieces: list[dict]                 # API-shaped piece dicts (bbox/centroid/etc. in ORIGINAL image coords)
    piece_count: int
    processing_time_ms: float
    mask: np.ndarray                   # at detection resolution
    contours_overlay: np.ndarray        # at detection resolution
    edges_overlay: np.ndarray           # at detection resolution; pieces colored by classification
    detect_scale: float                # detection_resolution -> original_resolution multiplier is 1/detect_scale


# Cap detection working resolution so a 4000x3000+ photo still processes
# comfortably inside the <5s budget; coordinates are scaled back up after.
DETECTION_MAX_DIM = 2200


def detect_pieces(image_path: str) -> DetectionResult:
    t0 = time.perf_counter()

    original = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError(f"Could not read image: {image_path}")

    working, scale = resize_max_dim(original, DETECTION_MAX_DIM)

    hsv = to_hsv(working)
    hsv_eq = apply_clahe_to_value_channel(hsv)
    working_eq = cv2.cvtColor(hsv_eq, cv2.COLOR_HSV2BGR)

    bg_color = estimate_background_color(working_eq)
    mask = foreground_mask(working_eq, bg_color)
    mask = morphological_clean(mask, open_kernel=5, close_kernel=9)

    contours = find_piece_contours(mask)

    img_area = working.shape[0] * working.shape[1]
    min_area = img_area * settings.MIN_PIECE_AREA_RATIO
    max_area = img_area * settings.MAX_PIECE_AREA_RATIO
    contours = filter_contours_by_area(contours, min_area, max_area)

    raw_pieces = [extract_piece_features(c) for c in contours]
    raw_pieces = sort_row_major(raw_pieces)

    edge_results = [_classify_raw_piece(p) for p in raw_pieces]

    inv_scale = 1.0 / scale
    pieces = [
        _to_api_piece(p, idx + 1, inv_scale, edge_result)
        for idx, (p, edge_result) in enumerate(zip(raw_pieces, edge_results))
    ]
    _apply_global_corner_selection(pieces, edge_results)

    contours_overlay = draw_contours_overlay(working, [p.contour for p in raw_pieces])
    edges_overlay = _draw_edges_overlay(working, raw_pieces, pieces)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        f"detect_pieces: {len(pieces)} pieces in {elapsed_ms:.0f}ms "
        f"(working res {working.shape[1]}x{working.shape[0]}, scale={scale:.3f})"
    )

    return DetectionResult(
        pieces=pieces,
        piece_count=len(pieces),
        processing_time_ms=elapsed_ms,
        mask=mask,
        contours_overlay=contours_overlay,
        edges_overlay=edges_overlay,
        detect_scale=scale,
    )


def _classify_raw_piece(p: RawPiece) -> EdgeClassification:
    """Phase 4/5: border/corner classification + per-side tab/hole/flat."""
    core = extract_core_shape(p.contour)
    if core is None:
        return EdgeClassification()
    return classify_piece(p.contour, core)


# A rectangular assembled puzzle always has EXACTLY 4 corners — a global,
# structural fact this pipeline wasn't using anywhere before, even though
# per-piece flat/tab/hole thresholding alone is noisy enough (measured
# ~96% per-edge accuracy) that naive per-piece corner counts overshoot by
# 2-3x across ~1000 pieces' worth of edges. Ranking every piece by "how
# flat do its best 2 edges look" and taking the global top 4 turns that
# same noisy per-edge signal into a comparison-based decision, which is
# far more robust than any fixed per-piece threshold could be — it doesn't
# need the noise to be small, just smaller than the true corner/non-corner
# gap on average.
CORNER_COUNT = 4


def _apply_global_corner_selection(pieces: list[dict], edge_results: list[EdgeClassification]) -> None:
    candidates = []
    for i, er in enumerate(edge_results):
        if not er.edge_deviation:
            continue  # core extraction failed for this piece; leave its fallback classification alone
        two_best = sorted(er.edge_deviation.values())[:2]
        candidates.append((sum(two_best), i))
    candidates.sort(key=lambda pair: pair[0])
    corner_indices = {i for _, i in candidates[:CORNER_COUNT]}

    for i, piece in enumerate(pieces):
        if i in corner_indices:
            piece["classification"] = "corner"
            continue
        flat_count = sum(1 for v in piece["edges"].values() if v == "flat")
        piece["classification"] = "border" if flat_count >= 1 else "interior"


# BGR (OpenCV convention) — matches the frontend's classification colors
# (corner=amber, border=blue, interior=gray) for visual consistency.
_CLASSIFICATION_COLORS_BGR = {
    "corner": (11, 158, 245),
    "border": (246, 130, 59),
    "interior": (209, 213, 219),
    "unknown": (229, 231, 235),
}


def _draw_edges_overlay(working: np.ndarray, raw_pieces: list[RawPiece], pieces: list[dict]) -> np.ndarray:
    """Phase 5 debug view: each piece's contour colored by its classification."""
    overlay = working.copy()
    for raw, piece in zip(raw_pieces, pieces):
        color = _CLASSIFICATION_COLORS_BGR.get(piece["classification"], _CLASSIFICATION_COLORS_BGR["unknown"])
        cv2.drawContours(overlay, [raw.contour], -1, color, 2)
    return overlay


def _to_api_piece(p: RawPiece, index: int, inv_scale: float, edge_result: EdgeClassification) -> dict:
    x, y, w, h = p.bbox
    cx, cy = p.centroid
    # Phase 6: prefer the core-shape rotation estimate (tab/hole-aware) over
    # the raw minAreaRect angle, when we managed to extract a core; it's
    # noticeably more stable since tabs no longer skew it.
    rotation = edge_result.rotation if edge_result.edges else float(p.rect_angle)
    return {
        "piece_id": f"P{index:04d}",
        "bbox": [round(x * inv_scale), round(y * inv_scale), round(w * inv_scale), round(h * inv_scale)],
        "centroid": [round(cx * inv_scale, 2), round(cy * inv_scale, 2)],
        "rotation": round(rotation, 2),
        "edges": {
            "top": edge_result.edges.get("top", "unknown"),
            "right": edge_result.edges.get("right", "unknown"),
            "bottom": edge_result.edges.get("bottom", "unknown"),
            "left": edge_result.edges.get("left", "unknown"),
        },
        "classification": edge_result.classification,
        "confidence": 0.9 if edge_result.edges else 0.5,
        "area": round(float(p.area) * (inv_scale ** 2), 1),
    }


def save_piece_crops(image_path: str, pieces: list[dict], pieces_dir: Path) -> None:
    """Extract and save each piece's crop from the ORIGINAL (full-res) image."""
    original = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if original is None:
        raise ValueError(f"Could not read image: {image_path}")

    for piece in pieces:
        x, y, w, h = piece["bbox"]
        crop = extract_crop(original, (x, y, w, h), padding=6)
        out_path = pieces_dir / f"{piece['piece_id']}.png"
        cv2.imwrite(str(out_path), crop)


def save_debug_images(result: DetectionResult, debug_dir: Path) -> None:
    cv2.imwrite(str(debug_dir / "mask.png"), result.mask)
    cv2.imwrite(str(debug_dir / "contours.png"), result.contours_overlay)
    cv2.imwrite(str(debug_dir / "edges.png"), result.edges_overlay)
