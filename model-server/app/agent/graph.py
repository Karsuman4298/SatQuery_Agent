"""
LangGraph orchestrator for SatQuery multi-agent system.

The graph has two nodes:
  1. router  — a text LLM that reads the user's query and chat history,
               then outputs a structured tool-call decision.
  2. executor — calls the chosen tool and formats the final response.

State flows: START → router → executor → END
"""

from __future__ import annotations
import json
from typing import Any, Annotated
import operator
import httpx
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from app.config import settings
from app.openrouter import call_model_with_schema
from app.agent.state import RouterDecision

from app.agent.tools import (
    vqa_tool,
    change_analysis_tool,
    fusion_analysis_tool,
    segmentation_tool,
)


# ─── State Schema ─────────────────────────────────────────────────────────────

class ImageContext(TypedDict, total=False):
    """All image-related data passed into the agent."""
    image: str            # base64 primary image
    before: str           # base64 before image (temporal)
    after: str            # base64 after image (temporal)
    optical: str          # base64 optical image (fusion)
    sar: str              # base64 SAR image (fusion)
    region_name: str      # name of the active region
    click_point: list     # [x, y] for segmentation
    metadata: dict        # database-backed image and ROI metadata


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    image_context: ImageContext
    tool_decision: str          # which tool was selected
    tool_result: dict           # result from the executed tool
    final_answer: str           # formatted answer to stream back


# ─── Router Node ──────────────────────────────────────────────────────────────

ROUTER_SYSTEM_PROMPT = """You are an intelligent routing agent for a satellite image analysis system called SatQuery.

You will receive:
- A user query about satellite imagery
- Conversation history (for context)
- Information about which images are available

Your ONLY job is to decide which specialized tool to invoke. Output EXACTLY one JSON object:

{
  "tool": "<tool_name>",
  "reasoning": "<one sentence why>"
}

Available tools:
- "vqa" → for general visual question answering on a single image (describe, classify, count objects, assess damage, identify features)
- "change_detection" → for comparing two images (before/after, temporal analysis, detecting what changed)
- "fusion" → for cross-validating optical and SAR images together (joint analysis, SAR confirmation, flood mapping)
- "segmentation" → for isolating a specific object or region based on a click point

Rules:
- If before/after images are provided → prefer "change_detection"
- If optical + SAR images are provided → prefer "fusion"
- If a click point is provided → prefer "segmentation"
- Otherwise → use "vqa"
- ONLY output valid JSON, nothing else."""


async def router_node(state: AgentState) -> dict:
    """
    Call a lightweight text LLM to decide which tool to use.
    Falls back to rule-based routing if the LLM is unavailable.
    """
    ctx = state["image_context"]
    last_query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), ""
    )
    metadata = ctx.get("metadata", {})

    # Build context summary for the router
    available_images = []
    if ctx.get("before") and ctx.get("after"):
        available_images.append("before/after image pair")
    if ctx.get("optical") and ctx.get("sar"):
        available_images.append("optical+SAR pair")
    if ctx.get("image"):
        available_images.append("single satellite image")
    if ctx.get("click_point"):
        available_images.append(f"click point at {ctx['click_point']}")

    history_str = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'AI'}: {m.content}"
        for m in state["messages"][-6:]  # last 3 turns
    )

    user_prompt = (
        f"Available data: {', '.join(available_images) or 'single image'}\n"
        f"Conversation history:\n{history_str}\n\n"
        f"Image metadata: {json.dumps(metadata, default=str)}\n"
        f"Current user query: {last_query}"
    )

    try:
        decision = await call_model_with_schema(
            [
                {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            RouterDecision,
            max_tokens=400,
            temperature=0.0,
        )
        tool_name = decision.tool
        if tool_name not in {"vqa", "change_detection", "fusion", "segmentation"}:
            raise ValueError(f"Unsupported tool selected: {tool_name}")
        print(f"Router selected: {tool_name} — {decision.reasoning}")
        return {"tool_decision": tool_name}
    except Exception as e:
        print(f"Router unavailable ({e}); using deterministic routing")

    # Deterministic routing is a control-flow fallback, never an answer fallback.
    q = last_query.lower()
    if ctx.get("before") and ctx.get("after"):
        tool_name = "change_detection"
    elif ctx.get("optical") and ctx.get("sar"):
        tool_name = "fusion"
    elif ctx.get("click_point"):
        tool_name = "segmentation"
    elif any(w in q for w in ["change", "before", "after", "differ", "temporal", "compare"]):
        tool_name = "change_detection"
    elif any(w in q for w in ["sar", "radar", "backscatter", "fusion", "optical"]):
        tool_name = "fusion"
    elif any(w in q for w in ["segment", "outline", "isolate", "click", "point"]):
        tool_name = "segmentation"
    else:
        tool_name = "vqa"

    print(f"🔀 Rule-based router selected: {tool_name}")
    return {"tool_decision": tool_name}


# ─── Executor Node ────────────────────────────────────────────────────────────

async def executor_node(state: AgentState) -> dict:
    """Execute the selected tool and format the result into a final answer."""
    tool_name = state["tool_decision"]
    ctx = state["image_context"]
    last_query = next(
        (m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), ""
    )
    metadata = ctx.get("metadata", {})

    result: dict[str, Any] = {}

    if tool_name == "change_detection":
        before = ctx.get("before", ctx.get("image", ""))
        after = ctx.get("after", "")
        result = await change_analysis_tool.ainvoke({"before": before, "after": after})

    elif tool_name == "fusion":
        optical = ctx.get("optical", ctx.get("image", ""))
        sar = ctx.get("sar", "")
        result = await fusion_analysis_tool.ainvoke({"optical": optical, "sar": sar, "question": last_query})

    elif tool_name == "segmentation":
        image = ctx.get("image", "")
        point = ctx.get("click_point", [128, 128])
        result = await segmentation_tool.ainvoke({"image": image, "point": point})

    else:  # vqa (default)
        image = ctx.get("image", "")
        result = await vqa_tool.ainvoke({"image": image, "question": last_query, "metadata": metadata})

    # Format the final answer based on the tool output
    if tool_name == "vqa":
        final_answer = result.get("answer", "I was unable to analyse the image.")
    elif tool_name == "change_detection":
        summary = result.get("summary", "")
        pct = result.get("change_pct", 0)
        final_answer = (
            f"{summary}\n\n"
            f"**Change Extent:** {pct:.1f}% of the scene area shows significant change. "
            "The change mask overlay has been updated on the image viewer."
        )
    elif tool_name == "fusion":
        final_answer = result.get("verification_result", "Analysis complete.")
        agr = result.get("agreement_pct", 0)
        final_answer += f"\n\n**Optical-SAR Agreement Score:** {agr:.1f}%"
    elif tool_name == "segmentation":
        final_answer = (
            "Segmentation mask generated for the selected region. "
            "The isolated object boundary is now overlaid on the image viewer."
        )

    ai_message = AIMessage(content=final_answer)
    return {
        "tool_result": result,
        "final_answer": final_answer,
        "messages": [ai_message],
    }


# ─── Build the Graph ──────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Compile and return the LangGraph StateGraph."""
    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("executor", executor_node)

    builder.add_edge(START, "router")
    builder.add_edge("router", "executor")
    builder.add_edge("executor", END)

    return builder.compile()


# Singleton compiled graph
agent_graph = build_graph()
