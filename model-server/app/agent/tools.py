"""
Agent tool definitions for SatQuery multi-agent system.

Each tool wraps one of the model-server's core capabilities.
The LangGraph router selects the appropriate tool based on user intent.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import random
from typing import List, Optional

import httpx
import numpy as np
from langchain_core.tools import tool
from PIL import Image

from app.config import settings
from app.agent.state import AnswerResponse, ChangeSummaryResponse, FusionResponse
from app.openrouter import call_model_with_schema, image_data_uri


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _clean_b64(image_str: str) -> str:
    """Strip the data-URI prefix from a base64 image string if present."""
    if image_str.startswith("data:image"):
        return image_str.split(",", 1)[1]
    return image_str


def _encode_mask_png(mask: np.ndarray) -> str:
    from PIL import Image as PILImage
    import io, base64
    if mask.max() == 1:
        mask = mask * 255
        
    # Convert grayscale mask to an RGBA image where mask is neon green
    rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    rgba[mask > 0] = [52, 211, 153, 255] # Emerald-400
    
    img = PILImage.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"


def _remote_sensing_prompt(question: str) -> str:
    """Build a concise, evidence-bound prompt for satellite image interpretation."""
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

{format_guidance}
If evidence is insufficient, say so directly in the Uncertainty section."""


def _clean_model_answer(answer: str) -> str:
    """Remove common meta-prefaces produced by small instruction models."""
    cleaned = answer.strip()
    lower = cleaned.lower()
    markers = ("draft:", "final answer:", "answer:")
    positions = [(lower.rfind(marker), marker) for marker in markers if marker in lower]
    if positions:
        position, marker = max(positions)
        cleaned = cleaned[position + len(marker):].strip()
    for marker in ("I need to", "Let me", "The user is asking"):
        if cleaned.lower().startswith(marker.lower()):
            sentence_end = cleaned.find(".")
            if sentence_end >= 0:
                cleaned = cleaned[sentence_end + 1:].strip()
            break
    return cleaned


async def _call_gemini_vision(prompt: str, images: List[str], max_tokens: int = 512) -> Optional[str]:
    """Helper to call Gemini 2.0 Flash REST API with vision inputs."""
    gemini_key = settings.gemini_api_key
    if not gemini_key:
        return None

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

    parts = [{"text": prompt}]
    for img_str in images:
        clean = _clean_b64(img_str)
        if clean and len(clean) > 50 and clean != "dummy_b64":
            parts.append({
                "inline_data": {
                    "mime_type": "image/png",
                    "data": clean
                }
            })

    payload = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_tokens
        }
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(api_url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"⚠️ Gemini Vision API error: {e}")
        return None


# ─── Mock answer bank ─────────────────────────────────────────────────────────

MOCK_VQA_ANSWERS = {
    "building": (
        "I can see approximately 15-20 buildings in this region, primarily residential "
        "structures with some larger commercial buildings. The building density is moderate, "
        "typical of a suburban area."
    ),
    "road": (
        "There are several road segments visible in this region. I can identify a main "
        "arterial road running east-west and 3-4 secondary roads branching off. Total "
        "visible road length is approximately 2.3 km."
    ),
    "vegetation": (
        "The region shows mixed vegetation coverage. Approximately 40% of the area is "
        "covered by green vegetation, including agricultural fields in the southern portion "
        "and scattered tree cover in the north."
    ),
    "water": (
        "I can detect a water body in the southeastern portion of this region. It appears "
        "to be a small reservoir or pond, covering approximately 0.5 hectares."
    ),
    "flood": (
        "Flood inundation is evident across approximately 18% of the scene. Affected areas "
        "include low-lying agricultural land and two residential sectors near the river "
        "channel. SAR backscatter confirms standing water."
    ),
    "damage": (
        "There are signs of structural damage visible in the central portion of this region. "
        "Several buildings show altered spectral signatures consistent with roof damage or "
        "collapse. Approximately 8 structures appear affected."
    ),
    "crop": (
        "The image shows agricultural fields with mixed crop types. Healthy green vegetation "
        "dominates the northern parcels while the southern fields appear to be in early "
        "growth or recently harvested stages."
    ),
    "default": (
        "This satellite image shows a mixed urban-rural landscape. I can identify residential "
        "buildings, road networks, vegetation patches, and some open ground. The area appears "
        "to be in a tropical/subtropical region based on the vegetation patterns."
    ),
}


