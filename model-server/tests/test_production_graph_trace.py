"""Regression test: the production graph must execute each stage."""

from __future__ import annotations

import base64
import io
import asyncio

import numpy as np
from PIL import Image

from app.agent.production_graph import production_graph
from app.agent.state import AnswerResponse, JudgeResponse, ObservationResponse
from app.agent.pipeline import new_state


def test_full_query_records_per_node_trace(monkeypatch):
    image = Image.fromarray(np.full((64, 64, 3), 120, dtype=np.uint8), mode="RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

    async def fake_model(messages, response_model, **kwargs):
        if response_model is ObservationResponse:
            return ObservationResponse(observations=[])
        if response_model is JudgeResponse:
            return JudgeResponse(judgments=[])
        return AnswerResponse(answer="Validated remote-sensing answer.")

    monkeypatch.setattr("app.agent.pipeline.call_model_with_schema", fake_model)
    monkeypatch.setattr("app.agent.tools.call_model_with_schema", fake_model)

    async def run_graph():
        state = new_state("describe image in short", {"image": data_uri})
        return await production_graph.ainvoke(state)

    result = asyncio.run(run_graph())

    trace = result["trace"]
    expected = {
        "input_validation",
        "sensor_metadata",
        "image_quality",
        "scene_observation",
        "vqa_agent",
        "evidence_validator",
        "evidence_judge",
        "uncertainty_checker",
        "report_generator",
    }
    assert len(trace) >= len(expected)
    assert expected.issubset({item["node"] for item in trace})
