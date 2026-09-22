"""
Phase 4 (border/corner classification) + Phase 5 (per-side tab/hole/flat)
tests, scored against the synthetic puzzle's known ground truth.

Edge labels ("top"/"right"/etc.) carry an inherent 90°-rotation ambiguity
relative to ground truth — see app/cv/rotation.py's module docstring — so
edge accuracy is scored via the best cyclic-shift match, per
conftest.best_cyclic_edge_match. Classification (corner/border/interior)
has no such ambiguity since it's just a count of flat sides.
"""
from app.services.piece_detector import detect_pieces
from tests.conftest import best_cyclic_edge_match, match_detected_to_ground_truth


def test_edge_classification_accuracy_exceeds_spec_target(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    matches = match_detected_to_ground_truth(result.pieces, small_synthetic_puzzle["ground_truth"])
    assert len(matches) > 90  # sanity: most of the 100 pieces should have matched

    total_edges = 0
    correct_edges = 0
    for gt_idx, detected in matches.items():
        true_edges = small_synthetic_puzzle["ground_truth"][gt_idx]["edges"]
        correct_edges += best_cyclic_edge_match(detected["edges"], true_edges)
        total_edges += 4

    accuracy = correct_edges / total_edges
    # Spec target: >80% (manual spot-check 10 random pieces). Measured
    # against the full ground truth here rather than a spot-check.
    assert accuracy > 0.80, f"edge classification accuracy {accuracy:.1%} below spec target"


def test_exactly_four_corners_detected(small_synthetic_puzzle):
    """
    A rectangular assembled puzzle always has exactly 4 corners — this is
    a hard requirement from the spec, and piece_detector.py now enforces
    it structurally (global top-4 ranking by per-edge flatness, rather
    than a per-piece threshold that can over/under-count independently
    per piece). See _apply_global_corner_selection's docstring.
    """
    result = detect_pieces(small_synthetic_puzzle["path"])
    detected_corners = sum(1 for p in result.pieces if p["classification"] == "corner")
    assert detected_corners == 4


def test_border_count_in_reasonable_range(small_synthetic_puzzle):
    result = detect_pieces(small_synthetic_puzzle["path"])
    gt = small_synthetic_puzzle["ground_truth"]

    true_border = sum(1 for p in gt if p["classification"] == "border")
    detected_border = sum(1 for p in result.pieces if p["classification"] == "border")
    # Border classification is still plain per-edge thresholding (no
    # structural constraint like corners have), so allow some slack.
    assert 0.6 * true_border < detected_border < 1.5 * true_border
