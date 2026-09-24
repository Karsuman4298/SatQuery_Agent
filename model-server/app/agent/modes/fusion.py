from langchain_core.tools import tool
from app.openrouter import call_model_with_schema, image_data_uri
from app.agent.state import FusionResponse, GraphState
from app.agent.pipeline import trace_node
import random
import base64
import io
from PIL import Image

def _clean_b64(uri: str) -> str:
    if "," in uri:
        return uri.split(",", 1)[1]
    return uri

@tool
async def fusion_tool(optical: str, sar: str, question: str = "Assess feature agreement between Optical and SAR images.") -> dict:
    """Compare Optical and SAR images for feature agreement."""
    if not optical or not sar or len(optical) < 100 or len(sar) < 100:
        from app.agent.exceptions import MalformedInputError
        raise MalformedInputError("Image payload is missing or corrupted.")
        
    try:
        raw_o = base64.b64decode(_clean_b64(optical))
        raw_s = base64.b64decode(_clean_b64(sar))
        try:
            img_o = Image.open(io.BytesIO(raw_o)).convert("L")
            img_s = Image.open(io.BytesIO(raw_s)).convert("L")
        except Exception:
            from app.agent.exceptions import MalformedInputError
            raise MalformedInputError("Image payload is corrupted and cannot be read.")
            
        # Optical reflectance and radar backscatter have different physical meaning.
        # Pixel brightness similarity cannot establish cross-sensor agreement.
        agreement_pct = None

        result, reasoning = await call_model_with_schema([
            {"role": "system", "content": "Analyze these OPTICAL and SAR images. Return a short summary regarding structure/feature agreement."},
            {"role": "user", "content": [
                {"type": "text", "text": f"Question: {question}"},
                {"type": "text", "text": "Optical Image:"},
                {"type": "image_url", "image_url": {"url": image_data_uri(optical)}},
                {"type": "text", "text": "SAR Image:"},
                {"type": "image_url", "image_url": {"url": image_data_uri(sar)}},
            ]}
        ], FusionResponse, max_tokens=200, temperature=0.0)
        
        return {"verification_result": result.analysis, "agreement_pct": agreement_pct, "evidence": [], "internal_reasoning": reasoning}
    except Exception as exc:
        raise RuntimeError("Optical–SAR specialist unavailable; no agreement estimate was produced.") from exc


async def fusion_node(state: GraphState) -> GraphState:
    trace_node(state, "fusion_agent")
    try:
        result = await fusion_tool.ainvoke({
            "optical": state.image_context.get("optical", ""),
            "sar": state.image_context.get("sar", ""),
            "question": state.user_query,
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
        "claim_id": "fusion-summary",
        "source_type": "interpretation",
        "text": result.get("verification_result", ""),
        "confidence": result.get("confidence", 0.0),
    })
    if state.trace and result.get("internal_reasoning"):
        state.trace[-1].reasoning = result.get("internal_reasoning")
    return state
