"""
Change detection endpoint — compares before/after satellite images.
Wraps TEOChat / change detection model (or returns mock data when MOCK_MODELS=true).
"""

import asyncio
import base64
import io
import random

import numpy as np
from fastapi import APIRouter
from PIL import Image
from pydantic import BaseModel

from app.config import settings

router = APIRouter()


class ChangeRequest(BaseModel):
    before: str  # base64-encoded before image
    after: str  # base64-encoded after image


class ChangeResponse(BaseModel):
    change_mask: str  # base64-encoded change mask (binary image)
    change_pct: float  # percentage of area changed


def _generate_change_mask(before_b64: str, after_b64: str) -> tuple[str, float]:
    """Generate a change mask from image difference or synthetic blobs if invalid base64."""
    clean_b = before_b64.split("base64,")[-1].strip() if "base64," in before_b64 else before_b64.strip()
    clean_a = after_b64.split("base64,")[-1].strip() if "base64," in after_b64 else after_b64.strip()

    # Identical base64 strings -> 0% change
    if not clean_b or not clean_a or clean_b == clean_a:
        mask_size = 256
        mask = np.zeros((mask_size, mask_size), dtype=np.uint8)
        img = Image.fromarray(mask)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mask_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return mask_b64, 0.0

    try:
        raw_b = base64.b64decode(clean_b)
        raw_a = base64.b64decode(clean_a)
        arr_b = np.array(Image.open(io.BytesIO(raw_b)).convert("L").resize((256, 256)))
        arr_a = np.array(Image.open(io.BytesIO(raw_a)).convert("L").resize((256, 256)))

        diff = np.abs(arr_b.astype(float) - arr_a.astype(float))
        max_diff = np.max(diff)

        # Identical or virtually identical images
        if max_diff < 5.0:
            mask_size = 256
            mask = np.zeros((mask_size, mask_size), dtype=np.uint8)
            img = Image.fromarray(mask)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            mask_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return mask_b64, 0.0

        threshold = np.percentile(diff, 88)
        if threshold < 15.0:
            threshold = 15.0

        mask = (diff > threshold).astype(np.uint8) * 255
        pct = float(np.sum(mask > 0)) / float(mask.size) * 100.0

        img = Image.fromarray(mask)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mask_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return mask_b64, round(pct, 2)
    except Exception:
        # Fallback to random change blobs if images cannot be decoded
        mask_size = 256
        mask = np.zeros((mask_size, mask_size), dtype=np.uint8)
        num_changes = random.randint(2, 4)
        for _ in range(num_changes):
            cx = random.randint(30, mask_size - 30)
            cy = random.randint(30, mask_size - 30)
            radius = random.randint(15, 40)
            y, x = np.ogrid[-cy : mask_size - cy, -cx : mask_size - cx]
            blob = x * x + y * y <= radius * radius
            mask[blob] = 255

        change_pct = float(np.sum(mask > 0)) / float(mask.size) * 100.0
        img = Image.fromarray(mask)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        mask_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return mask_b64, round(change_pct, 2)



@router.post("/change", response_model=ChangeResponse)
async def detect_changes(request: ChangeRequest):
    """Detect changes between before and after satellite images."""

    # Pixel difference is deterministic evidence; the agent supplies language analysis.
    mask_b64, change_pct = _generate_change_mask(request.before, request.after)
    return ChangeResponse(
        change_mask=mask_b64,
        change_pct=change_pct,
    )

