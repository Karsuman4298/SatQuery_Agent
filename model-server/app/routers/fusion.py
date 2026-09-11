from __future__ import annotations
"""Optical-SAR fusion endpoint backed by the configured OpenRouter model."""

from fastapi import APIRouter
from pydantic import BaseModel
from app.agent.state import FusionResponse as FusionAnalysisResponse
from app.openrouter import call_model_with_schema, image_data_uri
router = APIRouter()


class FusionRequest(BaseModel):
    optical: str  # base64-encoded optical image crop
    sar: str  # base64-encoded SAR image crop


class FusionResponse(BaseModel):
    verification_result: str
    confidence: float
    agreement_pct: float
    details: dict | None = None


@router.post("/fusion", response_model=FusionResponse)
async def optical_sar_fusion(request: FusionRequest):
    """Compare optical and SAR imagery using the configured vision model."""
    answer = await call_model_with_schema([
        {
            "role": "system",
            "content": "You are a careful multi-modal remote-sensing analyst. Compare only visible evidence in the optical and SAR images. Do not invent features or an agreement percentage; state when agreement cannot be estimated reliably.",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Compare the optical and SAR images. Report agreements, disagreements, and uncertainty. Give an agreement percentage only if visually justified."},
                {"type": "image_url", "image_url": {"url": image_data_uri(request.optical)}},
                {"type": "image_url", "image_url": {"url": image_data_uri(request.sar)}},
            ],
        },
    ], FusionAnalysisResponse, max_tokens=900, temperature=0.0)
    return FusionResponse(
        verification_result=answer.analysis,
        confidence=0.0,
        agreement_pct=answer.agreement_pct or 0.0,
        details={"model": "configured OpenRouter vision-language model"},
    )

