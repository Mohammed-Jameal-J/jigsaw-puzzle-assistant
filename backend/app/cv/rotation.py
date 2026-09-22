"""
Phase 6: rotation / orientation detection.

Finding a piece's true square "core" (stripped of tabs/holes) turned out
to be much more reliable via direct contour simplification than via
morphological open/close: at the pixel scale a single puzzle piece occupies
(tens of pixels), a closing/opening kernel wide enough to bridge a bump's
neck also distorts the piece's actual corners, and — less obviously —
even a generously-sized kernel doesn't fully re-flatten a rounded notch at
this scale because of plain pixel discretization (verified empirically;
this isn't a tuning slip, closing a small semicircular notch with a much
larger kernel still only partially fills it).

The corners of the underlying square stay genuinely sharp in the RAW
contour, though — only the tab/hole bumps are smooth, and they sit in the
middle portion of each side, not at the corners. So cv2.approxPolyDP with
an epsilon comfortably larger than the bump's peak deviation collapses
each bump back onto its straight edge while leaving the 4 real corners
standing, with no morphology needed at all.

Note on ambiguity: a square has 4-fold rotational symmetry, and these
pieces carry no printed image to break that symmetry, so "rotation" here
means orientation modulo 90°, not a recovery of some absolute original
top. That's inherent to the problem, not a bug — Phase 7+ (actual
matching, out of scope) is what would eventually resolve which of the 4
equivalent orientations is "correct" relative to neighboring pieces.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Multiples of the piece's shorter bbox side, tried in order until exactly
# 4 corners come out. The generator's bump depth is ~0.22x a side's length,
# and approxPolyDP only drops a bump's peak once epsilon exceeds that peak's
# deviation from the straight edge — so these start comfortably above 0.22.
EPSILON_MULTIPLIERS = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.35, 0.30]


@dataclass
class CoreShape:
    corners: np.ndarray       # (4, 2) float32, polygon order, LOCAL to the crop
    center: np.ndarray        # (2,) float32, LOCAL to the crop
    offset: np.ndarray        # (2,) the crop's top-left, to map back to caller's coords


def extract_core_shape(contour: np.ndarray) -> CoreShape | None:
    """
    Approximates a piece's plain square core as a 4-point polygon by
    simplifying its raw contour until the tab/hole bumps collapse but the
    corners survive. Returns None if the contour is too small/degenerate,
    or no epsilon in EPSILON_MULTIPLIERS yields a clean quadrilateral (in
    which case the minimal rotated rect is used as a last-resort fallback).
    """
    x, y, bw, bh = cv2.boundingRect(contour)
    side_estimate = min(bw, bh)
    if side_estimate < 8:
        return None

    offset = np.array([x, y], dtype=np.float32)
    local_contour = contour.reshape(-1, 2).astype(np.float32) - offset

    for mult in EPSILON_MULTIPLIERS:
        approx = cv2.approxPolyDP(local_contour, mult * side_estimate, True).reshape(-1, 2)
        if len(approx) == 4:
            corners = approx.astype(np.float32)
            break
    else:
        # Nothing gave exactly 4 — fall back to the minimal rotated rect,
        # which always returns 4 points at the cost of being a looser fit.
        rect = cv2.minAreaRect(local_contour)
        corners = cv2.boxPoints(rect).astype(np.float32)

    center = corners.mean(axis=0)
    return CoreShape(corners=corners, center=center, offset=offset)


def order_corners_clockwise(corners: np.ndarray) -> np.ndarray:
    """Sorts 4 points into clockwise order (image coords, y-down) starting from whichever comes first in angle."""
    center = corners.mean(axis=0)
    angles = np.arctan2(corners[:, 1] - center[1], corners[:, 0] - center[0])
    order = np.argsort(angles)
    return corners[order]


def rotation_from_core(core: CoreShape) -> float:
    """
    Degrees (0-360) describing the current orientation of the piece's
    first (clockwise) side relative to the image's +x axis. Meaningful as
    a consistent per-piece orientation estimate; see the module docstring
    for the mod-90 ambiguity this carries.
    """
    corners = order_corners_clockwise(core.corners)
    edge_vec = corners[1] - corners[0]
    angle = np.degrees(np.arctan2(edge_vec[1], edge_vec[0]))
    return float(angle % 360)