def _mock_vqa(question: str) -> dict:
    question_lower = question.lower()
    answer = MOCK_VQA_ANSWERS["default"]
    for key, ans in MOCK_VQA_ANSWERS.items():
        if key in question_lower:
            answer = ans
            break
    return {"answer": answer, "confidence": round(random.uniform(0.80, 0.92), 3), "evidence": []}


# ─── Tool 1: VQA ──────────────────────────────────────────────────────────────

from app.openrouter import call_model_with_schema, image_data_uri, with_graceful_degradation

@tool
async def vqa_tool(
    image: str,
    question: str,
    metadata: Optional[dict] = None,
    observations: Optional[List[str]] = None,
) -> dict:
    """
    Visual Question Answering on a single satellite image crop.

    Use this tool when the user asks a descriptive or classification question
    about what is visible in the current satellite image or region.

    Args:
        image: Base64-encoded satellite image (PNG/JPEG) or data-URI.
        question: Natural-language question about the image.

    Returns:
        dict with keys: answer (str), confidence (float), evidence (list).
    """
    metadata_context = json.dumps(metadata or {}, default=str)
    observation_context = "\n".join(f"- {item}" for item in (observations or []))
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

@tool
async def land_cover_tool(image: str, question: str = "Describe the land cover in this scene.") -> dict:
    """Deterministic land-cover classification over the scene."""
    import torch
    import torchvision.transforms as T
    from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large, DeepLabV3_MobileNet_V3_Large_Weights

    try:
        raw = base64.b64decode(_clean_b64(image))
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        
        weights = DeepLabV3_MobileNet_V3_Large_Weights.DEFAULT
        model = deeplabv3_mobilenet_v3_large(weights=weights)
        model.eval()
        
        preprocess = T.Compose([
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        input_tensor = preprocess(img).unsqueeze(0)
        with torch.no_grad():
            output = model(input_tensor)['out'][0]
        preds = output.argmax(0).numpy()
        
        total_pixels = preds.size
        classes, counts = np.unique(preds, return_counts=True)
        
        # Extremely simplified mapping for demonstration
        vocab = weights.meta["categories"]
        results = {}
        for cls_idx, count in zip(classes, counts):
            cls_name = vocab[cls_idx]
            pct = (count / total_pixels) * 100
            if pct > 1.0:
                results[cls_name] = round(pct, 1)
        
        stats_str = ", ".join(f"{k}: {v}%" for k, v in results.items())
        
        # VLM step to narrate the classification output
        narrate_result, reasoning = await call_model_with_schema([
            {"role": "system", "content": "You are a land cover analyst. Narrate the deterministic classification results provided by the CV model. Do not invent classes."},
            {"role": "user", "content": f"Classification output: {stats_str}. User asked: '{question}'. Narrate this in a brief sentence relevant to the user's question."}
        ], AnswerResponse, max_tokens=200, temperature=0.0)
        
        return {"answer": narrate_result.answer, "confidence": 0.0, "evidence": [], "internal_reasoning": reasoning}
    except Exception as exc:
        raise RuntimeError(f"Land cover classification failed: {exc}") from exc



# ─── Tool 2: Change Detection ─────────────────────────────────────────────────

@tool
async def change_analysis_tool(before: str, after: str, question: str = "Describe observable changes in a brief summary.") -> dict:
    """
    Bi-temporal change detection between two co-registered satellite images.

    Use this tool when the user uploads two images (before/after) and asks
    about changes, differences, or temporal analysis between them.

    Args:
        before: Base64-encoded 'before' satellite image.
        after: Base64-encoded 'after' satellite image.

    Returns:
        dict with keys: change_mask (base64 PNG), change_pct (float),
        summary (str describing what changed).
    """
    # Check identical images
    clean_b = _clean_b64(before).strip()
    clean_a = _clean_b64(after).strip()
    if clean_b == clean_a or not clean_b or not clean_a:
        mask_size = 256
        mask = np.zeros((mask_size, mask_size), dtype=np.uint8)
        return {
            "change_mask": _encode_mask_png(mask),
            "change_pct": 0.0,
            "summary": "No land-cover changes detected between identical image inputs."
        }

    # Calculate real pixel-difference mask
    def _diff_mask(b64_img_a: str, b64_img_b: str) -> tuple[str, float]:
        try:
            raw_a = base64.b64decode(_clean_b64(b64_img_a))
            raw_b = base64.b64decode(_clean_b64(b64_img_b))
            arr_a = np.array(Image.open(io.BytesIO(raw_a)).convert("L").resize((256, 256)))
            arr_b = np.array(Image.open(io.BytesIO(raw_b)).convert("L").resize((256, 256)))
            diff = np.abs(arr_a.astype(float) - arr_b.astype(float))
            if np.max(diff) < 5.0:
                mask = np.zeros((256, 256), dtype=np.uint8)
                return _encode_mask_png(mask), 0.0
            threshold = np.percentile(diff, 88)
            mask = (diff > max(threshold, 15.0)).astype(np.uint8) * 255
            pct = float(np.sum(mask > 0)) / float(mask.size) * 100.0
            return _encode_mask_png(mask), round(pct, 2)
        except Exception:
            mask = np.zeros((256, 256), dtype=np.uint8)
            return _encode_mask_png(mask), 0.0

    change_mask, change_pct = _diff_mask(before, after)

    try:
        summary_result, reasoning = await call_model_with_schema([
            {
                "role": "system",
                "content": "You are a careful remote-sensing change analyst. Narrate the provided change percentage in the context of the user's query. Do not infer causes or exact quantities beyond what is provided.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Computed pixel change: {change_pct}%. Image 1 is BEFORE and Image 2 is AFTER. User asked: '{question}'. Describe observable changes relevant to this question."},
                    {"type": "image_url", "image_url": {"url": image_data_uri(before)}},
                    {"type": "image_url", "image_url": {"url": image_data_uri(after)}},
                ],
            },
        ], ChangeSummaryResponse, max_tokens=800, temperature=0.0)
        return {"change_mask": change_mask, "change_pct": change_pct, "summary": summary_result.summary, "internal_reasoning": reasoning}
    except Exception:
        return {"change_mask": change_mask, "change_pct": change_pct, "summary": f"Change analysis unavailable for query: '{question}'"}


