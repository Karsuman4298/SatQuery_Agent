"""
Unified agent query router handling all 5 modalities.
"""

import uuid
from typing import AsyncGenerator
import json
import base64
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import numpy as np
import rasterio
from PIL import Image

from app.config import settings
from app.database import get_db
from app.models import ImageModel, RegionModel, QueryModel
from app.schemas import QueryRequest, QueryResponse
from app.main import http_client

router = APIRouter()


def _image_data_uri(image: ImageModel, region: RegionModel | None = None) -> str:
    path = Path(image.file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Uploaded image is not available: {path}")

    try:
        with rasterio.open(path) as source:
            window = None
            if region and region.pixel_bounds:
                bounds = region.pixel_bounds
                left = max(0, min(int(bounds.get("x_min", 0)), source.width))
                top = max(0, min(int(bounds.get("y_min", 0)), source.height))
                right = max(left, min(int(bounds.get("x_max", source.width)), source.width))
                bottom = max(top, min(int(bounds.get("y_max", source.height)), source.height))
                if right > left and bottom > top:
                    window = rasterio.windows.Window(left, top, right - left, bottom - top)

            bands = source.read(window=window).astype(np.float32)
            bands = np.nan_to_num(bands, nan=0.0, posinf=0.0, neginf=0.0)

            enhanced = np.zeros_like(bands, dtype=np.uint8)
            for band_index in range(bands.shape[0]):
                band = bands[band_index]
                valid = band[np.isfinite(band) & (band != 0)]
                if valid.size == 0:
                    continue
                low, high = np.percentile(valid, (2, 98))
                if high <= low:
                    enhanced[band_index] = np.clip(band, 0, 255).astype(np.uint8)
                else:
                    scaled = (band - low) / (high - low) * 255.0
                    enhanced[band_index] = np.clip(scaled, 0, 255).astype(np.uint8)

            if enhanced.shape[0] == 1:
                rgb = np.repeat(enhanced, 3, axis=0)
            elif enhanced.shape[0] == 2:
                rgb = np.concatenate([enhanced, enhanced[1:2]], axis=0)
            else:
                rgb = enhanced[:3]
            converted = Image.fromarray(np.transpose(rgb, (1, 2, 0)), mode="RGB")
    except (rasterio.errors.RasterioIOError, ValueError):
        with Image.open(path) as source:
            converted = source.convert("RGB")
            if region and region.pixel_bounds:
                bounds = region.pixel_bounds
                left = max(0, min(int(bounds.get("x_min", 0)), converted.width))
                top = max(0, min(int(bounds.get("y_min", 0)), converted.height))
                right = max(left, min(int(bounds.get("x_max", converted.width)), converted.width))
                bottom = max(top, min(int(bounds.get("y_max", converted.height)), converted.height))
                if right > left and bottom > top:
                    converted = converted.crop((left, top, right, bottom))

    buffer = io.BytesIO()
    converted.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _image_agent_metadata(image: ImageModel, region: RegionModel | None = None) -> dict:
    metadata = {
        "filename": image.filename,
        "crs": image.crs,
        "resolution_m": image.resolution_m,
        "sensor": image.sensor,
        "band_count": image.band_count,
        "width_px": image.width_px,
        "height_px": image.height_px,
        "metadata_json": image.metadata_json or {},
        "image_id": str(image.id),
    }
    if region:
        metadata["region"] = {
            "name": region.name,
            "pixel_bounds": region.pixel_bounds or {},
        }
    return metadata


async def _chat_history(image_id: uuid.UUID | None, db: AsyncSession) -> list[dict[str, str]]:
    if not image_id:
        return []
    result = await db.execute(
        select(QueryModel)
        .where(QueryModel.image_id == image_id)
        .order_by(QueryModel.created_at.desc())
        .limit(10)
    )
    history: list[dict[str, str]] = []
    for previous in reversed(result.scalars().all()):
        history.append({"role": "user", "content": previous.question})
        if previous.answer:
            history.append({"role": "assistant", "content": previous.answer})
    return history


async def stream_query(
    query_id: uuid.UUID,
    request: QueryRequest,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    
    def format_sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    try:
        def stage(stage_name: str, status: str, data: dict | None = None) -> str:
            return format_sse("stage", {"stage": stage_name, "status": status, "data": data or {}})

        yield stage("input_validation", "running")

        # Resolve images
        agent_payload = {
            "mode": request.mode,
            "question": request.question,
            "chat_history": await _chat_history(request.image_id, db),
            "image": "",
            "before": "",
            "after": "",
            "optical": "",
            "sar": "",
            "metadata": {}
        }
        
        primary_image = None
        region = None

        if request.image_id:
            img = (await db.execute(select(ImageModel).where(ImageModel.id == request.image_id))).scalar_one_or_none()
            if img:
                primary_image = img
                if request.region_id:
                    region = (await db.execute(select(RegionModel).where(RegionModel.id == request.region_id))).scalar_one_or_none()
                agent_payload["image"] = _image_data_uri(img, region)
                agent_payload["metadata"] = _image_agent_metadata(img, region)
                if region:
                    agent_payload["region_name"] = region.name
                    
        if request.before_image_id and request.after_image_id:
            b_img = (await db.execute(select(ImageModel).where(ImageModel.id == request.before_image_id))).scalar_one_or_none()
            a_img = (await db.execute(select(ImageModel).where(ImageModel.id == request.after_image_id))).scalar_one_or_none()
            if b_img and a_img:
                primary_image = a_img
                agent_payload["before"] = _image_data_uri(b_img)
                agent_payload["after"] = _image_data_uri(a_img)
                if not agent_payload["metadata"]:
                    agent_payload["metadata"] = _image_agent_metadata(a_img)
                    
        if request.optical_image_id and request.sar_image_id:
            o_img = (await db.execute(select(ImageModel).where(ImageModel.id == request.optical_image_id))).scalar_one_or_none()
            s_img = (await db.execute(select(ImageModel).where(ImageModel.id == request.sar_image_id))).scalar_one_or_none()
            if o_img and s_img:
                primary_image = o_img
                agent_payload["optical"] = _image_data_uri(o_img)
                agent_payload["sar"] = _image_data_uri(s_img)
                if not agent_payload["metadata"]:
                    agent_payload["metadata"] = _image_agent_metadata(o_img)

        yield stage("input_validation", "complete")
        yield stage("agent_graph", "running")
        
        async with httpx.AsyncClient(base_url=settings.model_server_url, timeout=90.0) as client:
            model_response = await client.post("/agent", json=agent_payload)
            model_response.raise_for_status()
            result = model_response.json()
            
        for item in result.get("stages", []):
            yield stage(item["stage"], item["status"], item.get("data", {}))
            
        yield stage("report_generator", "complete", {
            "answer": result.get("answer", ""),
            "evidence": result.get("evidence", []),
            "errors": result.get("errors", []),
            "change_mask": result.get("change_mask"),
            "change_pct": result.get("change_pct"),
            "agreement_pct": result.get("agreement_pct"),
            "segment_mask": result.get("segment_mask"),
        })

        if primary_image:
            db_query = QueryModel(
                id=query_id,
                image_id=primary_image.id,
                region_id=request.region_id,
                question=request.question,
                answer=result.get("answer", ""),
                confidence=result.get("confidence", 0.88),
                evidence=result.get("evidence", []),
                execution_trace=[{"step_name": "Agent Execution", "status": "completed", "duration_ms": 1000}],
                model_used=result.get("tool_used", "agent")
            )
            db.add(db_query)
            await db.commit()

        yield stage("persist_db", "complete", {
            "query_id": str(query_id),
            "confidence": result.get("confidence", 0.0),
        })

    except Exception as e:
        yield format_sse("stage", {"stage": "error_responder", "status": "failed", "data": {"error": str(e)}})


@router.post("/", response_class=StreamingResponse)
async def submit_query(request: QueryRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    query_id = uuid.uuid4()
    
    accept = http_request.headers.get("accept", "")
    if "text/event-stream" in accept:
        return StreamingResponse(
            stream_query(query_id, request, db),
            media_type="text/event-stream"
        )
    raise HTTPException(status_code=400, detail="Only SSE is supported.")


@router.get("/{image_id}")
async def get_queries(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QueryModel)
        .where(QueryModel.image_id == image_id)
        .order_by(QueryModel.created_at.asc())
    )
    queries = result.scalars().all()
    
    return [
        {
            "id": q.id,
            "question": q.question,
            "answer": q.answer,
            "created_at": q.created_at
        }
        for q in queries
    ]
