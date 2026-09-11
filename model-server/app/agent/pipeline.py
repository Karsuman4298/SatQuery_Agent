"""Structured production analysis nodes used by the agent graph."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agent.state import EvidenceItem, GraphState, JudgeResponse, Observation, ObservationResponse, QualityReport, SensorMetadata, TaskType
from app.openrouter import call_model_with_schema, image_data_uri, with_graceful_degradation, strip_reasoning

_OBSERVATION_CACHE = {}
from app.tools.quality import assess_image


OBSERVATION_PROMPT = """You are an observation-only remote-sensing module.
Return strict JSON: {"observations": [{"text": string, "confidence": number}]}.
Describe only directly visible features: tone, texture, shape, pattern, drainage,
terrain, water, vegetation, fields, roads, and built-up features.
Never output exact coordinates, sensor names, dates, crop species, disaster causes,
percentages, or precise counts. Do not explain your reasoning or mention the user.
Omit uncertain observations rather than guessing."""


def trace_node(state: GraphState, node: str) -> None:
    from app.agent.state import TraceEntry
    timestamp = datetime.now(timezone.utc)
    print(f"[agent-node] {node} {timestamp.isoformat()}")
    state.trace.append(TraceEntry(node=node, timestamp=timestamp))


def _task_type(question: str, context: dict[str, Any]) -> TaskType:
    query = question.lower()
    
    # Respect explicit task selection from the frontend
    explicit_task = context.get("task")
    if explicit_task:
        if explicit_task == "change_detection":
            return TaskType(kind="change_detection", requires_pair=True)
        if explicit_task == "fusion":
            return TaskType(kind="fusion", requires_pair=True, requires_sar=True)
        if explicit_task == "segmentation":
            return TaskType(kind="segmentation")
        if explicit_task == "land_cover":
            return TaskType(kind="land_cover")
        if explicit_task == "conversational":
            return TaskType(kind="conversational")
        return TaskType(kind="vqa")
        
    # Conversational if no image was provided by backend
    if not context.get("image") and not context.get("before") and not context.get("optical"):
        return TaskType(kind="conversational")
        
    if context.get("before") and context.get("after"):
        return TaskType(kind="change_detection", requires_pair=True)
    if context.get("optical") and context.get("sar"):
        return TaskType(kind="fusion", requires_pair=True, requires_sar=True)
    if context.get("click_point"):
        return TaskType(kind="segmentation")
    if any(word in query for word in ("land cover", "landcover", "classify", "terrain", "physiographic")):
        return TaskType(kind="land_cover")
    if any(word in query for word in ("segment", "segemnt", "mask", "outline", "isolate")):
        return TaskType(kind="segmentation")
    return TaskType(kind="vqa")


from app.agent.classifier import get_classifier


async def validate_input(state: GraphState) -> GraphState:
    trace_node(state, "input_validation")
    
    query = state.user_query.strip()
    frontend_mode = state.mode

    # 1. Query-driven task classification
    if query:
        classifier = await get_classifier()
        predicted_task, confidence, scores = await classifier.classify(query)
        state.classifier_scores = scores
        state.classifier_confidence = confidence
        state.inferred_task = predicted_task or frontend_mode or "vqa"
    else:
        state.inferred_task = frontend_mode or "conversational"
        state.task_routing_reason = "No text query provided"

    state.validated = True
    return state


_METADATA_CACHE = {}
_QUALITY_CACHE = {}

import hashlib

def _get_cache_key(image_id: str, image_b64: str) -> str:
    if not image_id or not image_b64:
        return None
    image_hash = hashlib.md5(image_b64.encode('utf-8')).hexdigest()
    return f"{image_id}_{image_hash}"

def normalize_metadata(state: GraphState) -> GraphState:
    trace_node(state, "sensor_metadata")
    image_id = state.image_context.get("metadata", {}).get("image_id")
    image_b64 = state.image_context.get("image", "")
    cache_key = _get_cache_key(image_id, image_b64)
    
    if cache_key and cache_key in _METADATA_CACHE:
        state.sensor_metadata["primary"] = _METADATA_CACHE[cache_key]
        return state

    metadata = state.image_context.get("metadata", {})
    if metadata:
        state.sensor_metadata["primary"] = SensorMetadata(
            crs=metadata.get("crs"),
            resolution_m=metadata.get("resolution_m"),
            band_count=metadata.get("band_count"),
            dtype=(metadata.get("metadata_json") or {}).get("dtype"),
            sensor_name=metadata.get("sensor"),
            provenance="file_metadata" if any(metadata.get(key) for key in ("crs", "resolution_m", "band_count", "sensor")) else "unknown",
        )
        if cache_key:
            _METADATA_CACHE[cache_key] = state.sensor_metadata["primary"]
    return state


def assess_quality(state: GraphState) -> GraphState:
    trace_node(state, "image_quality")
    image_id = state.image_context.get("metadata", {}).get("image_id")
    image_b64 = state.image_context.get("image", "")
    cache_key = _get_cache_key(image_id, image_b64)
    
    if cache_key and cache_key in _QUALITY_CACHE:
        state.quality_report = _QUALITY_CACHE[cache_key]
        if not state.quality_report.get("image", QualityReport(usable=True)).usable:
            state.validated = False
        return state

    for name in ("image", "before", "after", "optical", "sar"):
        image = state.image_context.get(name)
        if image:
            report = assess_image(image)
            state.quality_report[name] = QualityReport(
                usable=report.get("usable", False),
                blur_score=report.get("blur_score"),
                cloud_cover_pct=report.get("cloud_cover_pct"),
                issues=report.get("issues", []),
            )
            if not report.get("usable") and name == "image":
                state.validation_errors.extend(report.get("issues", []))
                state.validated = False
                
    if cache_key:
        _QUALITY_CACHE[cache_key] = state.quality_report
    return state


@with_graceful_degradation(fallback_factory=lambda: ObservationResponse(observations=[]))
async def observe_scene(state: GraphState) -> GraphState:
    trace_node(state, "scene_observation")
    image = state.image_context.get("image", "")
    if not image:
        return state
    image_id = state.image_context.get("metadata", {}).get("image_id")
    cache_key = _get_cache_key(image_id, image)
    
    if cache_key and cache_key in _OBSERVATION_CACHE:
        state.scene_observations = _OBSERVATION_CACHE[cache_key]
        if state.trace:
            state.trace[-1].reasoning = "Cache hit - skipped VLM call."
        return state

    parsed, reasoning = await call_model_with_schema([
        {"role": "system", "content": OBSERVATION_PROMPT},
        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_data_uri(image)}}, {"type": "text", "text": "Observe this satellite image."}]},
    ], ObservationResponse, max_tokens=800, temperature=0.0)
    
    state.scene_observations = parsed.observations
    if cache_key:
        _OBSERVATION_CACHE[cache_key] = parsed.observations
    if state.trace and reasoning:
        state.trace[-1].reasoning = reasoning
    return state


def validate_claims(state: GraphState) -> GraphState:
    trace_node(state, "evidence_validator")
    blocked = re.compile(r"\b(EPSG:\d+|\d+\s*(?:%|km|meters?|metres?)|20\d{2}|sentinel[- ]?\d|landsat)\b", re.I)
    for index, observation in enumerate(state.scene_observations):
        state.evidence.append(EvidenceItem(
            claim_id=f"observation-{index + 1}",
            source_type="observation",
            text=observation.text,
            confidence=observation.confidence,
        ))
    for interpretation in state.interpretations:
        item = interpretation if isinstance(interpretation, EvidenceItem) else EvidenceItem(**interpretation)
        state.evidence.append(item)
        if blocked.search(item.text) and not any(
            token in item.text.lower() for token in ("metadata", "computed", "calculated", "resolution")
        ):
            state.unsupported.append(item.text)
    state.validation_report = {"claims_checked": len(state.evidence), "unsupported_count": len(state.unsupported)}
    return state


@with_graceful_degradation(fallback_factory=lambda: JudgeResponse(judgments=[]))
async def judge_claims(state: GraphState) -> GraphState:
    """Run a separate judge-role model call over the draft evidence."""
    trace_node(state, "evidence_judge")
    if not state.interpretations:
        return state
    evidence_text = json.dumps([item.model_dump() if isinstance(item, EvidenceItem) else item for item in state.interpretations], default=str)
    result, reasoning = await call_model_with_schema([
        {
            "role": "system",
            "content": "You are an evidence validator. Judge each claim only against the supplied evidence. Return SUPPORTED, UNSUPPORTED, or CONTRADICTS_EVIDENCE. Do not add claims or reasoning outside the schema.",
        },
        {"role": "user", "content": f"Draft claims:\n{evidence_text}"},
    ], JudgeResponse, max_tokens=900, temperature=0.0)
    decisions = {item.claim_id: item for item in result.judgments}
    for item in state.evidence:
        judgment = decisions.get(item.claim_id)
        if judgment and judgment.verdict != "SUPPORTED":
            state.unsupported.append(item.text)
    state.validation_report["judge"] = [item.model_dump() for item in result.judgments]
    if state.trace and reasoning:
        state.trace[-1].reasoning = reasoning
    return state


def calculate_uncertainty(state: GraphState) -> GraphState:
    trace_node(state, "uncertainty_checker")
    quality = list(state.quality_report.values())
    quality_factor = 1.0 if not quality else sum(1.0 if report.usable else 0.25 for report in quality) / len(quality)
    
    tool_conf = state.tool_result.get("confidence", 0.75) if state.tool_result else 0.75
    state.uncertainty = {"overall_confidence": round(tool_conf * quality_factor, 3), "quality_factor": quality_factor}
    return state


def render_report(state: GraphState, answer: str = "") -> GraphState:
    trace_node(state, "report_generator")
    observations = "\n".join(f"- {item.text}" for item in state.scene_observations)
    metadata = state.sensor_metadata.get("primary")
    metadata_line = f"CRS: {metadata.crs}; resolution: {metadata.resolution_m} m; bands: {metadata.band_count}" if metadata else "Technical metadata unavailable."
    uncertainty = "Exact location, acquisition date, and unsupported measurements are not inferred from the image."
    if state.unsupported:
        uncertainty += " Some generated claims were withheld because they were not grounded in validated evidence."
    state.final_answer = answer or f"Observed features:\n{observations or '- No validated observations were returned.'}\n\nMetadata: {metadata_line}\n\nUncertainty: {uncertainty}"
    return state


def new_state(query: str, image_context: dict[str, Any] = None, mode: str = "vqa") -> GraphState:
    """Initialize a fresh graph state."""
    return GraphState(
        session_id=str(uuid.uuid4()),
        query_id=str(uuid.uuid4()),
        user_query=query,
        image_context=image_context or {},
        mode=mode
    )
