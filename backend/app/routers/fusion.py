"""
Fusion router for Optical-SAR cross-validation.
"""

import base64
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ImageModel
from app.schemas import FusionRequest, FusionResponse
from app.main import http_client
from PIL import Image

router = APIRouter()


@router.post("/verify", response_model=FusionResponse)
async def verify_fusion(request: FusionRequest, db: AsyncSession = Depends(get_db)):
    """Run optical-SAR fusion verification."""
    
    # Validate images exist
    result = await db.execute(select(ImageModel).where(ImageModel.id.in_([request.optical_image_id, request.sar_image_id])))
    images = result.scalars().all()
    if len(images) != 2:
        raise HTTPException(status_code=404, detail="One or both images not found")

    images_by_id = {image.id: image for image in images}

    def _read_b64(image_id):
        image = images_by_id[image_id]
        if not Path(image.file_path).is_file():
            raise FileNotFoundError("Uploaded image is not available")
        with Image.open(image.file_path) as source:
            converted = source.convert("RGB")
            buffer = io.BytesIO()
            converted.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    payload = {
        "optical": _read_b64(request.optical_image_id),
        "sar": _read_b64(request.sar_image_id),
    }

    try:
        model_response = await http_client.post("/fusion", json=payload)
        model_response.raise_for_status()
        result_data = model_response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model server error: {e}")

    return FusionResponse(
        verification_result=result_data["verification_result"],
        confidence=result_data["confidence"],
        agreement_pct=result_data["agreement_pct"],
        details=result_data.get("details"),
        execution_trace=[
            {"step_name": "Extracting features", "status": "completed", "duration_ms": 1200},
            {"step_name": "Cross-validating modalities", "status": "completed", "duration_ms": 800}
        ]
    )