# ─── Tool 3: Optical-SAR Fusion ───────────────────────────────────────────────

@tool
async def fusion_analysis_tool(optical: str, sar: str, question: str = "") -> dict:
    """
    Cross-modal analysis of co-registered optical and SAR satellite imagery.

    Use this tool when the user provides both an optical image and a SAR image
    and asks about validation, agreement, flood mapping, or joint analysis.

    Args:
        optical: Base64-encoded optical image.
        sar: Base64-encoded SAR image.
        question: Optional question to guide the analysis.

    Returns:
        dict with keys: verification_result (str), confidence (float),
        agreement_pct (float), details (dict).
    """
    try:
        opt_raw = base64.b64decode(_clean_b64(optical))
        sar_raw = base64.b64decode(_clean_b64(sar))
        opt_arr = np.array(Image.open(io.BytesIO(opt_raw)).convert("L").resize((256, 256)))
        sar_arr = np.array(Image.open(io.BytesIO(sar_raw)).convert("L").resize((256, 256)))
        opt_norm = (opt_arr - np.mean(opt_arr)) / (np.std(opt_arr) + 1e-5)
        sar_norm = (sar_arr - np.mean(sar_arr)) / (np.std(sar_arr) + 1e-5)
        correlation = np.mean(opt_norm * sar_norm)
        agreement_pct = max(0.0, min(100.0, (correlation + 1) * 50))
    except Exception:
        agreement_pct = 50.0

    try:
        result, reasoning = await call_model_with_schema([
            {
                "role": "system",
                "content": "You are a careful multi-modal remote-sensing analyst. Compare only visible evidence in the optical and SAR images. Narrate the provided structural agreement score. Do not invent features or a different agreement percentage.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Computed structural agreement score is {agreement_pct:.1f}%. {question or 'Compare the optical and SAR images and report agreements, disagreements, and uncertainty.'}"},
                    {"type": "image_url", "image_url": {"url": image_data_uri(optical)}},
                    {"type": "image_url", "image_url": {"url": image_data_uri(sar)}},
                ],
            },
        ], FusionResponse, max_tokens=900, temperature=0.0)
        return {
            "verification_result": result.analysis,
            "confidence": 0.0,
            "agreement_pct": agreement_pct,
            "internal_reasoning": reasoning,
            "details": {"modalities": ["optical", "SAR"], "model": settings.vision_language_model},
        }
    except Exception:
        return {
            "verification_result": f"Analysis unavailable for query: '{question}'",
            "confidence": 0.0,
            "agreement_pct": agreement_pct,
            "details": {"modalities": ["optical", "SAR"]}
        }


