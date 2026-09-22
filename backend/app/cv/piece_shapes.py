"""
Jigsaw piece geometry.

Builds a realistic piece silhouette (as a polygon) for a given set of 4 edge
kinds (flat / tab / hole). Used by:
  - scripts/generate_synthetic_puzzle.py  (Phase 1-2 test data)
  - app/services/edge_classifier.py       (Phase 4-5, later — shares the same
    "deviation from baseline" model so ground truth and detection agree)

Coordinate convention: local piece space, origin at the top-left of the
piece's base square, x right, y down (image convention). Bumps extend
OUTSIDE the base square (tabs) or INSIDE it (holes), so callers must leave
margin around the base square equal to at least `bump_height_ratio * size`.
"""
from __future__ import annotations

import math
from enum import Enum
from typing import NamedTuple

import numpy as np

DEFAULT_BUMP_WIDTH_RATIO = 0.36   # fraction of edge length occupied by the bump neck
DEFAULT_BUMP_HEIGHT_RATIO = 0.22  # bump protrusion/indentation depth, fraction of edge length
DEFAULT_SAMPLES = 14              # points used to approximate the bump curve


class EdgeKind(str, Enum):
    FLAT = "flat"
    TAB = "tab"
    HOLE = "hole"


class Point(NamedTuple):
    x: float
    y: float


def _edge_polyline(
    a: np.ndarray,
    b: np.ndarray,
    kind: EdgeKind,
    outward_normal: np.ndarray,
    bump_width_ratio: float,
    bump_height_ratio: float,
    samples: int,
) -> list[np.ndarray]:
    """Points from `a` up to (but excluding) `b` along one edge."""
    if kind == EdgeKind.FLAT:
        return [a]

    length = float(np.linalg.norm(b - a))
    neck_lo = (1.0 - bump_width_ratio) / 2.0
    neck_hi = 1.0 - neck_lo
    sign = 1.0 if kind == EdgeKind.TAB else -1.0
    height = bump_height_ratio * length

    pts = [a, a + (b - a) * neck_lo]
    for i in range(1, samples):
        t = neck_lo + (neck_hi - neck_lo) * i / samples
        base_pt = a + (b - a) * t
        local = (t - neck_lo) / (neck_hi - neck_lo)  # 0..1 across the bump
        offset = math.sin(math.pi * local) * height * sign
        pts.append(base_pt + outward_normal * offset)
    pts.append(a + (b - a) * neck_hi)
    return pts


def generate_piece_polygon(
    size_w: float,
    size_h: float,
    edges: dict[str, EdgeKind | str],
    bump_width_ratio: float = DEFAULT_BUMP_WIDTH_RATIO,
    bump_height_ratio: float = DEFAULT_BUMP_HEIGHT_RATIO,
    samples: int = DEFAULT_SAMPLES,
) -> np.ndarray:
    """
    Returns an (N, 2) float32 array of polygon points, local coordinates,
    tracing the piece outline clockwise starting at the top-left corner.

    `edges` keys: "top", "right", "bottom", "left" -> EdgeKind or matching str.
    """
    def kind_of(name: str) -> EdgeKind:
        v = edges[name]
        return v if isinstance(v, EdgeKind) else EdgeKind(v)

    tl = np.array([0.0, 0.0])
    tr = np.array([size_w, 0.0])
    br = np.array([size_w, size_h])
    bl = np.array([0.0, size_h])

    segments = [
        (tl, tr, kind_of("top"), np.array([0.0, -1.0])),
        (tr, br, kind_of("right"), np.array([1.0, 0.0])),
        (br, bl, kind_of("bottom"), np.array([0.0, 1.0])),
        (bl, tl, kind_of("left"), np.array([-1.0, 0.0])),
    ]

    points: list[np.ndarray] = []
    for a, b, kind, normal in segments:
        points.extend(
            _edge_polyline(a, b, kind, normal, bump_width_ratio, bump_height_ratio, samples)
        )
    return np.asarray(points, dtype=np.float32)


def flat_edges_for_grid_position(row: int, col: int, rows: int, cols: int) -> dict[str, bool]:
    """
    Which of the 4 edges are FLAT (outer boundary) for a piece at (row, col)
    in an `rows` x `cols` assembled grid. Matches Phase 4 definitions:
    corner = 2 flat edges, border = 1 flat edge, interior = 0 flat edges.
    """
    return {
        "top": row == 0,
        "left": col == 0,
        "right": col == cols - 1,
        "bottom": row == rows - 1,
    }


def classification_for_flats(flats: dict[str, bool]) -> str:
    n_flat = sum(flats.values())
    if n_flat >= 2:
        return "corner"
    if n_flat == 1:
        return "border"
    return "interior"
