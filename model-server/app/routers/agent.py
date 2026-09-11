"""
Agent endpoint — orchestrates multi-agent satellite analysis via LangGraph.
POST /agent  →  runs the full router → executor pipeline.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.agent.pipeline import new_state
from app.agent.production_graph import production_graph
from app.agent.state import GraphState

router = APIRouter()


class AgentRequest(BaseModel):
    """Incoming request payload for the agent endpoint."""
    mode: str = "vqa"
    question: str
    image: str = ""           # base64 primary image
    before: str = ""          # base64 before image (temporal)
    after: str = ""           # base64 after image (temporal)
    optical: str = ""         # base64 optical image (fusion)
    sar: str = ""             # base64 SAR image (fusion)
    region_name: str = ""
    click_point: list[int] | None = None
    chat_history: list[dict] = []   # [{"role": "user"|"assistant", "content": "..."}]
    metadata: dict[str, Any] = {}

class AgentResponse(BaseModel):
    """Response returned by the agent."""
    answer: str
    tool_used: str
    confidence: float = 0.0
    change_mask: str | None = None    # base64 PNG (only for change_detection)
    change_pct: float | None = None   # (only for change_detection)
    agreement_pct: float | None = None  # (only for fusion)
    segment_mask: str | None = None   # base64 PNG (only for segmentation)
    inferred_task: str | None = None
    task_routing_reason: str | None = None
    execution_summary: dict | None = None
    evidence: list[dict] = []
    errors: list[dict] = []
    stages: list[dict] = []

@router.post("/agent", response_model=AgentResponse)
@router.post("/agent/query", response_model=AgentResponse, include_in_schema=True)
async def run_agent(request: AgentRequest) -> AgentResponse:
    """
    Run the full agentic pipeline:
    1. Router decides which tool best fits the query.
    2. Executor invokes the tool with the image context.
    3. Returns formatted answer + raw tool outputs.
    """
    # Reconstruct LangChain message history
    messages = []
    for msg in request.chat_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    messages.append(HumanMessage(content=request.question))

    # Build image context
    image_context: dict[str, Any] = {}
    if request.image:
        image_context["image"] = request.image
    if request.before:
        image_context["before"] = request.before
    if request.after:
        image_context["after"] = request.after
    if request.optical:
        image_context["optical"] = request.optical
    if request.sar:
        image_context["sar"] = request.sar
    if request.region_name:
        image_context["region_name"] = request.region_name
    if request.click_point:
        image_context["click_point"] = request.click_point
    if request.metadata:
        image_context["metadata"] = request.metadata

    image_context["chat_history"] = request.chat_history
    initial_state = new_state(request.question, image_context, request.mode)
    try:
        final_state = GraphState.model_validate(await production_graph.ainvoke(initial_state))
    except Exception as exc:
        return AgentResponse(
            answer=f"Analysis unavailable: {exc}",
            tool_used="error",
            confidence=0.0,
            errors=[{"node": "agent_graph", "error": str(exc), "recovered": False}],
        )

    tool_used = final_state.task_type.kind if final_state.task_type else "vqa"
    tool_result = final_state.tool_result
    final_answer = final_state.final_answer

    # Build response
    response = AgentResponse(
        answer=final_answer,
        tool_used=tool_used,
        confidence=tool_result.get("confidence", final_state.uncertainty.get("overall_confidence", 0.0)),
        inferred_task=final_state.inferred_task or tool_used,
        task_routing_reason=final_state.task_routing_reason,
        execution_summary={
            "inferred_task": final_state.inferred_task or tool_used,
            "classifier_confidence": final_state.classifier_confidence,
            "task_routing_reason": final_state.task_routing_reason,
            "classifier_scores": final_state.classifier_scores,
            "needs_clarification": final_state.needs_clarification,
            "model_used": final_state.model_used,
        },
        evidence=[item.model_dump() if hasattr(item, "model_dump") else item for item in final_state.evidence],
        errors=final_state.errors,
        stages=[
            {"stage": item.node, "status": "complete", "data": {}}
            for item in final_state.trace
        ],
    )

    from app.routers.debug import _DEBUG_TRACES
    _DEBUG_TRACES[initial_state.query_id] = final_state.trace

    if tool_used == "change_detection":
        response.change_mask = tool_result.get("change_mask")
        response.change_pct = tool_result.get("change_pct")

    elif tool_used == "fusion":
        response.agreement_pct = tool_result.get("agreement_pct")

    elif tool_used == "segmentation":
        response.segment_mask = tool_result.get("mask")

    return response
