"""
Phase 2 preprocessing: RGB -> HSV, CLAHE lighting correction, morphological
cleanup. Kept as small, independently-testable functions per the "Every
feature must be testable" rule in the project spec.
"""
from __future__ import annotations

import cv2
import numpy as np


def load_image_bgr(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image at {path}")
    return img


def resize_max_dim(img: np.ndarray, max_dim: int) -> tuple[np.ndarray, float]:
    """Downscale so the longer side is `max_dim`, if larger. Returns (img, scale)."""
    h, w = img.shape[:2]
    longer = max(h, w)
    if longer <= max_dim:
        return img, 1.0
    scale = max_dim / longer
    resized = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def to_hsv(img_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)


def apply_clahe_to_value_channel(hsv: np.ndarray, clip_limit: float = 2.0, tile_grid: int = 8) -> np.ndarray:
    """
    CLAHE (Contrast Limited Adaptive Histogram Equalization) on the V channel
    corrects uneven lighting (shadows/hotspots) across a photographed table
    before we threshold for the background.
    """
    h, s, v = cv2.split(hsv)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    v_eq = clahe.apply(v)
    return cv2.merge([h, s, v_eq])


def morphological_clean(mask: np.ndarray, open_kernel: int = 5, close_kernel: int = 9) -> np.ndarray:
    """Open (remove speckle noise) then close (fill small holes) a binary mask."""
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel, open_kernel))
    close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel, close_kernel))
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_k)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, close_k)
    return closed
