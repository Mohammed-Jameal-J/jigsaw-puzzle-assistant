#!/usr/bin/env python3
"""
Generate a synthetic photo of ~1000 scattered jigsaw pieces for testing the
Phase 2 (piece detection), Phase 4 (border/corner), Phase 5 (edge
classification) and Phase 6 (rotation) pipeline without needing a real photo.

Design:
  - An assembled `rows` x `cols` grid defines each piece's TRUE edge kinds
    (flat on the outer boundary, random tab/hole elsewhere) and its TRUE
    classification (corner / border / interior).
  - Each piece is rendered as its own colored silhouette (with a subtle
    inner shadow to look photographed), then placed on a "table" background
    at a jittered-grid position with a random rotation — so pieces are
    scattered like a real photo but never overlap, keeping ground truth
    unambiguous.
  - A ground_truth.json is written alongside the image with each piece's
    true id, bbox, centroid, rotation, edges, and classification, so the
    detector's output can be scored directly instead of eyeballed.

Usage:
    python generate_synthetic_puzzle.py --out synthetic_puzzle_1000.jpg \
        --rows 25 --cols 40 --width 4000 --height 3000
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# Reuse the shared piece geometry from the backend so ground truth and the
# real detector/classifier agree on what a "tab" vs "hole" looks like.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.cv.piece_shapes import (  # noqa: E402
    EdgeKind,
    classification_for_flats,
    flat_edges_for_grid_position,
    generate_piece_polygon,
)

RNG_SEED_DEFAULT = 42

# Rotations we exercise heavily so Phase 6 has real 0/90/180/270 cases to
# detect, plus some arbitrary in-between angles for a realistic photo.
DISCRETE_ROTATIONS = [0, 90, 180, 270]

BACKGROUND_RGB = (55, 58, 52)  # "table" base color (before texture noise)
MIN_COLOR_DISTANCE_FROM_BG = 90.0  # a real piece on a table is never this close in color


def random_pastel_color(rng: random.Random) -> tuple[int, int, int]:
    """A random piece color, resampled if too close to the table color —
    otherwise the segmentation step has no contrast to detect it by, which
    isn't a detector bug, it's an unrealistic test case."""
    for _ in range(50):
        color = tuple(rng.randint(60, 220) for _ in range(3))
        dist = math.dist(color, BACKGROUND_RGB)
        if dist >= MIN_COLOR_DISTANCE_FROM_BG:
            return color  # type: ignore[return-value]
    return (220, 40, 40)  # fallback, practically unreachable


def build_piece_image(
    size_w: int,
    size_h: int,
    edges: dict[str, EdgeKind],
    color: tuple[int, int, int],
    margin: int,
) -> Image.Image:
    """Render one piece silhouette (RGBA) with the given edge shapes."""
    canvas_w = size_w + margin * 2
    canvas_h = size_h + margin * 2

    polygon = generate_piece_polygon(size_w, size_h, edges)
    polygon = polygon + np.array([margin, margin])  # shift into canvas

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pts = [tuple(p) for p in polygon]
    draw.polygon(pts, fill=(*color, 255), outline=(30, 30, 30, 255))

    # A soft inner shadow so pieces don't look like flat vector cutouts.
    shadow = Image.new("L", (canvas_w, canvas_h), 0)
    ImageDraw.Draw(shadow).polygon(pts, fill=255)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=max(2, size_w // 40)))
    shade = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 40))
    img = Image.composite(shade, img, shadow.point(lambda v: 255 - v))
    # re-apply the polygon mask so the shading doesn't leak outside the piece
    mask = Image.new("L", (canvas_w, canvas_h), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=255)
    img.putalpha(mask)
    return img


def generate_synthetic_puzzle(
    rows: int,
    cols: int,
    width: int,
    height: int,
    seed: int = RNG_SEED_DEFAULT,
    jitter_ratio: float = 0.05,
    rotation_mode: str = "mixed",  # "mixed" | "discrete" | "none"
) -> tuple[Image.Image, list[dict]]:
    rng = random.Random(seed)

    background = Image.new("RGB", (width, height), BACKGROUND_RGB)  # dark table
    # subtle table texture (low-freq noise) so it doesn't look like a flat fill
    noise = (np.random.default_rng(seed).normal(0, 6, (height, width, 1))).astype(np.int16)
    bg_arr = np.asarray(background, dtype=np.int16) + noise
    background = Image.fromarray(np.clip(bg_arr, 0, 255).astype(np.uint8))

    cell_w = width / cols
    cell_h = height / rows
    # base_size + margin*2, once rotated, must stay comfortably inside the
    # smaller cell dimension even after jitter shifts two neighbors toward
    # each other — otherwise adjacent pieces touch and merge into one blob
    # during detection. Kept conservative (0.46 / 0.16) rather than tuned to
    # the exact rotation range, so this holds for any --rotation-mode.
    base_size = min(cell_w, cell_h) * 0.46
    margin = int(base_size * 0.16)

    pieces_meta: list[dict] = []
    piece_num = 0

    for r in range(rows):
        for c in range(cols):
            piece_num += 1
            piece_id = f"P{piece_num:04d}"

            flats = flat_edges_for_grid_position(r, c, rows, cols)
            edges = {
                name: (EdgeKind.FLAT if is_flat else rng.choice([EdgeKind.TAB, EdgeKind.HOLE]))
                for name, is_flat in flats.items()
            }
            classification = classification_for_flats(flats)

            color = random_pastel_color(rng)
            piece_img = build_piece_image(int(base_size), int(base_size), edges, color, margin)

            if rotation_mode == "none":
                angle = 0
            elif rotation_mode == "discrete":
                angle = rng.choice(DISCRETE_ROTATIONS)
            else:  # mixed: mostly small realistic jitter, occasionally a hard rotation
                angle = rng.choice(DISCRETE_ROTATIONS) if rng.random() < 0.35 else rng.uniform(-8, 8)

            rotated = piece_img.rotate(-angle, expand=True, resample=Image.BICUBIC)

            cx = (c + 0.5) * cell_w + rng.uniform(-jitter_ratio, jitter_ratio) * cell_w
            cy = (r + 0.5) * cell_h + rng.uniform(-jitter_ratio, jitter_ratio) * cell_h
            paste_x = int(cx - rotated.width / 2)
            paste_y = int(cy - rotated.height / 2)

            background.paste(rotated, (paste_x, paste_y), rotated)

            bbox = (paste_x, paste_y, rotated.width, rotated.height)
            pieces_meta.append(
                {
                    "piece_id": piece_id,
                    "grid_row": r,
                    "grid_col": c,
                    "bbox": bbox,
                    "centroid": [cx, cy],
                    "rotation": angle % 360,
                    "edges": {k: v.value for k, v in edges.items()},
                    "classification": classification,
                    "color_rgb": color,
                }
            )

    return background, pieces_meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic scattered jigsaw puzzle photo.")
    parser.add_argument("--out", type=str, default="synthetic_puzzle_1000.jpg")
    parser.add_argument("--rows", type=int, default=25)
    parser.add_argument("--cols", type=int, default=40)
    parser.add_argument("--width", type=int, default=4000)
    parser.add_argument("--height", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=RNG_SEED_DEFAULT)
    parser.add_argument(
        "--rotation-mode", choices=["mixed", "discrete", "none"], default="mixed",
        help="mixed: realistic jitter + some hard 90/180/270 rotations (default); "
             "discrete: only 0/90/180/270; none: all pieces upright.",
    )
    args = parser.parse_args()

    img, pieces = generate_synthetic_puzzle(
        rows=args.rows, cols=args.cols, width=args.width, height=args.height,
        seed=args.seed, rotation_mode=args.rotation_mode,
    )

    out_path = Path(args.out)
    img.convert("RGB").save(out_path, quality=92)

    gt_path = out_path.with_name(out_path.stem + "_ground_truth.json")
    corners = sum(1 for p in pieces if p["classification"] == "corner")
    borders = sum(1 for p in pieces if p["classification"] == "border")
    interior = sum(1 for p in pieces if p["classification"] == "interior")
    gt_path.write_text(json.dumps({
        "image": str(out_path.name),
        "rows": args.rows,
        "cols": args.cols,
        "piece_count": len(pieces),
        "corner_count": corners,
        "border_count": borders,
        "interior_count": interior,
        "pieces": pieces,
    }, indent=2))

    print(f"Wrote {out_path} ({args.width}x{args.height}, {len(pieces)} pieces)")
    print(f"Wrote {gt_path}")
    print(f"Ground truth: {corners} corner, {borders} border, {interior} interior")


if __name__ == "__main__":
    main()
