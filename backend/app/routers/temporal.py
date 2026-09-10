"""
Temporal router for change detection and impact analysis.
"""

import uuid
import base64
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from PIL import Image

from app.config import settings
from app.database import get_db
from app.models import ImageModel, ChangeResultModel, ImpactStatsModel
from app.schemas import TemporalRequest, ChangeResultResponse, ImpactStats

router = APIRouter()


async def run_change_detection(change_id: uuid.UUID, db: AsyncSession):
    """Background task to run change detection and compute impact stats."""
    try:
        result = await db.execute(select(ChangeResultModel).where(ChangeResultModel.id == change_id))
        change = result.scalar_one_or_none()
        if not change:
            return

        change.status = "processing"
        await db.commit()

        # Fetch before and after image models
        b_res = await db.execute(select(ImageModel).where(ImageModel.id == change.before_image_id))
        before_img = b_res.scalar_one_or_none()
        a_res = await db.execute(select(ImageModel).where(ImageModel.id == change.after_image_id))
        after_img = a_res.scalar_one_or_none()

        def _read_b64(img_model: ImageModel | None) -> str:
            if not img_model or not Path(img_model.file_path).is_file():
                raise FileNotFoundError("Uploaded image is not available")
            with Image.open(img_model.file_path) as source:
                converted = source.convert("RGB")
                buffer = io.BytesIO()
                converted.save(buffer, format="PNG")
            return base64.b64encode(buffer.getvalue()).decode("ascii")

        b64_before = _read_b64(before_img)
        b64_after = _read_b64(after_img)

        # If identical image IDs passed
        if change.before_image_id == change.after_image_id:
            b64_after = b64_before

        payload = {
            "before": b64_before,
            "after": b64_after,
        }

        async with httpx.AsyncClient(base_url=settings.model_server_url, timeout=60.0) as client:
            resp = await client.post("/change", json=payload)
            resp.raise_for_status()
            model_data = resp.json()

        change_pct = model_data.get("change_pct", 0.0)

        # Update change result
        change.change_mask_url = f"data:image/png;base64,{model_data['change_mask']}"
        change.change_pct = change_pct
        change.status = "completed"
        import datetime
        change.completed_at = datetime.datetime.utcnow()

        await db.commit()


    except Exception as e:
        # Re-fetch change to avoid stale state issues, but we'll keep it simple here
        result = await db.execute(select(ChangeResultModel).where(ChangeResultModel.id == change_id))
        change = result.scalar_one_or_none()
        if change:
            change.status = "failed"
            change.error_message = str(e)
            await db.commit()


@router.post("/", response_model=ChangeResultResponse, status_code=202)
async def submit_temporal(
    request: TemporalRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Submit a pair of images for temporal change detection."""
    
    # Check if a pending/completed job already exists for this pair
    result = await db.execute(
        select(ChangeResultModel)
        .where(ChangeResultModel.before_image_id == request.before_image_id)
        .where(ChangeResultModel.after_image_id == request.after_image_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # Instead of failing, just return the existing job (idempotent)
        return _format_change_response(existing, None)

    # Validate images exist
    result = await db.execute(select(ImageModel).where(ImageModel.id.in_([request.before_image_id, request.after_image_id])))
    images = result.scalars().all()
    if len(images) != 2:
        raise HTTPException(status_code=404, detail="One or both images not found")

    change = ChangeResultModel(
        before_image_id=request.before_image_id,
        after_image_id=request.after_image_id,
        status="pending"
    )
    db.add(change)
    await db.flush() # get ID
    
    # Fire off background task
    background_tasks.add_task(run_change_detection, change.id, db)
    await db.commit()
    await db.refresh(change)
    
    return _format_change_response(change, None)


@router.get("/{change_id}", response_model=ChangeResultResponse)
async def get_change_result(change_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Check the status/result of a change detection job."""
    result = await db.execute(select(ChangeResultModel).where(ChangeResultModel.id == change_id))
    change = result.scalar_one_or_none()
    if not change:
        raise HTTPException(status_code=404, detail="Change result not found")
        
    impact = None
    if change.status == "completed":
        result_impact = await db.execute(select(ImpactStatsModel).where(ImpactStatsModel.change_result_id == change_id))
        impact = result_impact.scalar_one_or_none()

    return _format_change_response(change, impact)


def _format_change_response(change: ChangeResultModel, impact: ImpactStatsModel | None):
    impact_dict = None
    if impact:
        impact_dict = ImpactStats(
            affected_population=impact.affected_population,
            affected_buildings=impact.affected_buildings,
            affected_roads_km=impact.affected_roads_km,
            affected_area_sqkm=impact.affected_area_sqkm,
            data_sources=impact.data_sources or []
        )
        
    return ChangeResultResponse(
        change_id=change.id,
        before_image_id=change.before_image_id,
        after_image_id=change.after_image_id,
        change_mask_url=change.change_mask_url,
        change_pct=change.change_pct,
        impact_stats=impact_dict,
        status=change.status,
        error_message=change.error_message,
        created_at=change.created_at,
        completed_at=change.completed_at
    )
