"""Query-driven task classifier using Ollama nomic-embed-text embeddings.

Classifies user queries into one of the 5 supported task types by comparing
the query embedding to pre-computed canonical example embeddings.

The 90% evaluation gate is applied per-task: tasks that fail the gate fall
back to explicit frontend mode selection.
"""

from __future__ import annotations

import asyncio
import math
from typing import Literal

from app.model_clients.ollama_client import OllamaClient

TaskLabel = Literal["vqa", "segmentation", "change_detection", "fusion", "conversational"]

# Canonical few-shot examples per task. Each list contains representative
# queries that a user might type to trigger that task.
CANONICAL_EXAMPLES: dict[TaskLabel, list[str]] = {
    "vqa": [
        "what color is the river",
        "describe this satellite image",
        "what does this show",
        "what does this image show",
        "what is shown here",
        "what do you see in this image",
        "what land use patterns do you see",
        "how many buildings are in this area",
        "is there a road connecting these two towns",
        "what type of vegetation is visible",
        "identify the water bodies in the image",
        "what is the dominant land cover in this region",
        "are there any agricultural fields visible",
        "describe the terrain features",
        "what infrastructure can you identify",
        "is this area urban or rural",
        "what features are near the coastline",
        "estimate the density of the built-up area",
        "can you identify any airports or runways",
        "is there flooding visible in this scene",
        "what type of industry is in this area",
        "is there a dam visible in this image",
        "what geological features are visible",
        "are there wind turbines in this image",
        "what kind of settlement pattern is this",
    ],
    "segmentation": [
        "segment the main building",
        "isolate the water body",
        "outline the forest region",
        "mask the agricultural field",
        "extract the road network",
        "segment the large commercial building",
        "isolate the parking lot",
        "outline the stadium",
        "mask the river in this image",
        "extract the dense tree canopy",
        "segment everything that looks like a road",
        "highlight the residential area",
        "delineate the boundary of the lake",
        "separate the urban area from rural",
        "mark the airport runway",
        "extract all water features from this image",
        "highlight the crop fields in the image",
        "extract the coastline from this image",
        "extract the railway from this satellite image",
        "highlight the sand dunes in this image",
        "highlight the shipping containers separately",
        "mark all the buildings in this scene",
        "extract the impervious surfaces",
        "mask out the quarry area",
        "delineate the dam structure in this image",
    ],
    "change_detection": [
        "what changed between these two images",
        "detect changes between before and after",
        "show me what is different",
        "compare these two temporal images",
        "has this area been developed since the earlier image",
        "identify new construction between the two dates",
        "what vegetation has been lost",
        "are there any new roads built",
        "show deforestation changes",
        "compare urban expansion",
        "what buildings were demolished",
        "detect flood damage changes",
        "identify land use changes over time",
        "has the water level changed",
        "compare pre and post disaster imagery",
        "track the urban sprawl between these images",
        "show where demolition occurred between images",
        "quantify the vegetation loss between dates",
        "identify reconstruction after the disaster",
        "has the river course shifted between periods",
        "detect new construction since the last survey",
        "track glacier retreat between acquisitions",
        "compare impervious surface growth over time",
        "how has the shoreline shifted over this period",
        "what fields were converted to urban between dates",
    ],
    "fusion": [
        "fuse optical and SAR data",
        "combine the radar and optical images",
        "cross-validate SAR with optical imagery",
        "what does the SAR image reveal that optical does not",
        "merge these two sensor modalities",
        "compare radar backscatter with visible features",
        "verify the optical classification using SAR",
        "analyze agreement between optical and radar",
        "what structures appear in SAR but not optical",
        "use both sensor types to identify water",
        "integrate synthetic aperture radar with multispectral data",
        "correlate SAR texture with land cover",
        "check consistency between radar and visible spectrum",
        "fuse these images for a complete analysis",
        "which features agree between optical and SAR",
        "combine C-band SAR with optical for mapping",
        "merge radar and optical for ship detection",
        "use SAR to fill gaps in cloudy optical imagery",
        "cross-reference radar moisture with visible greenness",
        "use both modalities to improve classification",
    ],
    "conversational": [
        "hello",
        "what can you do",
        "help me understand satellite imagery",
        "what is remote sensing",
        "explain NDVI to me",
        "what was my previous question",
        "can you summarize what we discussed",
        "tell me about sentinel-2 bands",
        "what is the difference between optical and SAR",
        "how does change detection work",
        "what types of analysis can you perform",
        "thanks for the help",
        "who are you",
        "explain spectral indices",
        "what resolution does landsat have",
        "explain how SAR works as a technology",
        "what is atmospheric correction in remote sensing",
        "explain what pansharpening means",
        "how does interferometry work in satellite imaging",
        "what is radiometric correction",
        "what is the backscatter coefficient in radar",
        "can you explain orthorectification as a concept",
        "what machine learning methods are used in remote sensing",
        "what sensors does the International Space Station carry",
        "define spatial resolution versus spectral resolution",
        "what is the swath width of Sentinel-2",
        "how do polar orbiting satellites differ from geostationary",
        "how do you handle cloudy images in analysis",
        "how accurate is your change detection capability",
        "what data formats do you accept",
    ],
}


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class IntentClassifier:
    """Embedding-similarity based query classifier using Ollama nomic-embed-text.

    Pre-computes embeddings for canonical examples on first use, then classifies
    new queries by finding the task with the highest average similarity.
    """

    def __init__(self):
        self._client = OllamaClient()
        self._task_embeddings: dict[TaskLabel, list[list[float]]] = {}
        self._initialized = False
        # Per-task gate: tasks below 90% precision/recall fall back to explicit mode.
        # This is populated by evaluate_classifier.py after running the eval suite.
        self._enabled_tasks: set[TaskLabel] = {
            "vqa", "segmentation", "change_detection", "fusion", "conversational"
        }

    async def initialize(self) -> None:
        """Pre-compute embeddings for all canonical examples."""
        if self._initialized:
            return
        for task, examples in CANONICAL_EXAMPLES.items():
            embeddings = []
            for example in examples:
                emb = await self._client.embed(example)
                embeddings.append(emb)
            self._task_embeddings[task] = embeddings
        self._initialized = True

    def set_enabled_tasks(self, tasks: set[TaskLabel]) -> None:
        """Set which tasks have passed the 90% evaluation gate.

        Tasks not in this set fall back to explicit frontend mode selection.
        """
        self._enabled_tasks = tasks

    async def classify(
        self,
        query: str,
        *,
        threshold: float = 0.3,
    ) -> tuple[TaskLabel | None, float, dict[TaskLabel, float]]:
        """Classify a query into a task type.

        Returns:
            (predicted_task, confidence, per_task_scores)
            predicted_task is None if the best score is below threshold,
            meaning the query is ambiguous and needs clarification.
        """
        if not self._initialized:
            await self.initialize()

        query_embedding = await self._client.embed(query)

        scores: dict[TaskLabel, float] = {}
        for task, embeddings in self._task_embeddings.items():
            similarities = [_cosine_similarity(query_embedding, emb) for emb in embeddings]
            # Use the average of the top-3 most similar examples
            top_k = sorted(similarities, reverse=True)[:3]
            scores[task] = sum(top_k) / len(top_k) if top_k else 0.0

        best_task = max(scores, key=scores.get)  # type: ignore
        best_score = scores[best_task]

        # If the best task hasn't passed the evaluation gate, return None
        if best_task not in self._enabled_tasks:
            return None, best_score, scores

        if best_score < threshold:
            return None, best_score, scores
            
        # Disambiguation fallback: if score is borderline (e.g. between threshold and threshold+0.15)
        # ask the LLM for a quick opinion
        if threshold <= best_score < threshold + 0.15:
            try:
                from app.openrouter import call_model_with_schema
                from pydantic import BaseModel
                
                class DisambiguationResponse(BaseModel):
                    task: TaskLabel | None
                    
                resp, _ = await call_model_with_schema(
                    [
                        {"role": "system", "content": "You are a classifier. Pick the best task for the user query, or null if ambiguous."},
                        {"role": "user", "content": f"Query: {query}\n\nAllowed tasks: {list(self._enabled_tasks)}"}
                    ],
                    DisambiguationResponse,
                    max_tokens=50,
                    role="classifier_disambiguation"
                )
                if resp.task and resp.task in self._enabled_tasks:
                    best_task = resp.task
                    # slightly bump confidence to indicate LLM confirmed it
                    best_score = best_score + 0.1
                else:
                    return None, best_score, scores
            except Exception:
                pass # on failure, just proceed with the vector match

        return best_task, best_score, scores


# Module-level singleton
_classifier: IntentClassifier | None = None


async def get_classifier() -> IntentClassifier:
    """Get or create the singleton IntentClassifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
        await _classifier.initialize()
    return _classifier
