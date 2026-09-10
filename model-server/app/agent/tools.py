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


def _encode_mask_png(mask: "np.ndarray") -> str:
    """Encode a numpy uint8 mask array as a base64 PNG string."""
    img = Image.fromarray(mask)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


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
    answer_result = await call_model_with_schema([
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
    return {"answer": _clean_model_answer(answer_result.answer), "confidence": 0.0, "evidence": [], "observations": observation_context or '- None available.'}



# ─── Tool 2: Change Detection ─────────────────────────────────────────────────

@tool
async def change_analysis_tool(before: str, after: str) -> dict:
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

    summary_result = await call_model_with_schema([
        {
            "role": "system",
            "content": "You are a careful remote-sensing change analyst. Describe only visible differences; do not infer causes or exact quantities beyond the supplied pixel mask.",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Image 1 is BEFORE and Image 2 is AFTER. Describe observable changes and uncertainty."},
                {"type": "image_url", "image_url": {"url": image_data_uri(before)}},
                {"type": "image_url", "image_url": {"url": image_data_uri(after)}},
            ],
        },
    ], ChangeSummaryResponse, max_tokens=800, temperature=0.0)

    return {"change_mask": change_mask, "change_pct": change_pct, "summary": summary_result.summary}


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
    result = await call_model_with_schema([
        {
            "role": "system",
            "content": "You are a careful multi-modal remote-sensing analyst. Compare only visible evidence in the optical and SAR images. Do not invent features or an agreement percentage; state when agreement cannot be estimated reliably.",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question or "Compare the optical and SAR images and report agreements, disagreements, and uncertainty."},
                {"type": "image_url", "image_url": {"url": image_data_uri(optical)}},
                {"type": "image_url", "image_url": {"url": image_data_uri(sar)}},
            ],
        },
    ], FusionResponse, max_tokens=900, temperature=0.0)
    return {
        "verification_result": result.analysis,
        "confidence": 0.0,
        "agreement_pct": result.agreement_pct or 0.0,
        "details": {"modalities": ["optical", "SAR"], "model": settings.vision_language_model},
    }

    model_id = "Qwen/Qwen2-VL-7B-Instruct"
    api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}/v1/chat/completions"

    opt_uri = optical if optical.startswith("data:image") else f"data:image/png;base64,{optical}"
    sar_uri = sar if sar.startswith("data:image") else f"data:image/png;base64,{sar}"

    user_q = question or "Analyze and cross-validate both images. Report agreement, disagreement, and any unique information each modality provides."

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You are an expert in multi-modal remote sensing. "
                            "You are provided with two co-registered images of the same scene: "
                            "Image 1 is optical/multispectral and Image 2 is SAR (Synthetic Aperture Radar). "
                            f"Task: {user_q}\n"
                            "Provide your analysis in a structured paragraph. "
                            "End with an estimated agreement percentage (0-100%)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": opt_uri}},
                    {"type": "image_url", "image_url": {"url": sar_uri}},
                ],
            }
        ],
        "max_tokens": 512,
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                api_url,
                headers={"Authorization": f"Bearer {hf_token}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            result_text = resp.json()["choices"][0]["message"]["content"].strip()

        # Parse agreement percentage from response
        import re
        match = re.search(r"(\d{1,3})\s*%", result_text)
        agr_pct = float(match.group(1)) if match else 75.0

        return {
            "verification_result": result_text,
            "confidence": 0.88,
            "agreement_pct": agr_pct,
            "details": {"modalities": ["optical", "SAR"], "model_used": model_id},
        }
    except Exception:
        raise


# ─── Tool 4: Segmentation ─────────────────────────────────────────────────────

@tool
async def segmentation_tool(image: str, point: list) -> dict:
    """
    Segment a specific object or region in the satellite image using a click point.

    Use this tool when the user clicks on a location in the image and wants
    to isolate or outline a specific object (building, field, water body, etc.).

    Args:
        image: Base64-encoded satellite image.
        point: [x, y] pixel coordinates of the user's click on the image.

    Returns:
        dict with keys: mask (base64 PNG of the segmentation mask).
    """
    # Deterministic local mask until a real SAM2 checkpoint is configured.
    try:
        raw = base64.b64decode(_clean_b64(image))
        arr = np.array(Image.open(io.BytesIO(raw)).convert("L").resize((256, 256)))
        mask = np.zeros_like(arr, dtype=np.uint8)
        cx = min(max(int(point[0] * 256 / max(arr.shape[1], 1)), 5), 250)
        cy = min(max(int(point[1] * 256 / max(arr.shape[0], 1)), 5), 250)
        seed_val = arr[cy, cx]
        tolerance = 30
        flood_mask = np.abs(arr.astype(int) - int(seed_val)) < tolerance
        mask[flood_mask] = 255
        # Restrict to a reasonable radius from click
        y_grid, x_grid = np.ogrid[-cy: 256 - cy, -cx: 256 - cx]
        radius_mask = (x_grid * x_grid + y_grid * y_grid) <= 70 ** 2
        mask[~radius_mask] = 0
        return {"mask": _encode_mask_png(mask)}
    except Exception as exc:
        raise RuntimeError(f"Segmentation failed: {exc}") from exc
