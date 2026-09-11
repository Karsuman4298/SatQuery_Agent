import pytest
import numpy as np
from app.agent.production_graph import production_graph
from app.agent.state import GraphState, TaskType, Observation
from unittest.mock import patch, MagicMock
from app.agent.pipeline import _OBSERVATION_CACHE

# Dummy base64 images for testing
dummy_image_1 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
dummy_image_2 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII="

@pytest.mark.asyncio
@patch("app.agent.modes.vqa.call_model_with_schema", side_effect=Exception("Test offline API"))
@patch("app.agent.pipeline.assess_image", return_value={"usable": True})
async def test_same_image_different_queries_vqa(mock_assess, mock_call_schema):
    # Test VQA
    state1 = GraphState(
        user_query="Are there any buildings?",
        image_context={"image": dummy_image_1, "metadata": {"image_id": "img1", "crs": "EPSG:4326", "sensor": "test"}},
        task_type=TaskType(kind="vqa")
    )
    res1 = await production_graph.ainvoke(state1)
    
    state2 = GraphState(
        user_query="Are there any rivers?",
        image_context={"image": dummy_image_1, "metadata": {"image_id": "img1", "crs": "EPSG:4326", "sensor": "test"}},
        task_type=TaskType(kind="vqa")
    )
    res2 = await production_graph.ainvoke(state2)
    
    # Assert responses are not identical
    assert res1["final_answer"] != res2["final_answer"]
    # Assert semantic relevance
    assert "buildings" in res1["final_answer"].lower()
    assert "rivers" in res2["final_answer"].lower()

@pytest.mark.asyncio
@patch("app.agent.modes.vqa.call_model_with_schema")
@patch("app.agent.pipeline.call_model_with_schema")
@patch("app.agent.pipeline.assess_image", return_value={"usable": True})
async def test_different_images_same_query_vqa(mock_assess, mock_pipeline_call, mock_tools_call):
    class MockObsResponse1:
        observations = [Observation(text="Image 1 is dark", confidence=1.0)]
        judgments = []
        answer = "Image 1 observation"
        
    class MockObsResponse2:
        observations = [Observation(text="Image 2 is bright", confidence=1.0)]
        judgments = []
        answer = "Image 2 observation"
        
    # We will use side_effect to return different values for the tools call
    mock_tools_call.side_effect = [
        (MockObsResponse1(), "reasoning"), # vqa_tool
        (MockObsResponse2(), "reasoning")  # vqa_tool
    ]
    mock_pipeline_call.side_effect = [
        (MockObsResponse1(), "reasoning"), # observe_scene
        (MockObsResponse1(), "reasoning"), # judge_claims
        (MockObsResponse2(), "reasoning"), # observe_scene
        (MockObsResponse2(), "reasoning")  # judge_claims
    ]

    state1 = GraphState(
        user_query="Describe the scene",
        image_context={"image": dummy_image_1, "metadata": {"image_id": "img1", "crs": "EPSG:4326", "sensor": "test"}},
        task_type=TaskType(kind="vqa")
    )
    res1 = await production_graph.ainvoke(state1)
    
    state2 = GraphState(
        user_query="Describe the scene",
        image_context={"image": dummy_image_2, "metadata": {"image_id": "img2", "crs": "EPSG:4326", "sensor": "test"}},
        task_type=TaskType(kind="vqa")
    )
    res2 = await production_graph.ainvoke(state2)
    
    assert res1["final_answer"] != res2["final_answer"]
    assert "Image 1 observation" in res1["final_answer"]
    assert "Image 2 observation" in res2["final_answer"]

