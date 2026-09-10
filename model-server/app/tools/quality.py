"""Deterministic image validation and quality assessment."""

from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from app.tools.gis import blur_score, cloud_cover_percent


def clean_base64(value: str) -> str:
    return value.split(",", 1)[1] if value.startswith("data:") and "," in value else value


def decode_image(value: str) -> np.ndarray:
    """Decode a model data URI into channels-first float32 pixels."""
    raw = base64.b64decode(clean_base64(value))
    with Image.open(io.BytesIO(raw)) as image:
        array = np.asarray(image.convert("RGB"), dtype=np.float32)
    return np.transpose(array, (2, 0, 1))


def assess_image(value: str) -> dict:
    """Return deterministic quality metrics and a usable flag."""
    try:
        pixels = decode_image(value)
        finite = np.isfinite(pixels)
        nonzero = np.count_nonzero(pixels)
        usable = bool(finite.all() and pixels.size > 0 and nonzero > 0)
        issues: list[str] = []
        if not usable:
            issues.append("Image is empty, non-finite, or contains no non-zero pixels")
        if pixels.shape[1] < 32 or pixels.shape[2] < 32:
            issues.append("Image resolution is too small for reliable scene interpretation")
        return {
            "usable": usable,
            "blur_score": blur_score(pixels),
            "cloud_cover_pct": cloud_cover_percent(pixels),
            "issues": issues,
            "shape": list(pixels.shape),
        }
    except Exception as exc:
        return {"usable": False, "issues": [f"Image decode failed: {exc}"]}
