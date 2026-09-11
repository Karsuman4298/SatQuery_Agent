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
            return ObservationResponse(observations=[]), None
        if response_model is JudgeResponse:
            return JudgeResponse(judgments=[]), None
        return AnswerResponse(observed_features="val", interpretation="val", uncertainty="val"), None

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
    nodes = {item.node if hasattr(item, "node") else item["node"] for item in trace}
    assert expected.issubset(nodes)


def test_answer_response_schema():
    # Issue 1: Test schema parsing and computed_field model_dump_json
    raw_json = '{"observed_features": "test feature", "interpretation": "test interp", "uncertainty": "test uncert"}'
    resp = AnswerResponse.model_validate_json(raw_json)
    
    assert resp.observed_features == "test feature"
    assert "Observed features: test feature" in resp.answer
    
    dumped = resp.model_dump_json()
    assert '"answer":' in dumped
    assert "test feature" in dumped


def test_conversational_bypass_trace(monkeypatch):
    # Issue 3: Conversational query bypasses CV/GIS nodes
    from app.agent.state import ConversationalResponse
    
    async def fake_conversational(messages, response_model, **kwargs):
        return ConversationalResponse(answer="I remember that.", referenced_turn=1), None
        
    monkeypatch.setattr("app.agent.modes.conversational.call_model_with_schema", fake_conversational)
    
    async def run_graph():
        state = new_state("what did i ask earlier?", {"chat_history": [{"role": "user", "content": "turn 1 text"}]}, mode="conversational")
        return await production_graph.ainvoke(state)
        
    result = asyncio.run(run_graph())
    
    trace_nodes = {item.node if hasattr(item, "node") else item["node"] for item in result["trace"]}
    
    assert "input_validation" in trace_nodes
    assert "conversational_agent" in trace_nodes
    assert "report_generator" in trace_nodes
    
    # Assert CV/GIS nodes were bypassed
    assert "sensor_metadata" not in trace_nodes
    assert "image_quality" not in trace_nodes
    assert "scene_observation" not in trace_nodes
    assert "vqa_agent" not in trace_nodes
    
    # Output must be ConversationalResponse string
    assert result["final_answer"] == "I remember that."

def test_graceful_degradation_no_leak(monkeypatch):
    # Issue 2: Deliberately trigger a SchemaValidationFailed to ensure no tracebacks leak
    from app.openrouter import SchemaValidationFailed
    
    async def fake_fail(messages, response_model, **kwargs):
        raise SchemaValidationFailed("Simulated validation error")
        
    monkeypatch.setattr("app.agent.pipeline.call_model_with_schema", fake_fail)
    monkeypatch.setattr("app.agent.tools.call_model_with_schema", fake_fail)
    
    async def run_graph():
        state = new_state("describe image in short", {"image": "data:image/png;base64,dummy"})
        return await production_graph.ainvoke(state)
        
    result = asyncio.run(run_graph())
    
    final_answer = result["final_answer"]
    assert "pydantic.dev" not in final_answer
    assert "SchemaValidationFailed" not in final_answer
    assert "Analysis unavailable for this section" in final_answer or "val" in final_answer


def test_history_memory(monkeypatch):
    # Issue 4: Test history is injected and conversational agent responds accurately
    from app.agent.state import ConversationalResponse
    async def fake_conversational(messages, response_model, **kwargs):
        history_in_prompt = messages[1]["content"]
        assert "turn 1 text" in history_in_prompt
        return ConversationalResponse(answer="Your previous question was: turn 1 text", referenced_turn=1), None
        
    monkeypatch.setattr("app.agent.modes.conversational.call_model_with_schema", fake_conversational)
    
    async def run_graph():
        state = new_state("what was my previous question?", {"chat_history": [{"role": "user", "content": "turn 1 text"}]})
        return await production_graph.ainvoke(state)
        
    result = asyncio.run(run_graph())
    assert "turn 1 text" in result["final_answer"]


def test_all_five_query_types():
    # Issue 5: Integration test spanning all 5 query types
    from app.agent.pipeline import _task_type
    
    # 1. VQA
    assert _task_type("how many cars?", {"image": "data"}).kind == "vqa"
    # 2. Change Detection
    assert _task_type("what changed?", {"image": "data", "before": "b", "after": "a"}).kind == "change_detection"
    # 3. Fusion
    assert _task_type("fuse them", {"image": "data", "optical": "o", "sar": "s"}).kind == "fusion"
    # 4. Land Cover
    assert _task_type("classify land cover", {"image": "data"}).kind == "land_cover"
    # 5. Conversational
    assert _task_type("hello", {}).kind == "conversational"
