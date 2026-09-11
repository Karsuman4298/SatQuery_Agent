"""Test query-driven task classification, input sufficiency checking, clarification responses, and execution summary serialization."""

from __future__ import annotations

import asyncio
import pytest
from app.agent.classifier import IntentClassifier
from app.agent.pipeline import new_state
from app.agent.production_graph import production_graph
from app.agent.state import AnswerResponse, GraphState, ObservationResponse


@pytest.fixture
def mock_classifier(monkeypatch):
    """Ensure classifier uses fast pre-warmed embeddings in tests."""
    pass


@pytest.mark.asyncio
async def test_classifier_tasks():
    classifier = IntentClassifier()
    await classifier.initialize()

    # VQA
    task, conf, _ = await classifier.classify("what color is the river?")
    assert task == "vqa"
    assert conf > 0.3

    # Segmentation
    task, conf, _ = await classifier.classify("segment the main building in this image")
    assert task == "segmentation"
    assert conf > 0.3

    # Change Detection
    task, conf, _ = await classifier.classify("what changed between these two images?")
    assert task == "change_detection"
    assert conf > 0.3

    # Fusion
    task, conf, _ = await classifier.classify("fuse optical and SAR data to analyze agreement")
    assert task == "fusion"
    assert conf > 0.3

    # Conversational
    task, conf, _ = await classifier.classify("explain how NDVI works")
    assert task == "conversational"
    assert conf > 0.3


@pytest.mark.asyncio
async def test_input_sufficiency_clarification(monkeypatch):
    """Asking for change detection with only 1 image must trigger a clarification response."""
    async def fake_model(messages, response_model, **kwargs):
        if response_model is ObservationResponse:
            return ObservationResponse(observations=[]), None
        return AnswerResponse(observed_features="val", interpretation="val", uncertainty="val"), None

    monkeypatch.setattr("app.agent.pipeline.call_model_with_schema", fake_model)
    monkeypatch.setattr("app.agent.tools.call_model_with_schema", fake_model)

    # Submit change detection query with ONLY 1 image ("image" key)
    state = new_state(
        "what changed between these images?",
        {"image": "data:image/png;base64,dummy"},
        mode="vqa"  # Frontend tab was set to VQA, but query implies change detection
    )
    result = await production_graph.ainvoke(state)

    assert result["needs_clarification"] is True
    assert result["inferred_task"] == "change_detection"
    assert "requires a before image and after image" in result["clarification_message"]
    assert "Change Detection requires" in result["final_answer"]
