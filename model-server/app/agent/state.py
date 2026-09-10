"""Typed state and evidence contracts for the remote-sensing graph."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


SourceType = Literal["observation", "interpretation", "calculation", "metadata", "unsupported"]
TaskKind = Literal["vqa", "land_cover", "change_detection", "fusion", "segmentation"]


class BBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    crs: Optional[str] = None


class EvidenceItem(BaseModel):
    claim_id: str
    source_type: SourceType
    text: str
    region: Optional[BBox] = None
    tool_ref: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class SensorMetadata(BaseModel):
    crs: Optional[str] = None
    transform: Optional[List[float]] = None
    resolution_m: Optional[float] = None
    band_count: Optional[int] = None
    dtype: Optional[str] = None
    sensor_name: Optional[str] = None
    acquisition_date: Optional[str] = None
    footprint: Optional[BBox] = None
    provenance: Literal["file_metadata", "unknown"] = "unknown"


class QualityReport(BaseModel):
    cloud_cover_pct: Optional[float] = None
    blur_score: Optional[float] = None
    noise_score: Optional[float] = None
    misregistration_px: Optional[float] = None
    usable: bool = True
    issues: List[str] = Field(default_factory=list)


class Observation(BaseModel):
    text: str
    region: Optional[BBox] = None
    confidence: float = Field(ge=0.0, le=1.0)


class ObservationResponse(BaseModel):
    observations: List[Observation] = Field(default_factory=list)


class RouterDecision(BaseModel):
    tool: TaskKind
    reasoning: str = ""


class AnswerResponse(BaseModel):
    answer: str


class ChangeSummaryResponse(BaseModel):
    summary: str


class FusionResponse(BaseModel):
    analysis: str
    agreement_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class ClaimJudgment(BaseModel):
    claim_id: str
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTS_EVIDENCE"]
    reason: str


class JudgeResponse(BaseModel):
    judgments: List[ClaimJudgment] = Field(default_factory=list)


class TaskType(BaseModel):
    kind: TaskKind
    requires_pair: bool = False
    requires_sar: bool = False


class GraphState(BaseModel):
    session_id: str = ""
    query_id: str = ""
    user_query: str = ""
    image_refs: List[str] = Field(default_factory=list)
    roi: Optional[BBox] = None
    image_context: Dict[str, Any] = Field(default_factory=dict)

    validated: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    sensor_metadata: Dict[str, SensorMetadata] = Field(default_factory=dict)
    quality_report: Dict[str, QualityReport] = Field(default_factory=dict)
    task_type: Optional[TaskType] = None

    scene_observations: List[Observation] = Field(default_factory=list)
    land_cover: Optional[Dict[str, Any]] = None
    gis_calculations: Dict[str, Any] = Field(default_factory=dict)
    interpretations: List[EvidenceItem] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    unsupported: List[str] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    validation_report: Dict[str, Any] = Field(default_factory=dict)

    final_answer: str = ""
    tool_result: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[Dict[str, Any]] = Field(default_factory=list)

    def public_dict(self) -> Dict[str, Any]:
        """Serialize only user-facing artifacts; never expose internal trace."""
        return self.model_dump(exclude={"trace", "image_context"})
