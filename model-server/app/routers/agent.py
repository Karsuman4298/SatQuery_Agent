"""
Agent endpoint — orchestrates multi-agent satellite analysis via LangGraph.
POST /agent  →  runs the full router → executor pipeline.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4
import asyncio

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field

from app.agent.pipeline import new_state
from app.agent.production_graph import production_graph
from app.agent.state import GraphState

from app.runtime.api import owner as runtime_owner

router = APIRouter()


class AgentRequest(BaseModel):
    """Incoming request payload for the agent endpoint."""
    mode: str = "vqa"
    question: str = Field(min_length=1, max_length=2000)
    asset_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=2)
    thread_id: UUID | None = None
    alignment_confirmed: bool = False
    image: str = ""           # base64 primary image
    before: str = ""          # base64 before image (temporal)
    after: str = ""           # base64 after image (temporal)
    optical: str = ""         # base64 optical image (fusion)
    sar: str = ""             # base64 SAR image (fusion)
    region_name: str = ""
    click_point: tuple[int, int] | None = None
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
async def run_agent(request: AgentRequest, owner_scope: str = Depends(runtime_owner)) -> AgentResponse:
    """
    Run the full agentic pipeline:
    1. Router decides which tool best fits the query.
    2. Executor invokes the tool with the image context.
    3. Returns formatted answer + raw tool outputs.
    """
    if request.asset_ids:
        from app.runtime.api import query as run_reference_query, runtime
        from app.runtime.contracts import Query
        import base64
        task = {"segmentation": "grounding", "change_detection": "change", "fusion": "fusion"}.get(request.mode, "auto")
        result = await run_reference_query(Query(query=request.question, asset_ids=request.asset_ids,
            thread_id=request.thread_id or uuid4(), task=task, alignment_confirmed=request.alignment_confirmed,
            click_point=request.click_point), owner_scope)
        mask = next((item for item in result.evidence if item.mask_uri), None)
        mask_data = None
        if mask:
            from starlette.concurrency import run_in_threadpool
            mask_data = "data:image/png;base64," + base64.b64encode(await run_in_threadpool(runtime().objects.get, mask.mask_uri)).decode()
        return AgentResponse(answer=result.answer, tool_used=result.plan.tool, confidence=result.confidence or 0.,
            segment_mask=mask_data, inferred_task=result.plan.task,
            execution_summary={"execution_id": str(result.execution_id), "thread_id": str(result.thread_id),
                "plan": result.plan.model_dump(mode="json"), "warnings": result.warnings,
                "status": result.status, "confidence_available": result.confidence is not None},
            evidence=[item.model_dump(mode="json") for item in result.evidence],
            errors=[{"error": issue, "recovered": False} for issue in result.conflicts],
            stages=[item.model_dump(mode="json") for item in result.trace])

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
        final_state = GraphState.model_validate(await asyncio.wait_for(production_graph.ainvoke(initial_state), timeout=170))
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
            "tool_parameters": {"mode": request.mode, "click_point": request.click_point},
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
    if len(_DEBUG_TRACES) >= 100:
        _DEBUG_TRACES.pop(next(iter(_DEBUG_TRACES)))
    _DEBUG_TRACES[initial_state.query_id] = final_state.trace

    if tool_used == "change_detection":
        response.change_mask = tool_result.get("change_mask")
        response.change_pct = tool_result.get("change_pct")

    elif tool_used == "fusion":
        response.agreement_pct = tool_result.get("agreement_pct")

    elif tool_used == "segmentation":
        response.segment_mask = tool_result.get("mask")

    return response
