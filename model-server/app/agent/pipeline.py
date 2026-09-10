"""Structured production analysis nodes used by the agent graph."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.agent.state import EvidenceItem, GraphState, JudgeResponse, Observation, ObservationResponse, QualityReport, SensorMetadata, TaskType
from app.openrouter import call_model_with_schema, image_data_uri
from app.tools.quality import assess_image


OBSERVATION_PROMPT = """You are an observation-only remote-sensing module.
Return strict JSON: {"observations": [{"text": string, "confidence": number}]}.
Describe only directly visible features: tone, texture, shape, pattern, drainage,
terrain, water, vegetation, fields, roads, and built-up features.
Never output exact coordinates, sensor names, dates, crop species, disaster causes,
percentages, or precise counts. Do not explain your reasoning or mention the user.
Omit uncertain observations rather than guessing."""


def trace_node(state: GraphState, node: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[agent-node] {node} {timestamp}")
    state.trace.append({"node": node, "ts": timestamp})


def _task_type(question: str, context: dict[str, Any]) -> TaskType:
    query = question.lower()
    if context.get("before") and context.get("after"):
        return TaskType(kind="change_detection", requires_pair=True)
    if context.get("optical") and context.get("sar"):
        return TaskType(kind="fusion", requires_pair=True, requires_sar=True)
    if context.get("click_point"):
        return TaskType(kind="segmentation")
    if any(word in query for word in ("land cover", "landcover", "classify", "terrain", "physiographic")):
        return TaskType(kind="land_cover")
    return TaskType(kind="vqa")


def validate_input(state: GraphState) -> GraphState:
    trace_node(state, "input_validation")
    state.task_type = _task_type(state.user_query, state.image_context)
    if not state.user_query.strip():
        state.validation_errors.append("Question cannot be empty")
    primary = state.image_context.get("image", "")
    if not primary and state.task_type.kind not in {"change_detection", "fusion"}:
        state.validation_errors.append("No primary image was supplied")
    if state.task_type.requires_pair:
        if state.task_type.kind == "change_detection" and not (state.image_context.get("before") and state.image_context.get("after")):
            state.validation_errors.append("Before and after images are required")
        if state.task_type.kind == "fusion" and not (state.image_context.get("optical") and state.image_context.get("sar")):
            state.validation_errors.append("Optical and SAR images are required")
    state.validated = not state.validation_errors
    return state


def normalize_metadata(state: GraphState) -> GraphState:
    trace_node(state, "sensor_metadata")
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
    return state


def assess_quality(state: GraphState) -> GraphState:
    trace_node(state, "image_quality")
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
    return state


async def observe_scene(state: GraphState) -> GraphState:
    trace_node(state, "scene_observation")
    image = state.image_context.get("image", "")
    if not image:
        return state
    try:
        parsed = await call_model_with_schema([
            {"role": "system", "content": OBSERVATION_PROMPT},
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_data_uri(image)}}, {"type": "text", "text": "Observe this satellite image."}]},
        ], ObservationResponse, max_tokens=800, temperature=0.0)
        state.scene_observations = parsed.observations
    except Exception as exc:
        state.errors.append({"node": "scene_observation", "error": str(exc), "recovered": True})
        state.unsupported.append("Scene observations unavailable because the structured model response was invalid.")
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


async def judge_claims(state: GraphState) -> GraphState:
    """Run a separate judge-role model call over the draft evidence."""
    trace_node(state, "evidence_judge")
    if not state.interpretations:
        return state
    evidence_text = json.dumps([item.model_dump() if isinstance(item, EvidenceItem) else item for item in state.interpretations], default=str)
    try:
        result = await call_model_with_schema([
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
    except Exception as exc:
        state.errors.append({"node": "evidence_judge", "error": str(exc), "recovered": True})
        state.unsupported.extend(item.text for item in state.evidence if item.source_type == "interpretation")
    return state


def calculate_uncertainty(state: GraphState) -> GraphState:
    trace_node(state, "uncertainty_checker")
    quality = list(state.quality_report.values())
    quality_factor = 1.0 if not quality else sum(1.0 if report.usable else 0.25 for report in quality) / len(quality)
    state.uncertainty = {"overall_confidence": round(0.75 * quality_factor, 3), "quality_factor": quality_factor}
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


def new_state(question: str, context: dict[str, Any], query_id: str = "") -> GraphState:
    return GraphState(session_id=str(uuid.uuid4()), query_id=query_id, user_query=question, image_context=context)
