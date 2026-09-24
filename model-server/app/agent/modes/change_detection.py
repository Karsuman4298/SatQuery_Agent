from langchain_core.tools import tool
import io
import base64
from PIL import Image
from app.openrouter import call_model_with_schema, image_data_uri
from app.agent.state import ChangeSummaryResponse, GraphState
from app.agent.pipeline import trace_node

def _clean_b64(uri: str) -> str:
    if "," in uri:
        return uri.split(",", 1)[1]
    return uri

@tool
async def change_analysis_tool(before: str, after: str, question: str = "Describe observable changes in a brief summary.") -> dict:
    """Analyze two images (before and after) for changes."""
    if not before or not after or len(before) < 100 or len(after) < 100:
        from app.agent.exceptions import MalformedInputError
        raise MalformedInputError("Image payload is missing or corrupted.")
        
    try:
        raw_b = base64.b64decode(_clean_b64(before))
        raw_a = base64.b64decode(_clean_b64(after))
        try:
            img_b = Image.open(io.BytesIO(raw_b)).convert("RGB")
            img_a = Image.open(io.BytesIO(raw_a)).convert("RGB")
        except Exception:
            from app.agent.exceptions import MalformedInputError
            raise MalformedInputError("Image payload is corrupted and cannot be read.")
        
        import numpy as np
        import hashlib
        print(f"[DEBUG] before hash: {hashlib.md5(raw_b).hexdigest()}")
        print(f"[DEBUG] after hash: {hashlib.md5(raw_a).hexdigest()}")
        arr_b = np.array(img_b.resize((256, 256))).astype(np.float32)
        arr_a = np.array(img_a.resize((256, 256))).astype(np.float32)
        diff = np.abs(arr_a - arr_b).mean(axis=2)
        print(f"[DEBUG] diff sum: {diff.sum()}")
        threshold = 30.0
        change_mask = (diff > threshold).astype(np.uint8)
        change_pct = float(change_mask.mean()) * 100
        
        rgba = np.zeros((256, 256, 4), dtype=np.uint8)
        rgba[change_mask > 0] = [255, 185, 87, 150]
        mask_img = Image.fromarray(rgba, mode="RGBA").resize(img_a.size, Image.Resampling.NEAREST)
        buf = io.BytesIO()
        mask_img.save(buf, format="PNG")
        mask_uri = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
        
        result, reasoning = await call_model_with_schema([
            {"role": "system", "content": "Analyze these BEFORE and AFTER satellite images. Respond with ONLY the summary string as requested."},
            {"role": "user", "content": [
                {"type": "text", "text": f"Question: {question}"},
                {"type": "image_url", "image_url": {"url": image_data_uri(before)}},
                {"type": "image_url", "image_url": {"url": image_data_uri(after)}},
            ]}
        ], ChangeSummaryResponse, max_tokens=200, temperature=0.0)
        
        return {"summary": result.summary, "change_pct": change_pct, "change_mask": mask_uri, "limitations": "Exploratory RGB difference at threshold 30/255 and 256px; includes illumination and registration effects. Not semantic land-cover change.", "evidence": [], "internal_reasoning": reasoning}
    except Exception as exc:
        raise RuntimeError("Change specialist unavailable; no change estimate was produced.") from exc


async def change_node(state: GraphState) -> GraphState:
    trace_node(state, "change_detection_agent")
    try:
        result = await change_analysis_tool.ainvoke({
            "before": state.image_context.get("before", ""),
            "after": state.image_context.get("after", ""),
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
        "claim_id": "change-summary",
        "source_type": "interpretation",
        "text": result.get("summary", ""),
        "confidence": 0.0,
    })
    if state.trace and result.get("internal_reasoning"):
        state.trace[-1].reasoning = result.get("internal_reasoning")
    return state
