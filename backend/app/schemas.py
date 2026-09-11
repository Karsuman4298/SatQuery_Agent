"""
Pydantic request/response schemas matching contracts/openapi.yaml.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Shared ──────────────────────────────────────────────
class PixelBounds(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class GeoJsonPolygon(BaseModel):
    type: str = "Polygon"
    coordinates: list[list[list[float]]]


class ErrorResponse(BaseModel):
    error: str
    detail: str


# ─── Image ───────────────────────────────────────────────
class ImageMetadataResponse(BaseModel):
    id: UUID
    filename: str
    file_path: str
    crs: str | None = None
    bounds: GeoJsonPolygon | None = None
    resolution_m: float | None = None
    sensor: str | None = None
    band_count: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    metadata_json: dict | None = None
    upload_time: datetime

    class Config:
        from_attributes = True


# ─── Region ──────────────────────────────────────────────
class RegionCreate(BaseModel):
    image_id: UUID
    name: str
    geometry: GeoJsonPolygon | None = None
    pixel_bounds: PixelBounds | None = None


class RegionResponse(BaseModel):
    id: UUID
    image_id: UUID
    name: str
    geometry: GeoJsonPolygon | None = None
    pixel_bounds: PixelBounds | None = None
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Query ───────────────────────────────────────────────
from typing import Literal

class QueryRequest(BaseModel):
    mode: Literal["vqa", "segmentation", "change_detection", "fusion", "conversational"]
    question: str = ""
    image_id: UUID | None = None
    region_id: UUID | None = None
    
    # Optional fields for multi-image modes
    before_image_id: UUID | None = None
    after_image_id: UUID | None = None
    optical_image_id: UUID | None = None
    sar_image_id: UUID | None = None


class ExecutionTraceStep(BaseModel):
    step_name: str
    status: str  # pending | running | completed | failed
    duration_ms: int = 0
    detail: str | None = None


class Evidence(BaseModel):
    type: str  # bbox | mask | point
    bbox: PixelBounds | None = None
    mask_url: str | None = None
    confidence: float
    label: str | None = None


class QueryResponse(BaseModel):
    query_id: UUID
    answer: str
    confidence: float
    evidence: list[Evidence] = []
    execution_trace: list[ExecutionTraceStep] = []
    model_used: str | None = None

    class Config:
        from_attributes = True


# ─── Temporal ────────────────────────────────────────────
class TemporalRequest(BaseModel):
    before_image_id: UUID
    after_image_id: UUID


class ImpactStats(BaseModel):
    affected_population: int | None = None
    affected_buildings: int | None = None
    affected_roads_km: float | None = None
    affected_area_sqkm: float | None = None
    data_sources: list[str] = []


class ChangeResultResponse(BaseModel):
    change_id: UUID
    before_image_id: UUID
    after_image_id: UUID
    change_mask_url: str | None = None
    change_pct: float | None = None
    impact_stats: ImpactStats | None = None
    status: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


# ─── Fusion ──────────────────────────────────────────────
class FusionRequest(BaseModel):
    optical_image_id: UUID
    sar_image_id: UUID
    region_id: UUID | None = None


class FusionResponse(BaseModel):
    verification_result: str
    confidence: float
    agreement_pct: float | None = None
    details: dict | None = None
    execution_trace: list[ExecutionTraceStep] = []
