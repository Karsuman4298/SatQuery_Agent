from __future__ import annotations
"""
VQA endpoint — Visual Question Answering on satellite image crops.
Wraps GeoChat model (or returns mock data when MOCK_MODELS=true).
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.state import AnswerResponse
from app.openrouter import call_model_with_schema, image_data_uri
from app.agent.tools import _clean_model_answer, _remote_sensing_prompt

router = APIRouter()


class VQARequest(BaseModel):
    image: str  # base64-encoded image crop
    question: str


class BBox(BaseModel):
    x_min: int
    y_min: int
    x_max: int
    y_max: int


class VQAEvidence(BaseModel):
    type: str = "bbox"
    bbox: BBox | None = None
    confidence: float
    label: str | None = None


class VQAResponse(BaseModel):
    answer: str
    confidence: float
    evidence: list[VQAEvidence] = []


@router.post("/vqa", response_model=VQAResponse)
async def run_vqa(request: VQARequest):
    """Run grounded visual question answering through OpenRouter."""
    answer = await call_model_with_schema([
        {
            "role": "system",
            "content": _remote_sensing_prompt(request.question),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": f"Question: {request.question}"},
                {"type": "image_url", "image_url": {"url": image_data_uri(request.image)}},
            ],
        },
    ], AnswerResponse, max_tokens=700, temperature=0.0)
    return VQAResponse(
        answer=_clean_model_answer(answer.answer),
        confidence=0.0,
        evidence=[]
    )