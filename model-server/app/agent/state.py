"""Typed state and evidence contracts for the remote-sensing graph."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union
from datetime import datetime

from pydantic import BaseModel, Field, computed_field


SourceType = Literal["observation", "interpretation", "calculation", "metadata", "unsupported"]
TaskKind = Literal["vqa", "land_cover", "change_detection", "fusion", "segmentation"]


class BBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    crs: Optional[str] = None


class LocalizeResponse(BaseModel):
    bbox: Optional[BBox] = None
    point_x: Optional[float] = Field(None, description="The X coordinate of a point strictly on the object (0-1000 scale). Must be inside the bbox.")
    point_y: Optional[float] = Field(None, description="The Y coordinate of a point strictly on the object (0-1000 scale). Must be inside the bbox.")


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
    observed_features: str
    interpretation: str
    uncertainty: str

    @computed_field
    @property
    def answer(self) -> str:
        return f"Observed features: {self.observed_features}\nInterpretation: {self.interpretation}\nUncertainty: {self.uncertainty}"


class ConversationalResponse(BaseModel):
    answer: str
    referenced_turn: Optional[int] = None


class ChangeSummaryResponse(BaseModel):
    summary: str


class FusionResponse(BaseModel):
    analysis: str
    agreement_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)

class CaptionResponse(BaseModel):
    caption: str


class ClarificationResponse(BaseModel):
    """Returned when the classified task cannot be fulfilled with the given inputs."""
    inferred_task: str
    message: str
    missing_inputs: list[str] = []


class ClaimJudgment(BaseModel):
    claim_id: str
    verdict: Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTS_EVIDENCE"]
    reason: str


class JudgeResponse(BaseModel):
    judgments: List[ClaimJudgment] = Field(default_factory=list)


class TraceEntry(BaseModel):
    node: str
    timestamp: datetime
    reasoning: Optional[str] = None
    input_summary: dict = Field(default_factory=dict)
    output_summary: dict = Field(default_factory=dict)
    duration_ms: float = 0.0


class TaskType(BaseModel):
    kind: Union[TaskKind, Literal["conversational"]]
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
    missing_inputs: List[str] = Field(default_factory=list)
    sensor_metadata: Dict[str, SensorMetadata] = Field(default_factory=dict)
    quality_report: Dict[str, QualityReport] = Field(default_factory=dict)
    
    mode: Literal["vqa", "segmentation", "change_detection", "fusion", "conversational"] = "vqa"
    task_type: Optional[TaskType] = None
    inferred_task: Optional[str] = None
    task_routing_reason: str = ""
    classifier_scores: Dict[str, float] = Field(default_factory=dict)
    classifier_confidence: float = 0.0
    needs_clarification: bool = False
    clarification_message: str = ""
    model_used: Optional[str] = None

    scene_observations: List[Observation] = Field(default_factory=list)
    land_cover: Optional[Dict[str, Any]] = None
    gis_calculations: Dict[str, Any] = Field(default_factory=dict)
    interpretations: List[EvidenceItem] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    unsupported: List[str] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    validation_report: Dict[str, Any] = Field(default_factory=dict)

    final_answer: Union[AnswerResponse, ConversationalResponse, str] = ""
    tool_result: Dict[str, Any] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    trace: List[TraceEntry] = Field(default_factory=list)

    def public_dict(self) -> Dict[str, Any]:
        """Serialize only user-facing artifacts; never expose internal trace."""
        return self.model_dump(exclude={"trace", "image_context"})

GraphState.model_rebuild()
