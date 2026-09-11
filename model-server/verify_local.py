import asyncio
import uuid
import base64
from app.agent.production_graph import production_graph
import app.tools.quality
from app.agent.state import QualityReport, GraphState

async def mock_assess(*args, **kwargs):
    return QualityReport(score=1.0, checks_passed=True, anomalies=[])
app.tools.quality.assess_image = mock_assess

async def run_sequence():
    image_id = str(uuid.uuid4())
    # 1x1 transparent pixel png
    dummy_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    print("================================")
    print("--- Turn 1: what does this image show? ---")
    state1 = GraphState(
        session_id="s1",
        query_id="q1",
        user_query="what does this image show?",
        image_context={
            "image": dummy_image,
            "metadata": {"image_id": image_id},
            "chat_history": []
        }
    )
    res1 = await production_graph.ainvoke(state1)
    ans1 = res1["final_answer"].model_dump() if hasattr(res1["final_answer"], "model_dump") else res1["final_answer"]
    print("Answer:", ans1)
    print("Nodes run:", [t.node for t in res1["trace"]])
    print("Reasoning found:", any(t.reasoning for t in res1["trace"]))
    
    print("\n================================")
    print("--- Turn 2: what crops are likely growing here? ---")
    state2 = GraphState(
        session_id="s1",
        query_id="q2",
        user_query="what crops are likely growing here?",
        image_context={
            "image": dummy_image,
            "metadata": {"image_id": image_id},
            "chat_history": [{"role": "user", "content": "what does this image show?"}, {"role": "assistant", "content": "Some description."}]
        }
    )
    res2 = await production_graph.ainvoke(state2)
    ans2 = res2["final_answer"].model_dump() if hasattr(res2["final_answer"], "model_dump") else res2["final_answer"]
    print("Answer:", ans2)
    print("Nodes run:", [t.node for t in res2["trace"]])
    print("Reasoning in observe_scene:", [t.reasoning for t in res2["trace"] if t.node == "scene_observation"])
    
    print("\n================================")
    print("--- Turn 3: what was my previous question? ---")
    state3 = GraphState(
        session_id="s1",
        query_id="q3",
        user_query="what was my previous question?",
        image_context={
            "image": dummy_image,
            "metadata": {"image_id": image_id},
            "chat_history": [
                {"role": "user", "content": "what does this image show?"}, 
                {"role": "assistant", "content": "Some description."},
                {"role": "user", "content": "what crops are likely growing here?"}, 
                {"role": "assistant", "content": "Some crop answer."}
            ]
        }
    )
    res3 = await production_graph.ainvoke(state3)
    ans3 = res3["final_answer"].model_dump() if hasattr(res3["final_answer"], "model_dump") else res3["final_answer"]
    print("Answer:", ans3)
    print("Nodes run:", [t.node for t in res3["trace"]])
    
    print("\n================================")
    print("--- Turn 4: who am i? ---")
    state4 = GraphState(
        session_id="s1",
        query_id="q4",
        user_query="who am i?",
        image_context={
            "image": dummy_image,
            "metadata": {"image_id": image_id},
            "chat_history": []
        }
    )
    res4 = await production_graph.ainvoke(state4)
    ans4 = res4["final_answer"].model_dump() if hasattr(res4["final_answer"], "model_dump") else res4["final_answer"]
    print("Answer:", ans4)
    print("Nodes run:", [t.node for t in res4["trace"]])

if __name__ == "__main__":
    asyncio.run(run_sequence())
