"""
Phase 5: classify each of a piece's 4 sides as TAB / HOLE / FLAT.
Phase 4: corner/border/interior mostly falls out of that (count the flat
sides), EXCEPT corner detection also uses a global ranking pass — see
piece_detector.select_corners_globally for why.

Method: take the piece's core square (app/cv/rotation.py has already
stripped the tabs/holes off to find it), walk its 4 sides in order, and
for each side measure how far the ORIGINAL (undecorated) contour deviates
from that side's baseline in the middle portion of the side — a bump
outward past a threshold is a tab, a dent inward past the threshold is a
hole, and staying near the baseline is flat.

Calibration note: measured against ground truth, a HOLE's indentation
consistently reads shallower than a TAB's protrusion of the same true
depth (~0.151 vs ~0.218 of the side length, for bumps generated at 0.22) —
likely JPEG/anti-aliasing softening concave regions more than convex ones
at this pixel scale. HOLE_DEPTH_CORRECTION compensates for that measured
bias; it's tuned to this generator/pipeline's current settings and may
need recalibrating against a different image source.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.cv.rotation import CoreShape, order_corners_clockwise

SIDE_LABELS = ["top", "right", "bottom", "left"]
BUMP_THRESHOLD_RATIO = 0.08   # fraction of side length; generator's bumps are ~0.22, comfortable margin
CENTER_BAND_RATIO = 0.35      # only look at the middle of each side, corners are noisy
HOLE_DEPTH_CORRECTION = 1.45  # compensates hole indentations reading ~31% shallow; see module docstring


@dataclass
class EdgeClassification:
    edges: dict = field(default_factory=dict)            # "top"/"right"/"bottom"/"left" -> tab/hole/flat
    edge_deviation: dict = field(default_factory=dict)    # same keys -> normalized |deviation| (0 = perfectly flat)
    classification: str = "unknown"                       # corner / border / interior (pre-global-ranking)
    rotation: float = 0.0                                 # degrees; which corner order was picked as "top"


def _pick_top_index(corners_cw: np.ndarray) -> int:
    """Index of the corner whose following side's midpoint sits highest (smallest y) in the image."""
    n = len(corners_cw)
    mids = [(corners_cw[i] + corners_cw[(i + 1) % n]) / 2 for i in range(n)]
    return int(np.argmin([m[1] for m in mids]))  # smallest y = topmost


def classify_piece(contour: np.ndarray, core: CoreShape) -> EdgeClassification:
    corners = order_corners_clockwise(core.corners)
    if len(corners) != 4:
        return EdgeClassification()  # degenerate core; leave as unknown rather than guess

    top_idx = _pick_top_index(corners)
    corners = np.roll(corners, -top_idx, axis=0)  # rotate array so side 0 is "top"

    contour_pts = contour.reshape(-1, 2).astype(np.float32) - core.offset

    edges: dict = {}
    edge_deviation: dict = {}
    for i, label in enumerate(SIDE_LABELS):
        a, b = corners[i], corners[(i + 1) % 4]
        side_vec = b - a
        side_len = float(np.linalg.norm(side_vec))
        if side_len < 1e-3:
            edges[label] = "unknown"
            edge_deviation[label] = 1.0
            continue
        tangent = side_vec / side_len
        normal = np.array([tangent[1], -tangent[0]])  # perpendicular; flip if it points inward

        mid = (a + b) / 2
        # Outward normal should point away from the core's center.
        if np.dot(normal, mid - core.center) < 0:
            normal = -normal

        rel = contour_pts - mid
        local_t = rel @ tangent
        local_n = rel @ normal

        band = (np.abs(local_t) < (CENTER_BAND_RATIO * side_len)) & (np.abs(local_n) < 0.32 * side_len)
        if not np.any(band):
            edges[label] = "flat"
            edge_deviation[label] = 0.0
            continue

        band_n = local_n[band]
        max_n = float(band_n.max())
        min_n = float(band_n.min()) * HOLE_DEPTH_CORRECTION  # compensate the measured hole-depth bias
        threshold = BUMP_THRESHOLD_RATIO * side_len

        if max_n > threshold:
            edges[label] = "tab"
        elif min_n < -threshold:
            edges[label] = "hole"
        else:
            edges[label] = "flat"

        edge_deviation[label] = max(abs(max_n), abs(min_n)) / side_len

    flat_count = sum(1 for v in edges.values() if v == "flat")
    if flat_count >= 2:
        classification = "corner"
    elif flat_count == 1:
        classification = "border"
    else:
        classification = "interior"

    top_edge_vec = corners[1] - corners[0]
    rotation = float(np.degrees(np.arctan2(top_edge_vec[1], top_edge_vec[0])) % 360)

    return EdgeClassification(
        edges=edges, edge_deviation=edge_deviation, classification=classification, rotation=rotation
    )
