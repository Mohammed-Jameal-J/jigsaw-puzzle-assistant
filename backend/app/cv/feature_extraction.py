"""
Phase 2/3 feature extraction: turn a raw contour into the metadata fields
the API needs (bbox, centroid, an initial rotation estimate from the
min-area rect), plus the crop used for Phase 6/5 downstream work and the
row-major sort used to assign P0001..P{N} IDs (Phase 3).
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class RawPiece:
    contour: np.ndarray
    bbox: tuple[int, int, int, int]       # x, y, w, h
    centroid: tuple[float, float]
    area: float
    rect_angle: float                     # raw cv2.minAreaRect angle, degrees


def extract_piece_features(contour: np.ndarray) -> RawPiece:
    x, y, w, h = cv2.boundingRect(contour)
    area = cv2.contourArea(contour)

    m = cv2.moments(contour)
    if m["m00"] != 0:
        cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
    else:
        cx, cy = x + w / 2.0, y + h / 2.0

    (_, _), (_, _), angle = cv2.minAreaRect(contour)

    return RawPiece(contour=contour, bbox=(x, y, w, h), centroid=(cx, cy), area=area, rect_angle=angle)


def extract_crop(img_bgr: np.ndarray, bbox: tuple[int, int, int, int], padding: int = 6) -> np.ndarray:
    x, y, w, h = bbox
    ih, iw = img_bgr.shape[:2]
    x0 = max(0, x - padding)
    y0 = max(0, y - padding)
    x1 = min(iw, x + w + padding)
    y1 = min(ih, y + h + padding)
    return img_bgr[y0:y1, x0:x1].copy()


def sort_row_major(pieces: list[RawPiece]) -> list[RawPiece]:
    """
    Sort pieces top-left to bottom-right: group into rows by centroid y
    (band width = ~0.6x the median piece height, adaptive to piece size),
    then sort left-to-right within each row.
    """
    if not pieces:
        return []

    heights = sorted(p.bbox[3] for p in pieces)
    median_h = heights[len(heights) // 2] or 1
    row_band = max(1.0, median_h * 0.6)

    # Assign a row index by sorting on y first, then bucketing.
    by_y = sorted(pieces, key=lambda p: p.centroid[1])
    rows: list[list[RawPiece]] = []
    current_row: list[RawPiece] = []
    current_row_y = None

    for p in by_y:
        if current_row_y is None or abs(p.centroid[1] - current_row_y) <= row_band:
            current_row.append(p)
            # running average keeps the band anchored to the row, not the first piece
            current_row_y = sum(q.centroid[1] for q in current_row) / len(current_row)
        else:
            rows.append(current_row)
            current_row = [p]
            current_row_y = p.centroid[1]
    if current_row:
        rows.append(current_row)

    ordered: list[RawPiece] = []
    for row in rows:
        ordered.extend(sorted(row, key=lambda p: p.centroid[0]))
    return ordered
