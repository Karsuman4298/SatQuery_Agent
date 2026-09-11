"""Production LangGraph pipeline with typed, validated intermediate artifacts."""

from __future__ import annotations
from langgraph.graph import END, START, StateGraph

from app.agent.pipeline import (
    assess_quality,
    normalize_metadata,
    observe_scene,
    validate_input,
)
from app.agent.state import GraphState

from app.agent.modes.vqa import vqa_node
from app.agent.modes.change_detection import change_node
from app.agent.modes.fusion import fusion_node
from app.agent.modes.segmentation import segmentation_node
from app.agent.modes.conversational import conversational_router_node, conversational_aggregator_node

from app.agent.shared.evidence_validator import evidence_node, judge_claims
from app.agent.shared.uncertainty_checker import uncertainty_node
from app.agent.shared.report_generator import error_node


def _after_router(state: GraphState) -> str:
    if state.needs_clarification:
        return "conversational_aggregator"
    if state.mode == "conversational":
        return "conversational_aggregator"
    return "sensor_metadata"


def _task_route(state: GraphState) -> str:
    # Direct routing based on explicitly set mode
    mode_map = {
        "vqa": "vqa_agent",
        "change_detection": "change_detection_agent",
        "fusion": "fusion_agent",
        "segmentation": "segmentation_agent",
        "conversational": "conversational_aggregator"
    }
    return mode_map.get(state.mode, "vqa_agent")


async def input_validation_node(state: GraphState) -> GraphState:
    return await validate_input(state)


def metadata_node(state: GraphState) -> GraphState:
    return normalize_metadata(state)


def quality_node(state: GraphState) -> GraphState:
    return assess_quality(state)


async def observation_node(state: GraphState) -> GraphState:
    return await observe_scene(state)


def build_production_graph():
    graph = StateGraph(GraphState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("conversational_router", conversational_router_node)
    graph.add_node("sensor_metadata", metadata_node)
    graph.add_node("image_quality", quality_node)
    graph.add_node("scene_observation", observation_node)
    
    # Mode nodes
    graph.add_node("vqa_agent", vqa_node)
    graph.add_node("change_detection_agent", change_node)
    graph.add_node("fusion_agent", fusion_node)
    graph.add_node("segmentation_agent", segmentation_node)
    
    # Shared post-processing nodes
    graph.add_node("evidence_validator", evidence_node)
    graph.add_node("evidence_judge", judge_claims)
    graph.add_node("uncertainty_checker", uncertainty_node)
    graph.add_node("conversational_aggregator", conversational_aggregator_node)
    graph.add_node("error_responder", error_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "conversational_router")
    
    graph.add_conditional_edges("conversational_router", _after_router, {
        "conversational_aggregator": "conversational_aggregator",
        "sensor_metadata": "sensor_metadata"
    })
    
    graph.add_edge("sensor_metadata", "image_quality")
    graph.add_conditional_edges("image_quality", lambda s: "continue" if s.validated else "error", {"continue": "scene_observation", "error": "error_responder"})
    
    graph.add_conditional_edges("scene_observation", _task_route, {
        "vqa_agent": "vqa_agent",
        "change_detection_agent": "change_detection_agent",
        "fusion_agent": "fusion_agent",
        "segmentation_agent": "segmentation_agent",
        "conversational_aggregator": "conversational_aggregator"
    })
    
    def _after_agent(state: GraphState) -> str:
        if not state.validated:
            return "error_responder"
        return "evidence_validator"

    for node in ("vqa_agent", "change_detection_agent", "fusion_agent", "segmentation_agent"):
        graph.add_conditional_edges(node, _after_agent, {
            "error_responder": "error_responder",
            "evidence_validator": "evidence_validator"
        })
        
    graph.add_edge("evidence_validator", "evidence_judge")
    graph.add_edge("evidence_judge", "uncertainty_checker")
    graph.add_edge("uncertainty_checker", "conversational_aggregator")
    graph.add_edge("conversational_aggregator", END)
    graph.add_edge("error_responder", END)
    
    return graph.compile()


production_graph = build_production_graph()
