import pytest
import asyncio
from app.agent.classifier import IntentClassifier

@pytest.mark.asyncio
async def test_classifier_fallback():
    classifier = IntentClassifier()
    await classifier.initialize()
    
    # Simulate that 'change_detection' failed the eval gate
    classifier.set_enabled_tasks({"vqa", "segmentation", "fusion", "conversational"})
    
    # Ask a clear change detection query
    query = "what changed between these two images"
    
    # Should return None because change_detection is disabled
    best_task, best_score, scores = await classifier.classify(query)
    
    assert best_task is None, f"Expected None due to disabled task, got {best_task}"
    assert best_score > 0.8, "Should still have high confidence internally"
    assert max(scores, key=scores.get) == "change_detection", "Internal scores should still prefer change_detection"
    
    print("Fallback to None works correctly when task fails 90% gate.")
