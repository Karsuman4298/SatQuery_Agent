"""
Images router. Handles upload and retrieval of satellite images.
"""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

from app.config import settings
from app.database import get_db
from app.models import ImageModel
from app.schemas import ImageMetadataResponse, GeoJsonPolygon
from app.services.image_service import extract_metadata

router = APIRouter()

# Ensure upload directory exists
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=ImageMetadataResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    sensor: str | None = Form(None),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a satellite image, extract metadata, and save to database.
    """
    # Create unique filename
    ext = Path(file.filename).suffix
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = upload_dir / new_filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")

    # Extract metadata
    try:
        metadata = extract_metadata(str(file_path))
    except Exception as e:
        # Cleanup file if metadata extraction fails drastically
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")

    # Add optional overrides
    if sensor:
        metadata["sensor"] = sensor
    
    if description:
        metadata["metadata_json"]["description"] = description

    # Create DB model
    db_image = ImageModel(**metadata)
    db.add(db_image)
    await db.flush() # flush to get the ID

    # Need to convert PostGIS geometry to GeoJSON for the response
    response_bounds = None
    if db_image.bounds is not None:
        try:
            # Note: GeoAlchemy2 WKB elements can be complex to parse back in async mode before commit.
            # Using the geojson_bounds we stored earlier as a workaround for the response.
            if "geojson_bounds" in metadata.get("metadata_json", {}):
                response_bounds = metadata["metadata_json"]["geojson_bounds"]
        except Exception:
            pass

    response = ImageMetadataResponse(
        id=db_image.id,
        filename=db_image.filename,
        file_path=db_image.file_path,
        crs=db_image.crs,
        bounds=response_bounds,
        resolution_m=db_image.resolution_m,
        sensor=db_image.sensor,
        band_count=db_image.band_count,
        width_px=db_image.width_px,
        height_px=db_image.height_px,
        metadata_json=db_image.metadata_json,
        upload_time=db_image.upload_time,
    )
    
    return response


@router.get("/{image_id}", response_model=ImageMetadataResponse)
async def get_image(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get metadata for a specific image."""
    result = await db.execute(select(ImageModel).where(ImageModel.id == image_id))
    db_image = result.scalar_one_or_none()
    
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    response_bounds = None
    if db_image.bounds is not None:
        try:
            shape = to_shape(db_image.bounds)
            response_bounds = mapping(shape)
        except Exception:
            pass

    return ImageMetadataResponse(
        id=db_image.id,
        filename=db_image.filename,
        file_path=db_image.file_path,
        crs=db_image.crs,
        bounds=response_bounds,
        resolution_m=db_image.resolution_m,
        sensor=db_image.sensor,
        band_count=db_image.band_count,
        width_px=db_image.width_px,
        height_px=db_image.height_px,
        metadata_json=db_image.metadata_json,
        upload_time=db_image.upload_time,
    )


@router.get("/{image_id}/tile")
async def get_image_tile(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get the image as a web-viewable PNG tile (mocked for now)."""
    result = await db.execute(select(ImageModel).where(ImageModel.id == image_id))
    db_image = result.scalar_one_or_none()
    if not db_image:
        raise HTTPException(status_code=404, detail="Image not found")
        
    from fastapi.responses import FileResponse
    # For now, just return the raw file if it's png/jpg, otherwise return a placeholder
    path = Path(db_image.file_path)
    if path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        return FileResponse(path)
    
    # If it's a TIF, we'd need rasterio to convert it. Returning dummy content for hackathon.
    return FileResponse(path)
