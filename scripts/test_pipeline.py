#!/usr/bin/env python3
"""
Integration smoke test for the detection pipeline: generates a synthetic
puzzle (or reuses one you point it at), runs Phase 2/3 detection, and
reports against the spec's hard requirements.

Usage:
    python scripts/test_pipeline.py
    python scripts/test_pipeline.py --image path/to/photo.jpg --ground-truth path/to/gt.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from app.services.piece_detector import detect_pieces  # noqa: E402
from generate_synthetic_puzzle import generate_synthetic_puzzle  # noqa: E402


def report(label: str, passed: bool, detail: str) -> bool:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {label}: {detail}")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the detection pipeline against a test puzzle.")
    parser.add_argument("--image", type=str, default=None, help="Existing puzzle photo to test. Generates one if omitted.")
    parser.add_argument("--ground-truth", type=str, default=None, help="Ground truth JSON matching --image.")
    parser.add_argument("--rows", type=int, default=25)
    parser.add_argument("--cols", type=int, default=40)
    args = parser.parse_args()

    all_passed = True

    if args.image:
        image_path = Path(args.image)
        gt_pieces = json.loads(Path(args.ground_truth).read_text())["pieces"] if args.ground_truth else None
    else:
        print(f"Generating a {args.rows}x{args.cols} synthetic puzzle...")
        img, gt_pieces = generate_synthetic_puzzle(rows=args.rows, cols=args.cols, width=4000, height=3000, seed=42)
        image_path = PROJECT_ROOT / "uploads" / "pipeline_test.jpg"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        img.convert("RGB").save(image_path, quality=92)

    true_count = len(gt_pieces) if gt_pieces else None

    print(f"\nRunning detection on {image_path} ...")
    t0 = time.perf_counter()
    result = detect_pieces(str(image_path))
    wall_ms = (time.perf_counter() - t0) * 1000

    print(f"\nResults: {result.piece_count} pieces detected in {result.processing_time_ms:.0f}ms "
          f"(wall clock {wall_ms:.0f}ms)\n")

    all_passed &= report(
        "Detection time < 5s",
        result.processing_time_ms < 5000,
        f"{result.processing_time_ms:.0f}ms",
    )

    if true_count:
        success_rate = result.piece_count / true_count
        all_passed &= report(
            "Success rate > 95%",
            success_rate > 0.95,
            f"{result.piece_count}/{true_count} = {success_rate:.1%}",
        )
    else:
        print(f"  [SKIP] Success rate: no ground truth available for {image_path}")

    print()
    if all_passed:
        print("All checks passed.")
    else:
        print("Some checks failed — see above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
