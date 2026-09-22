"""
Phase 2 tests: piece detection must find (close to) the true piece count,
stay within the detection time budget, and produce sane per-piece geometry.
"""
from app.services.piece_detector import detect_pieces


def test_detects_most_pieces(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    true_count = len(small_synthetic_puzzle["ground_truth"])

    # Spec requirement: >95% success rate.
    assert result.piece_count >= true_count * 0.95
    assert result.piece_count <= true_count * 1.05  # also shouldn't over-detect


def test_detection_is_fast(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    # Spec requirement: <5s, even on a full-size 4000x3000 photo. This small
    # image should be far under that.
    assert result.processing_time_ms < 5000


def test_piece_ids_are_sequential_and_unique(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    ids = [p["piece_id"] for p in result.pieces]

    assert len(ids) == len(set(ids)), "piece IDs must be unique"
    assert ids == sorted(ids), "piece IDs must be assigned in sorted order (P0001, P0002, ...)"
    if ids:
        assert ids[0] == "P0001"


def test_piece_bboxes_are_within_image_bounds(small_synthetic_puzzle):
    import cv2

    img = cv2.imread(small_synthetic_puzzle["path"])
    h, w = img.shape[:2]

    result = detect_pieces(small_synthetic_puzzle["path"])
    for piece in result.pieces:
        x, y, pw, ph = piece["bbox"]
        assert x >= 0 and y >= 0
        assert x + pw <= w
        assert y + ph <= h
        assert pw > 0 and ph > 0
