import io
import base64
import numpy as np
from PIL import Image
from typing import Optional
from langchain_core.tools import tool
from app.openrouter import call_model_with_schema, image_data_uri
from app.agent.state import LocalizeResponse, AnswerResponse, GraphState
from app.agent.pipeline import trace_node

def _clean_b64(uri: str) -> str:
    if "," in uri:
        return uri.split(",", 1)[1]
    return uri

def _encode_mask_png(mask: np.ndarray) -> str:
    if mask.max() <= 1:
        mask = mask * 255
    rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    rgba[mask > 0] = [52, 211, 153, 255] # Emerald-400
    from PIL import Image as PILImage
    img = PILImage.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

async def localize_region(image: str, region_description: str) -> dict:
    result, reasoning = await call_model_with_schema([
        {"role": "system", "content": "Return the bounding box and a central point for the requested object."},
        {"role": "user", "content": [
            {"type": "text", "text": f"Locate: {region_description}"},
            {"type": "image_url", "image_url": {"url": image_data_uri(image)}},
        ]}
    ], LocalizeResponse, max_tokens=150)
    return {"bbox": result.bbox.model_dump() if result.bbox else None, "point_x": result.point_x, "point_y": result.point_y, "internal_reasoning": reasoning}

@tool
async def segmentation_tool(image: str, point: Optional[list] = None, region_description: Optional[str] = None) -> dict:
    """Segment an object in the image based on point or description."""
    if not image or len(image) < 100:
        from app.agent.exceptions import MalformedInputError
        raise MalformedInputError("Image payload is missing or corrupted.")
        
    reasoning = None
    bboxes = None
    if not point and region_description:
        loc_result = await localize_region(image, region_description)
        reasoning = loc_result.get("internal_reasoning")
        if not loc_result.get("bbox"):
            return {"mask": "", "error": "please click the region", "internal_reasoning": reasoning}
        
        px, py = loc_result.get("point_x"), loc_result.get("point_y")
        if px is not None and py is not None and (px != 0 and py != 0):
            point = [px, py]
        elif loc_result.get("bbox"):
            bbox = loc_result["bbox"]
            # Fallback to the exact center of the bounding box
            cx = (bbox["x_min"] + bbox["x_max"]) / 2
            cy = (bbox["y_min"] + bbox["y_max"]) / 2
            point = [cx, cy]
            bboxes = None

    if not point and not bboxes and not 'multi_points' in locals():
        return {"mask": "", "error": "please click the region", "internal_reasoning": reasoning}

    try:
        import torch
        from ultralytics import SAM
        raw = base64.b64decode(_clean_b64(image))
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            from app.agent.exceptions import MalformedInputError
            raise MalformedInputError("Image payload is corrupted and cannot be read.")
            
        if point and max(point) > 1.0 and max(point) <= 1000:
            point = [point[0] / 1000 * img.width, point[1] / 1000 * img.height]
        elif point and max(point) <= 1.0:
            point = [point[0] * img.width, point[1] * img.height]
        
        if bboxes:
            b = bboxes[0]
            if max(b) > 1.0 and max(b) <= 1000:
                bboxes = [[b[0] / 1000 * img.width, b[1] / 1000 * img.height, b[2] / 1000 * img.width, b[3] / 1000 * img.height]]
            elif max(b) <= 1.0:
                bboxes = [[b[0] * img.width, b[1] * img.height, b[2] * img.width, b[3] * img.height]]

        model = SAM("mobile_sam.pt")
        if bboxes:
            results = model.predict(img, bboxes=bboxes, verbose=False)
        else:
            results = model.predict(img, points=[point], labels=[1], verbose=False)
        
        mask = np.zeros((img.height, img.width), dtype=np.uint8)
        conf = 0.9
        if results and len(results) > 0 and results[0].masks is not None:
            m = results[0].masks.data[0].cpu().numpy()
            from PIL import Image as PILImage
            m_img = PILImage.fromarray((m * 255).astype(np.uint8)).resize((img.width, img.height), resample=PILImage.NEAREST)
            mask = np.array(m_img)
            
            if hasattr(results[0], "boxes") and results[0].boxes is not None and len(results[0].boxes.conf) > 0:
                conf = float(results[0].boxes.conf[0].cpu().numpy())

        mask_b64 = _encode_mask_png(mask)
        caption = "segmented region"
        
        ys, xs = np.where(mask > 0)
        if len(ys) > 0 and len(xs) > 0:
            x_min, x_max = int(np.min(xs)), int(np.max(xs))
            y_min, y_max = int(np.min(ys)), int(np.max(ys))
            pad = 10
            x_min, y_min = max(0, x_min - pad), max(0, y_min - pad)
            x_max, y_max = min(img.width, x_max + pad), min(img.height, y_max + pad)
            
            cropped = img.crop((x_min, y_min, x_max, y_max))
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            cropped_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            
            try:
                from app.agent.state import CaptionResponse
                caption_resp, _ = await call_model_with_schema([
                    {"role": "user", "content": [
                        {"type": "text", "text": "Caption the central object or region in this image crop in one brief phrase (e.g., 'a dense tree canopy', 'a large commercial building', 'a river segment')."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cropped_b64}"}}
                    ]}
                ], CaptionResponse, max_tokens=30, temperature=0.0)
                caption = caption_resp.caption
            except Exception:
                pass

        return {"mask": mask_b64, "internal_reasoning": reasoning, "confidence": conf, "caption": caption}
    except Exception as exc:
        from app.agent.exceptions import MalformedInputError
        if isinstance(exc, MalformedInputError):
            raise
        raise RuntimeError(f"Segmentation failed: {exc}") from exc


async def segmentation_node(state: GraphState) -> GraphState:
    trace_node(state, "segmentation_agent")
    try:
        result = await segmentation_tool.ainvoke({
            "image": state.image_context.get("image", ""),
            "point": state.image_context.get("click_point"),
            "region_description": state.user_query,
        })
    except Exception as e:
        from app.agent.exceptions import MalformedInputError
        if isinstance(e, MalformedInputError):
            state.validated = False
            state.validation_errors.append(str(e))
            return state
        raise
    
    if "error" in result:
        state.errors.append({"node": "segmentation_agent", "error": result["error"], "recovered": False})
        state.tool_result = {"answer": result["error"], "status": "not_found", "internal_reasoning": result.get("internal_reasoning")}
    else:
        state.tool_result = result
        state.interpretations.append({
            "claim_id": "segmentation-mask",
            "source_type": "interpretation",
            "text": f"Segmented region based on: {state.user_query}",
            "confidence": result.get("confidence", 0.9),
        })
    if state.trace and result.get("internal_reasoning"):
        state.trace[-1].reasoning = result.get("internal_reasoning")
    return state
