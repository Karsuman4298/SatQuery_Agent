import asyncio
import uuid
import base64
from app.agent.production_graph import production_graph
from app.agent.state import GraphState, QualityReport
import app.agent.pipeline
import app.agent.tools
import io
from PIL import Image

# Mock quality assessor
def mock_assess(*args, **kwargs):
    return {"usable": True, "blur_score": 0.0, "cloud_cover_pct": 0.0, "issues": []}
app.agent.pipeline.assess_image = mock_assess

async def mock_call_model(*args, **kwargs):
    schema = args[1]
    name = schema.__name__
    if name == "AnswerResponse":
        return schema(observed_features="mock", interpretation="mock", uncertainty="mock"), "mock reason"
    if name == "ChangeSummaryResponse":
        return schema(summary="mocked"), "mock reason"
    if name == "FusionResponse":
        return schema(analysis="mocked", agreement_pct=100.0), "mock reason"
    if name == "ObservationResponse":
        return schema(observations=[]), "mock reason"
    if name == "JudgeResponse":
        return schema(judgments=[]), "mock reason"
    if name == "ConversationalResponse":
        return schema(answer="mocked"), "mock reason"
    if name == "LocalizeResponse":
        from app.agent.state import BBox
        return schema(bbox=BBox(x_min=0, y_min=0, x_max=10, y_max=10)), "mock reason"
    return schema(), "mock reason"

app.agent.tools.call_model_with_schema = mock_call_model
app.agent.pipeline.call_model_with_schema = mock_call_model
app.agent.production_graph.call_model_with_schema = mock_call_model

# 64x64 image
buf = io.BytesIO()
Image.new("RGB", (64, 64), color="black").save(buf, format="PNG")
DUMMY_IMAGE = base64.b64encode(buf.getvalue()).decode("utf-8")

async def run_test():
    image_id_1 = str(uuid.uuid4())
    image_id_2 = str(uuid.uuid4())
    dummy_image_1 = DUMMY_IMAGE
    dummy_image_2 = DUMMY_IMAGE

    print("\n--- Turn 1: what does this show? ---")
    state1 = GraphState(
        session_id="s1", query_id="q1", user_query="what does this show?",
        image_context={"image": dummy_image_1, "metadata": {"image_id": image_id_1}, "chat_history": []}
    )
    res1 = await production_graph.ainvoke(state1)
    nodes1 = [t.node for t in res1["trace"]]
    assert "vqa_agent" in nodes1
    assert "segmentation_agent" not in nodes1
    print("Turn 1 correct. Nodes:", nodes1)

    print("\n--- Turn 2: segment the water body in the top left ---")
    state2 = GraphState(
        session_id="s1", query_id="q2", user_query="segment the water body in the top left",
        image_context={"image": dummy_image_1, "metadata": {"image_id": image_id_1}, "chat_history": []}
    )
    res2 = await production_graph.ainvoke(state2)
    nodes2 = [t.node for t in res2["trace"]]
    assert "segmentation_agent" in nodes2
    assert "vqa_agent" not in nodes2
    # Verify caching happened
    obs_trace = [t for t in res2["trace"] if t.node == "scene_observation"][0]
    assert obs_trace.reasoning == "Cache hit - skipped VLM call."
    print("Turn 2 correct. Nodes:", nodes2)

    print("\n--- Turn 3: what changed between this and the second image? ---")
    state3 = GraphState(
        session_id="s1", query_id="q3", user_query="what changed between this and the second image?",
        image_context={"before": dummy_image_1, "after": dummy_image_2, "metadata": {"image_id": image_id_2}, "chat_history": []}
    )
    res3 = await production_graph.ainvoke(state3)
    nodes3 = [t.node for t in res3["trace"]]
    assert "change_detection_agent" in nodes3
    assert "segmentation_agent" not in nodes3
    print("Turn 3 correct. Nodes:", nodes3)

    print("\n--- Turn 4: what does this show? ---")
    state4 = GraphState(
        session_id="s1", query_id="q4", user_query="what does this show?",
        image_context={"image": dummy_image_1, "metadata": {"image_id": image_id_1}, "chat_history": []}
    )
    res4 = await production_graph.ainvoke(state4)
    nodes4 = [t.node for t in res4["trace"]]
    assert "vqa_agent" in nodes4
    assert "change_detection_agent" not in nodes4
    # Verify caching happened
    obs_trace4 = [t for t in res4["trace"] if t.node == "scene_observation"][0]
    assert obs_trace4.reasoning == "Cache hit - skipped VLM call."
    print("Turn 4 correct. Nodes:", nodes4)

    print("\nALL DYNAMIC ROUTING TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_test())