# ─── Tool 4: Segmentation ─────────────────────────────────────────────────────

async def localize_region(image: str, region_description: str) -> Optional[dict]:
    """Call the VLM to get a bounding box for the region."""
    from app.agent.state import LocalizeResponse
    result, reasoning = await call_model_with_schema([
        {"role": "system", "content": "You are a localization module. Return a pixel bounding box for the described region. For complex or non-convex shapes like rivers, you MUST also provide an exact point (point_x, point_y) that falls STRICTLY on the requested object itself, NOT just the center of the bounding box. Never guess if you aren't confident."},
        {"role": "user", "content": [
            {"type": "text", "text": f"Locate: {region_description}"},
            {"type": "image_url", "image_url": {"url": image_data_uri(image)}}
        ]}
    ], LocalizeResponse, max_tokens=200, temperature=0.0)
    
    if result.bbox:
        return {"bbox": result.bbox.model_dump(), "internal_reasoning": reasoning}
    return {"bbox": None, "internal_reasoning": reasoning}

@tool
async def segmentation_tool(image: str, point: Optional[list] = None, region_description: Optional[str] = None) -> dict:
    """
    Segment a specific object or region in the satellite image using a click point or text description.

    Use this tool when the user clicks on a location in the image or describes a region and wants
    to isolate or outline a specific object (building, field, water body, etc.).

    Args:
        image: Base64-encoded satellite image.
        point: [x, y] pixel coordinates of the user's click on the image.
        region_description: Natural language description of the region to segment.

    Returns:
        dict with keys: mask (base64 PNG of the segmentation mask).
    """
    reasoning = None
    bboxes = None
    if not point and region_description:
        loc_result = await localize_region(image, region_description)
        reasoning = loc_result.get("internal_reasoning")
        if not loc_result.get("bbox"):
            return {"mask": "", "error": "please click the region", "internal_reasoning": reasoning}
        
        # Check if model provided a specific point on the object
        px, py = loc_result.get("point_x"), loc_result.get("point_y")
        if px is not None and py is not None and (px != 0 and py != 0):
            point = [px, py]
        else:
            # For complex shapes like rivers, the center of the bbox is often land.
            # But the edges of a tight bounding box MUST touch the object.
            # We generate 4 points on the edges of the bbox and use them as point prompts.
            bbox = loc_result["bbox"]
            cx = (bbox["x_min"] + bbox["x_max"]) / 2
            cy = (bbox["y_min"] + bbox["y_max"]) / 2
            # Offset slightly inward to ensure they are on the object, not outside
            dx = (bbox["x_max"] - bbox["x_min"]) * 0.05
            dy = (bbox["y_max"] - bbox["y_min"]) * 0.05
            
            p1 = [cx, bbox["y_min"] + dy]
            p2 = [cx, bbox["y_max"] - dy]
            p3 = [bbox["x_min"] + dx, cy]
            p4 = [bbox["x_max"] - dx, cy]
            
            # FastSAM predict takes a list of points. We'll pass all 4 edge points.
            point = p1 # We will actually pass multiple points below
            bboxes = None
            multi_points = [p1, p2, p3, p4]

    if not point and not bboxes and not 'multi_points' in locals():
        return {"mask": "", "error": "please click the region", "internal_reasoning": reasoning}

    try:
        import torch
        from ultralytics import SAM
        raw = base64.b64decode(_clean_b64(image))
        img = Image.open(io.BytesIO(raw)).convert("RGB")
        
        multi_points_scaled = []
        if 'multi_points' in locals():
            for p in multi_points:
                if max(p) > 1.0 and max(p) <= 1000:
                    multi_points_scaled.append([p[0] / 1000 * img.width, p[1] / 1000 * img.height])
                elif max(p) <= 1.0:
                    multi_points_scaled.append([p[0] * img.width, p[1] * img.height])
                else:
                    multi_points_scaled.append(p)
                    
        # Scale point if normalized to 1000 bins (legacy)
        elif point and max(point) > 1.0 and max(point) <= 1000:
            point = [point[0] / 1000 * img.width, point[1] / 1000 * img.height]
        elif point and max(point) <= 1.0:
            point = [point[0] * img.width, point[1] * img.height]
        
        # If coordinates are normalized to 1000 (Qwen's native bin format), scale to pixels
        if bboxes:
            b = bboxes[0]
            if max(b) > 1.0 and max(b) <= 1000:
                bboxes = [[b[0] / 1000 * img.width, b[1] / 1000 * img.height, b[2] / 1000 * img.width, b[3] / 1000 * img.height]]
            elif max(b) <= 1.0:
                bboxes = [[b[0] * img.width, b[1] * img.height, b[2] * img.width, b[3] * img.height]]

        model = SAM("mobile_sam.pt")
        # Run inference using box prompt or point prompt
        if bboxes:
            results = model.predict(img, bboxes=bboxes, verbose=False)
        elif multi_points_scaled:
            # labels=[1]*len ensures all points are positive prompts
            results = model.predict(img, points=multi_points_scaled, labels=[1]*len(multi_points_scaled), verbose=False)
        else:
            results = model.predict(img, points=[point], labels=[1], verbose=False)
        
        # Extract mask
        mask = np.zeros((img.height, img.width), dtype=np.uint8)
        conf = 0.9
        if results and len(results) > 0 and results[0].masks is not None:
            # Take the first mask
            m = results[0].masks.data[0].cpu().numpy()
            # SAM masks might be resized, resize back to original image size if needed
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
            # Add small padding
            pad = 10
            x_min, y_min = max(0, x_min - pad), max(0, y_min - pad)
            x_max, y_max = min(img.width, x_max + pad), min(img.height, y_max + pad)
            
            cropped = img.crop((x_min, y_min, x_max, y_max))
            buf = io.BytesIO()
            cropped.save(buf, format="PNG")
            cropped_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            
            try:
                caption_resp, _ = await call_model_with_schema([
                    {"role": "user", "content": [
                        {"type": "text", "text": "Caption the central object or region in this image crop in one brief phrase (e.g., 'a dense tree canopy', 'a large commercial building', 'a river segment')."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{cropped_b64}"}}
                    ]}
                ], AnswerResponse, max_tokens=30, temperature=0.0)
                caption = caption_resp.answer
            except Exception:
                pass

        return {"mask": mask_b64, "internal_reasoning": reasoning, "confidence": conf, "caption": caption}
    except Exception as exc:
        raise RuntimeError(f"Segmentation failed: {exc}") from exc
