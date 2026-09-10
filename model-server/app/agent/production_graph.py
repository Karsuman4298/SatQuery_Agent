"""Production LangGraph pipeline with typed, validated intermediate artifacts."""

from __future__ import annotations
from typing import Literal
from langgraph.graph import END, START, StateGraph

from app.agent.pipeline import (
    assess_quality,
    calculate_uncertainty,
    normalize_metadata,
    observe_scene,
    render_report,
    validate_claims,
    judge_claims,
    validate_input,
    trace_node,
)
from app.agent.state import GraphState
from app.agent.tools import change_analysis_tool, fusion_analysis_tool, segmentation_tool, vqa_tool


def _after_validation(state: GraphState) -> Literal["continue", "error"]:
    return "continue" if state.validated else "error"


def _task_route(state: GraphState) -> str:
    return state.task_type.kind if state.task_type else "vqa"


async def input_validation_node(state: GraphState) -> GraphState:
    return validate_input(state)


def metadata_node(state: GraphState) -> GraphState:
    return normalize_metadata(state)


def quality_node(state: GraphState) -> GraphState:
    return assess_quality(state)


async def observation_node(state: GraphState) -> GraphState:
    return await observe_scene(state)


async def vqa_node(state: GraphState) -> GraphState:
    trace_node(state, "vqa_agent")
    result = await vqa_tool.ainvoke({
        "image": state.image_context.get("image", ""),
        "question": state.user_query,
        "metadata": state.image_context.get("metadata", {}),
        "observations": [item.text for item in state.scene_observations],
    })
    state.tool_result = result
    state.interpretations.append({
        "claim_id": "vqa-answer",
        "source_type": "interpretation",
        "text": result.get("answer", ""),
        "confidence": result.get("confidence", 0.0),
    })
    return state


async def change_node(state: GraphState) -> GraphState:
    trace_node(state, "change_detection_agent")
    result = await change_analysis_tool.ainvoke({
        "before": state.image_context.get("before", ""),
        "after": state.image_context.get("after", ""),
    })
    state.tool_result = result
    state.interpretations.append({
        "claim_id": "change-summary",
        "source_type": "interpretation",
        "text": result.get("summary", ""),
        "confidence": 0.0,
    })
    return state


async def fusion_node(state: GraphState) -> GraphState:
    trace_node(state, "fusion_agent")
    result = await fusion_analysis_tool.ainvoke({
        "optical": state.image_context.get("optical", ""),
        "sar": state.image_context.get("sar", ""),
        "question": state.user_query,
    })
    state.tool_result = result
    state.interpretations.append({
        "claim_id": "fusion-summary",
        "source_type": "interpretation",
        "text": result.get("verification_result", ""),
        "confidence": result.get("confidence", 0.0),
    })
    return state


async def segmentation_node(state: GraphState) -> GraphState:
    trace_node(state, "segmentation_agent")
    result = await segmentation_tool.ainvoke({
        "image": state.image_context.get("image", ""),
        "point": state.image_context.get("click_point", [128, 128]),
    })
    state.tool_result = result
    return state


def evidence_node(state: GraphState) -> GraphState:
    return validate_claims(state)


def uncertainty_node(state: GraphState) -> GraphState:
    return calculate_uncertainty(state)


def report_node(state: GraphState) -> GraphState:
    result = state.tool_result
    if state.task_type and state.task_type.kind == "vqa":
        answer = result.get("answer", "")
    elif state.task_type and state.task_type.kind == "change_detection":
        answer = f"{result.get('summary', '')}\n\n**Change Extent:** {result.get('change_pct', 0):.1f}% of the scene area shows pixel-level difference."
    elif state.task_type and state.task_type.kind == "fusion":
        answer = f"{result.get('verification_result', '')}\n\n**Computed agreement indicator:** {result.get('agreement_pct', 0):.1f}%"
    elif state.task_type and state.task_type.kind == "segmentation":
        answer = "Segmentation mask generated for the selected point."
    else:
        answer = ""
    return render_report(state, answer)


def error_node(state: GraphState) -> GraphState:
    trace_node(state, "error_responder")
    state.final_answer = "Unable to analyze the input: " + "; ".join(state.validation_errors)
    return state


def build_production_graph():
    graph = StateGraph(GraphState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("sensor_metadata", metadata_node)
    graph.add_node("image_quality", quality_node)
    graph.add_node("scene_observation", observation_node)
    graph.add_node("vqa_agent", vqa_node)
    graph.add_node("land_cover_agent", vqa_node)
    graph.add_node("change_detection_agent", change_node)
    graph.add_node("fusion_agent", fusion_node)
    graph.add_node("segmentation_agent", segmentation_node)
    graph.add_node("evidence_validator", evidence_node)
    graph.add_node("evidence_judge", judge_claims)
    graph.add_node("uncertainty_checker", uncertainty_node)
    graph.add_node("report_generator", report_node)
    graph.add_node("error_responder", error_node)

    graph.add_edge(START, "input_validation")
    graph.add_conditional_edges("input_validation", _after_validation, {"continue": "sensor_metadata", "error": "error_responder"})
    graph.add_edge("sensor_metadata", "image_quality")
    graph.add_conditional_edges("image_quality", _after_validation, {"continue": "scene_observation", "error": "error_responder"})
    graph.add_conditional_edges("scene_observation", _task_route, {
        "vqa": "vqa_agent",
        "land_cover": "land_cover_agent",
        "change_detection": "change_detection_agent",
        "fusion": "fusion_agent",
        "segmentation": "segmentation_agent",
    })
    for node in ("vqa_agent", "land_cover_agent", "change_detection_agent", "fusion_agent", "segmentation_agent"):
        graph.add_edge(node, "evidence_validator")
    graph.add_edge("evidence_validator", "evidence_judge")
    graph.add_edge("evidence_judge", "uncertainty_checker")
    graph.add_edge("uncertainty_checker", "report_generator")
    graph.add_edge("report_generator", END)
    graph.add_edge("error_responder", END)
    return graph.compile()


production_graph = build_production_graph()
