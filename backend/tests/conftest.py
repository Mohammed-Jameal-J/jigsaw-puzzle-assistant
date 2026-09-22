"""Shared fixtures for backend tests."""
import sys
from pathlib import Path

import numpy as np
import pytest

# tests/ -> backend/ -> project root -> scripts/
SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from generate_synthetic_puzzle import generate_synthetic_puzzle  # noqa: E402


@pytest.fixture(scope="session")
def small_synthetic_puzzle(tmp_path_factory):
    """
    A small (10x10 = 100 piece) synthetic puzzle, generated once per test
    session — big enough to exercise real detection logic, small enough
    that the test suite stays fast.
    """
    tmp_dir = tmp_path_factory.mktemp("synthetic")
    img, pieces = generate_synthetic_puzzle(
        rows=10, cols=10, width=1000, height=800, seed=7, rotation_mode="mixed"
    )
    path = tmp_dir / "small_puzzle.jpg"
    img.convert("RGB").save(path, quality=92)
    return {"path": str(path), "ground_truth": pieces, "rows": 10, "cols": 10}


def match_detected_to_ground_truth(detected_pieces: list[dict], ground_truth: list[dict], max_dist: float = 30.0) -> dict[int, dict]:
    """
    Maps ground-truth index -> nearest detected piece by centroid distance.
    Detection order doesn't line up with generation order (pieces are
    sorted row-major after detection), so tests match by position instead.
    """
    gt_centroids = np.array([p["centroid"] for p in ground_truth])
    matches: dict[int, dict] = {}
    for detected in detected_pieces:
        dc = np.array(detected["centroid"])
        dists = np.linalg.norm(gt_centroids - dc, axis=1)
        idx = int(np.argmin(dists))
        if dists[idx] < max_dist:
            matches[idx] = detected
    return matches


def best_cyclic_edge_match(predicted_edges: dict, true_edges: dict) -> int:
    """
    Counts correct edge labels (top/right/bottom/left) at whichever 0/90/
    180/270 cyclic rotation of the labels scores highest — the piece's
    own square symmetry means our detector and the generator can agree on
    the *pattern* of tab/hole/flat while disagreeing on which side is
    labeled "top", and that's an inherent ambiguity, not an error.
    """
    labels = ["top", "right", "bottom", "left"]
    return max(
        sum(1 for i in range(4) if predicted_edges[labels[i]] == true_edges[labels[(i + shift) % 4]])
        for shift in range(4)
    )

