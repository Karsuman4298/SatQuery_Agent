"""SAM2 segmentation endpoint."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class SegmentRequest(BaseModel):
    image: str  # base64-encoded image
    point: list[int]  # [x, y] click point


class SegmentResponse(BaseModel):
    mask: str  # base64-encoded mask


@router.post("/segment", response_model=SegmentResponse)
async def segment_image(request: SegmentRequest):
    """Fail explicitly until a real SAM2 checkpoint is configured."""
    raise HTTPException(status_code=503, detail="Segmentation model is not configured")

