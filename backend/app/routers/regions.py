"""
Regions router. Handles user-drawn regions on images.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely.geometry import shape, mapping

from app.database import get_db
from app.models import RegionModel, ImageModel
from app.schemas import RegionCreate, RegionResponse

router = APIRouter()


@router.post("/", response_model=RegionResponse, status_code=201)
async def create_region(region: RegionCreate, db: AsyncSession = Depends(get_db)):
    """Create a named region tied to an image."""
    
    # Verify image exists
    result = await db.execute(select(ImageModel).where(ImageModel.id == region.image_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    geom = None
    if region.geometry:
        try:
            shapely_geom = shape(region.geometry.dict())
            geom = WKTElement(shapely_geom.wkt, srid=4326)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid geometry: {e}")

    pixel_bounds_dict = region.pixel_bounds.dict() if region.pixel_bounds else None

    db_region = RegionModel(
        image_id=region.image_id,
        name=region.name,
        geometry=geom,
        pixel_bounds=pixel_bounds_dict,
    )
    db.add(db_region)
    await db.commit()
    await db.refresh(db_region)

    response_geom = None
    if db_region.geometry is not None:
        try:
            sh = to_shape(db_region.geometry)
            response_geom = mapping(sh)
        except Exception:
            pass

    return RegionResponse(
        id=db_region.id,
        image_id=db_region.image_id,
        name=db_region.name,
        geometry=response_geom,
        pixel_bounds=db_region.pixel_bounds,
        created_at=db_region.created_at,
    )


@router.get("/{image_id}", response_model=List[RegionResponse])
async def list_regions(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all regions for an image."""
    result = await db.execute(select(RegionModel).where(RegionModel.image_id == image_id))
    regions = result.scalars().all()
    
    responses = []
    for r in regions:
        response_geom = None
        if r.geometry is not None:
            try:
                sh = to_shape(r.geometry)
                response_geom = mapping(sh)
            except Exception:
                pass
                
        responses.append(RegionResponse(
            id=r.id,
            image_id=r.image_id,
            name=r.name,
            geometry=response_geom,
            pixel_bounds=r.pixel_bounds,
            created_at=r.created_at,
        ))
        
    return responses


@router.delete("/{image_id}/{region_id}", status_code=204)
async def delete_region(image_id: uuid.UUID, region_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a region."""
    result = await db.execute(
        delete(RegionModel)
        .where(RegionModel.id == region_id)
        .where(RegionModel.image_id == image_id)
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Region not found")
        
    await db.commit()