@pytest.mark.asyncio
@patch("app.agent.modes.vqa.call_model_with_schema")
@patch("app.agent.pipeline.call_model_with_schema")
@patch("app.agent.pipeline.assess_image", return_value={"usable": True})
async def test_full_scene_vs_cropped_region_cache(mock_assess, mock_pipeline_call, mock_tools_call):
    # Test 3: Cache key collision fix
    class MockObsResponse:
        observations = []
        judgments = []
        answer = "Mocked answer"
    
    mock_pipeline_call.return_value = (MockObsResponse(), "reasoning")
    mock_tools_call.return_value = (MockObsResponse(), "reasoning")
    
    # Clear cache before test
    _OBSERVATION_CACHE.clear()
    
    # 1. Full Scene Query
    state1 = GraphState(
        user_query="Describe the scene",
        image_context={"image": dummy_image_1, "region_name": "", "metadata": {"image_id": "img_same"}},
        task_type=TaskType(kind="vqa")
    )
    await production_graph.ainvoke(state1)
    
    # Observe scene is called, then tool is called, etc.
    assert mock_pipeline_call.call_count > 0
    initial_call_count = mock_pipeline_call.call_count
    
    # 2. Cropped Region Query (same image_id, but different payload)
    state2 = GraphState(
        user_query="Describe the region",
        image_context={"image": dummy_image_2, "region_name": "Region A", "metadata": {"image_id": "img_same"}},
        task_type=TaskType(kind="vqa")
    )
    await production_graph.ainvoke(state2)
    
    # Call count should increase because region_name cache key is different!
    assert mock_pipeline_call.call_count > initial_call_count
    
    # The cache keys should be different
    # Since we use MD5 now, let's just assert length increased
    assert len(_OBSERVATION_CACHE) == 2

@pytest.mark.asyncio
@patch("app.agent.modes.vqa.call_model_with_schema")
@patch("app.agent.pipeline.call_model_with_schema")
@patch("app.agent.pipeline.assess_image", return_value={"usable": True})
async def test_md5_cache_different_crops_same_name(mock_assess, mock_pipeline_call, mock_tools_call):
    # Test 4: Two different crops, same image_id, SAME region_name.
    # The cache should not hit because the image bytes differ.
    class MockObsResponse:
        observations = [Observation(text="Mock", confidence=1.0)]
        judgments = []
        answer = "Mocked answer"
    
    mock_pipeline_call.return_value = (MockObsResponse(), "reasoning")
    mock_tools_call.return_value = (MockObsResponse(), "reasoning")
    
    _OBSERVATION_CACHE.clear()
    
    # Crop 1
    state1 = GraphState(
        user_query="Describe",
        image_context={"image": dummy_image_1, "region_name": "SharedRegion", "metadata": {"image_id": "img_same"}},
        task_type=TaskType(kind="vqa")
    )
    await production_graph.ainvoke(state1)
    
    initial_call_count = mock_pipeline_call.call_count
    
    # Crop 2 (different image payload, dummy_image_2)
    state2 = GraphState(
        user_query="Describe",
        image_context={"image": dummy_image_2, "region_name": "SharedRegion", "metadata": {"image_id": "img_same"}},
        task_type=TaskType(kind="vqa")
    )
    await production_graph.ainvoke(state2)
    
    # Call count should increase because image payload changed!
    assert mock_pipeline_call.call_count > initial_call_count
    assert len(_OBSERVATION_CACHE) == 2

@pytest.mark.asyncio
@patch("app.agent.modes.vqa.call_model_with_schema")
@patch("app.agent.modes.change_detection.call_model_with_schema")
@patch("app.agent.modes.fusion.call_model_with_schema")
async def test_tool_error_handling(mock_fusion, mock_change, mock_vqa):
    # Test 5: Verify tool error handling and dynamic fallbacks
    # Force VLM exception
    mock_vqa.side_effect = Exception("Simulated unrecoverable VLM failure")
    mock_change.side_effect = Exception("Simulated unrecoverable VLM failure")
    mock_fusion.side_effect = Exception("Simulated unrecoverable VLM failure")
    
    # 1. vqa_tool
    from app.agent.modes.vqa import vqa_tool
    vqa_res = await vqa_tool.ainvoke({"image": dummy_image_1, "question": "What is here?"})
    assert "Analysis unavailable for your question: 'What is here?'" in vqa_res["answer"]
    assert "Exception" not in vqa_res["answer"]
    assert "Simulated" not in vqa_res["answer"]
    
    # 2. change_analysis_tool
    from app.agent.modes.change_detection import change_analysis_tool
    change_res = await change_analysis_tool.ainvoke({"before": dummy_image_1, "after": dummy_image_2, "question": "What changed?"})
    assert "Change analysis unavailable for query: 'What changed?'" in change_res["summary"]
    assert "Exception" not in change_res["summary"]
    
    # 3. fusion_analysis_tool
    from app.agent.modes.fusion import fusion_analysis_tool
    fusion_res = await fusion_analysis_tool.ainvoke({"optical": dummy_image_1, "sar": dummy_image_2, "question": "Any fusion?"})
    assert "Analysis unavailable for query: 'Any fusion?'" in fusion_res["verification_result"]
    assert "Exception" not in fusion_res["verification_result"]
