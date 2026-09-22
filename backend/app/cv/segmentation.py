"""
Phase 2 segmentation: separate puzzle pieces from the table background, then
find and filter their contours.

Approach: the background (table) is assumed roughly uniform in color (a mat,
tablecloth, or desk) with pieces visibly different in color/brightness on
top of it — the standard setup for photographing scattered puzzle pieces.
We estimate the background color from the image border, threshold on color
distance from it (Otsu-adaptive so it survives different lighting/table
colors), then clean the mask morphologically before contour extraction.
"""
from __future__ import annotations

import cv2
import numpy as np


def estimate_background_color(img_bgr: np.ndarray, border_ratio: float = 0.02) -> np.ndarray:
    """Median color of a thin frame around the image edge, assumed background."""
    h, w = img_bgr.shape[:2]
    bh, bw = max(1, int(h * border_ratio)), max(1, int(w * border_ratio))
    strips = [
        img_bgr[:bh, :, :].reshape(-1, 3),
        img_bgr[-bh:, :, :].reshape(-1, 3),
        img_bgr[:, :bw, :].reshape(-1, 3),
        img_bgr[:, -bw:, :].reshape(-1, 3),
    ]
    samples = np.concatenate(strips, axis=0)
    return np.median(samples, axis=0)


def foreground_mask(img_bgr: np.ndarray, bg_color: np.ndarray) -> np.ndarray:
    """
    Binary mask (uint8, 0/255) of pixels that differ from the background
    color beyond an Otsu-derived threshold on the per-pixel color distance.
    """
    diff = np.linalg.norm(img_bgr.astype(np.float32) - bg_color.astype(np.float32), axis=2)
    diff_u8 = np.clip(diff, 0, 255).astype(np.uint8)
    # Otsu picks the threshold adaptively so this survives different table
    # colors/lighting without hand-tuned constants.
    _, mask = cv2.threshold(diff_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return mask


def find_piece_contours(mask: np.ndarray) -> list[np.ndarray]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return list(contours)


def filter_contours_by_area(
    contours: list[np.ndarray], min_area: float, max_area: float
) -> list[np.ndarray]:
    return [c for c in contours if min_area <= cv2.contourArea(c) <= max_area]


def draw_contours_overlay(img_bgr: np.ndarray, contours: list[np.ndarray]) -> np.ndarray:
    overlay = img_bgr.copy()
    cv2.drawContours(overlay, contours, -1, (0, 255, 0), 2)
    return overlay
