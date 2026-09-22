"""Phase 1: upload validation and persistence to the file-based store."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from fastapi import UploadFile

from app.core.config import settings


class UploadValidationError(ValueError):
    pass


async def validate_and_read_upload(file: UploadFile) -> bytes:
    if file.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise UploadValidationError(
            f"Unsupported content type '{file.content_type}'. "
            f"Allowed: {sorted(settings.ALLOWED_CONTENT_TYPES)}"
        )

    data = await file.read()
    if len(data) == 0:
        raise UploadValidationError("Uploaded file is empty.")
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        mb = settings.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)
        raise UploadValidationError(f"File too large. Max size is {mb:.0f} MB.")
    return data


def decode_and_validate_image(data: bytes) -> tuple[np.ndarray, int, int]:
    """Decode bytes to a BGR image and sanity-check its dimensions."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise UploadValidationError("Could not decode image — file may be corrupt or not a real image.")

    h, w = img.shape[:2]
    if min(h, w) < settings.MIN_IMAGE_DIM:
        raise UploadValidationError(
            f"Image too small ({w}x{h}). Minimum dimension is {settings.MIN_IMAGE_DIM}px."
        )
    return img, w, h


def save_original_image(img_bgr: np.ndarray, puzzle_dir: Path) -> Path:
    path = puzzle_dir / "original.jpg"
    ok = cv2.imwrite(str(path), img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    if not ok:
        raise IOError(f"Failed to write image to {path}")
    return path
