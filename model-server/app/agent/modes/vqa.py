from typing import Optional, List
import json
from langchain_core.tools import tool
from app.openrouter import call_model_with_schema, image_data_uri
from app.agent.state import AnswerResponse, GraphState
from app.agent.pipeline import trace_node

def _remote_sensing_prompt(question: str) -> str:
    short_request = any(
        phrase in question.lower()
        for phrase in ("in short", "briefly", "short description", "quickly")
    )
    format_guidance = (
        "Answer in 2-3 sentences, maximum 60 words."
        if short_request
        else "Use these headings: Observed features, Interpretation, Uncertainty. Keep the answer under 180 words."
    )
    return f"""Question: {question}

You are the final-answer component of a professional remote-sensing analysis system.
Respond with the answer only. Do not show reasoning, deliberation, self-correction, or statements such as 'let me think', 'the user is asking', or 'I should'.

Analyze only visual evidence in the supplied image. Use remote-sensing terminology where supported: land cover/use, terrain, texture, tone, pattern, shape, drainage, field morphology, built-up features, water, and vegetation. Distinguish observation from interpretation. Never identify an exact place, sensor, date, crop type, or quantitative measurement unless the image provides defensible evidence. For ambiguous requests such as 'what does this region specify?', describe the visible land-cover class and physiographic setting rather than guessing a location.

{format_guidance}"""


@tool
async def vqa_tool(
    image: str,
    question: str,
    metadata: Optional[dict] = None,
    observations: Optional[List[str]] = None,
) -> dict:
    """Answer a remote sensing question based on the provided image."""
    metadata_context = json.dumps(metadata or {}, default=str)
    observation_context = "\n".join(f"- {item}" for item in (observations or []))
    
    if not image or len(image) < 100:
        from app.agent.exceptions import MalformedInputError
        raise MalformedInputError("Image payload is missing or corrupted.")
        
    try:
        answer_result, reasoning = await call_model_with_schema([
            {
                "role": "system",
                "content": f"{_remote_sensing_prompt(question)}\n\nMetadata is authoritative only for file properties, not visual content:\n{metadata_context}\n\nValidated visual observations (use as evidence, do not expand beyond them):\n{observation_context or '- None available.'}",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Question: {question}"},
                    {"type": "image_url", "image_url": {"url": image_data_uri(image)}},
                ],
            },
        ], AnswerResponse, max_tokens=700, temperature=0.0)
        return {"answer": answer_result.answer, "confidence": 0.0, "evidence": [], "observations": observation_context or '- None available.', "internal_reasoning": reasoning}
    except Exception:
        return {"answer": f"Analysis unavailable for your question: '{question}'", "confidence": 0.0, "evidence": [], "observations": ""}


async def vqa_node(state: GraphState) -> GraphState:
    trace_node(state, "vqa_agent")
    try:
        result = await vqa_tool.ainvoke({
            "image": state.image_context.get("image", ""),
            "question": state.user_query,
            "metadata": state.image_context.get("metadata", {}),
            "observations": [obs.text for obs in state.scene_observations],
        })
    except Exception as e:
        from app.agent.exceptions import MalformedInputError
        if isinstance(e, MalformedInputError):
            state.validated = False
            state.validation_errors.append(str(e))
            return state
        raise
        
    state.tool_result = result
    state.interpretations.append({
        "claim_id": "vqa-answer",
        "source_type": "interpretation",
        "text": result.get("answer", ""),
        "confidence": result.get("confidence", 0.0),
    })
    if state.trace and result.get("internal_reasoning"):
        state.trace[-1].reasoning = result.get("internal_reasoning")
    return state
