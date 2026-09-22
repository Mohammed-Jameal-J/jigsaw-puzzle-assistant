"""
Phase 6 (rotation detection) tests.

A solid-color square piece with no printed image has 4-fold rotational
symmetry, so we can't recover an absolute "original top" — see
app/cv/rotation.py's module docstring. What IS testable: pieces placed
upright (rotation_mode="none") should be detected as axis-aligned (their
core's orientation should sit close to a multiple of 90°), and the core
extraction should succeed for the large majority of pieces.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from generate_synthetic_puzzle import generate_synthetic_puzzle  # noqa: E402

from app.cv.rotation import extract_core_shape, rotation_from_core
from app.services.piece_detector import detect_pieces


def test_core_extraction_succeeds_for_most_pieces(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    # Every detected piece's rotation should be a real estimate (0.5
    # confidence is the "core extraction failed" signal from _to_api_piece).
    with_core = sum(1 for p in result.pieces if p["confidence"] > 0.5)
    assert with_core / len(result.pieces) > 0.90


def test_upright_pieces_are_detected_as_axis_aligned(tmp_path):
    img, pieces = generate_synthetic_puzzle(
        rows=6, cols=6, width=700, height=700, seed=3, rotation_mode="none"
    )
    path = tmp_path / "upright.jpg"
    img.convert("RGB").save(path, quality=92)

    result = detect_pieces(str(path))

    # rotation_from_core reports an angle relative to the image's +x axis;
    # for an unrotated piece that should land near a multiple of 90°.
    near_multiple_of_90 = 0
    for piece in result.pieces:
        remainder = piece["rotation"] % 90
        distance_to_nearest_multiple = min(remainder, 90 - remainder)
        if distance_to_nearest_multiple < 12:  # degrees of tolerance
            near_multiple_of_90 += 1

    assert near_multiple_of_90 / len(result.pieces) > 0.85
