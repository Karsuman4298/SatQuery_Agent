"""Pure GIS/raster calculations. These functions do not call an LLM."""

from __future__ import annotations

import math
from typing import Any

import numpy as np


def area_from_mask(mask: np.ndarray, transform: Any = None) -> float:
    """Return area in square metres for true/non-zero mask pixels."""
    pixel_area = 1.0
    if transform is not None:
        pixel_area = abs(transform.a * transform.e - transform.b * transform.d)
    return float(np.count_nonzero(mask) * pixel_area)


def percent_change(before: np.ndarray, after: np.ndarray) -> float:
    """Return the percentage of pixels whose values differ."""
    if before.shape != after.shape:
        raise ValueError("before and after arrays must have the same shape")
    changed = np.asarray(before) != np.asarray(after)
    return float(np.count_nonzero(changed) / changed.size * 100.0) if changed.size else 0.0


def pixel_to_latlon(x: float, y: float, transform: Any) -> tuple[float, float]:
    """Convert a pixel coordinate to map x/y using a raster transform."""
    map_x, map_y = transform * (x + 0.5, y + 0.5)
    return float(map_x), float(map_y)


def bbox_to_geojson(bbox: dict[str, float], transform: Any) -> dict:
    """Convert a pixel bbox to a polygon in the raster coordinate system."""
    points = [
        pixel_to_latlon(bbox["x_min"], bbox["y_min"], transform),
        pixel_to_latlon(bbox["x_max"], bbox["y_min"], transform),
        pixel_to_latlon(bbox["x_max"], bbox["y_max"], transform),
        pixel_to_latlon(bbox["x_min"], bbox["y_max"], transform),
    ]
    return {"type": "Polygon", "coordinates": [[[*point] for point in points + [points[0]]]]}


def blur_score(image: np.ndarray) -> float:
    """Estimate sharpness using variance of a small discrete Laplacian."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim == 3:
        values = values.mean(axis=0)
    laplacian = (
        -4 * values
        + np.roll(values, 1, axis=0)
        + np.roll(values, -1, axis=0)
        + np.roll(values, 1, axis=1)
        + np.roll(values, -1, axis=1)
    )
    return float(np.var(laplacian))


def cloud_cover_percent(image: np.ndarray) -> float | None:
    """Return a conservative bright/low-information pixel percentage."""
    values = np.asarray(image, dtype=np.float32)
    if values.ndim != 3 or values.shape[0] < 3:
        return None
    finite = np.nan_to_num(values[:3], nan=0.0)
    brightness = finite.mean(axis=0)
    valid = finite.max(axis=0) > 0
    if not np.any(valid):
        return None
    threshold = np.percentile(brightness[valid], 95)
    return float(np.mean((brightness >= threshold) & valid) * 100.0)


def structural_agreement(optical: np.ndarray, sar: np.ndarray) -> float:
    """Compare normalized edge-like gradients between two aligned arrays."""
    a = np.asarray(optical, dtype=np.float32).mean(axis=0) if optical.ndim == 3 else np.asarray(optical, dtype=np.float32)
    b = np.asarray(sar, dtype=np.float32).mean(axis=0) if sar.ndim == 3 else np.asarray(sar, dtype=np.float32)
    if a.shape != b.shape:
        raise ValueError("optical and SAR arrays must have the same shape")
    grad_a = np.hypot(np.gradient(a, axis=0), np.gradient(a, axis=1)).ravel()
    grad_b = np.hypot(np.gradient(b, axis=0), np.gradient(b, axis=1)).ravel()
    if np.std(grad_a) == 0 or np.std(grad_b) == 0:
        return 0.0
    correlation = float(np.corrcoef(grad_a, grad_b)[0, 1])
    return max(0.0, min(1.0, (correlation + 1.0) / 2.0))
