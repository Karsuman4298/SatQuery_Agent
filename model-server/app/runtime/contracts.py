from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


def now(): return datetime.now(timezone.utc)


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid', protected_namespaces=(), allow_inf_nan=False)


class Asset(Contract):
    asset_id: UUID = Field(default_factory=uuid4)
    owner: str
    filename: str
    storage_uri: str
    preview_uri: str
    checksum: str
    modality: Literal['optical', 'multispectral', 'sar']
    sensor: str | None = None
    acquisition_time: datetime | None = None
    benchmark: str | None = None
    crs: str | None = None
    transform: list[float] = Field(default_factory=list)
    bbox_geo: list[float] | None = None
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    bands: list[str]
    dtype: str
    resolution: list[float]
    processing_level: str | None = None
    tiles: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)

    @field_validator('acquisition_time')
    @classmethod
    def normalize_time(cls, value):
        return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


Task = Literal['vqa', 'caption', 'grounding', 'change', 'fusion']


class Query(Contract):
    thread_id: UUID = Field(default_factory=uuid4)
    query: str = Field(min_length=3, max_length=2000)
    asset_ids: list[UUID] = Field(min_length=1, max_length=2)
    task: Task | Literal['auto'] = 'auto'
    alignment_confirmed: bool = False
    click_point: tuple[int, int] | None = None
    max_retries: int = Field(default=1, ge=0, le=2)
    promote_memory: bool = False

    @model_validator(mode='after')
    def validate_query(self):
        self.query = self.query.strip()
        if len(self.query) < 3 or len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError('Provide a non-empty question and distinct asset IDs.')
        if self.click_point and any(v < 0 or v > 1000 for v in self.click_point):
            raise ValueError('Click coordinates must be between 0 and 1000.')
        return self


class QueryPlan(Contract):
    task: Task
    tool: str
    asset_ids: list[UUID]
    operations: list[str]
    parameters: dict
    limitations: list[str] = Field(default_factory=list)


class Evidence(Contract):
    evidence_id: UUID = Field(default_factory=uuid4)
    asset_id: UUID
    type: Literal['observation', 'interpretation', 'calculation', 'mask', 'metadata']
    text: str = Field(min_length=1, max_length=4000)
    bbox_pixel: tuple[float, float, float, float] | None = None
    bbox_geo: tuple[float, float, float, float] | None = None
    mask_uri: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    model_name: str
    model_version: str
    timestamp: datetime = Field(default_factory=now)
    verified: bool = False


class Trace(Contract):
    stage: str
    status: Literal['complete', 'failed', 'warning'] = 'complete'
    duration_ms: int = Field(default=0, ge=0)
    parameters: dict = Field(default_factory=dict)
    output_ids: list[str] = Field(default_factory=list)
    detail: str | None = None


class Execution(Contract):
    execution_id: UUID = Field(default_factory=uuid4)
    thread_id: UUID
    owner: str
    query: str
    plan: QueryPlan | None = None
    status: Literal['running', 'complete', 'uncertain', 'failed'] = 'running'
    evidence: list[Evidence] = Field(default_factory=list)
    answer: str = ''
    confidence: float | None = None
    conflicts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[Trace] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=now)
    completed_at: datetime | None = None
    attempts: int = 0
