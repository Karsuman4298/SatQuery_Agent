"""
SatQuery Model Server
─────────────────────
Internal FastAPI service wrapping remote sensing analysis models.
All endpoints are called by the backend service — never exposed directly to the frontend.

Set MOCK_MODELS=false for live OpenRouter analysis.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import vqa, change, fusion, segment, debug
from app.routers import agent as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate the configured live inference mode at startup."""
    if not settings.mock_models:
        print(f" Model server running in LIVE mode — {settings.vision_language_model}")
    else:
        print(" Model server running in MOCK mode — API calls return simulated data")
    print(" Multi-agent LangGraph orchestrator loaded")
    yield
    # Cleanup
    print("Shutting down model server")


app = FastAPI(
    title="SatQuery Model Server",
    description="Internal ML inference service for SatQuery",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust as necessary for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(vqa.router, tags=["vqa"])
app.include_router(change.router, tags=["change"])
app.include_router(fusion.router, tags=["fusion"])
app.include_router(segment.router, tags=["segment"])
app.include_router(agent_router.router, tags=["agent"])
from app.runtime.api import router as runtime_router
app.include_router(runtime_router)
app.include_router(debug.router, tags=["debug"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "model-server",
        "mock_mode": settings.mock_models,
    }


@app.get('/readiness')
async def readiness():
    """Distinguish a live API process from an available local inference model."""
    import httpx
    available = False
    model = settings.ollama_model if settings.model_backend == 'ollama' else settings.vllm_model
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            if settings.model_backend == 'ollama':
                response = await client.get(f'{settings.ollama_base_url.rstrip("/")}/api/tags')
                response.raise_for_status()
                available = any(item.get('name') == model or item.get('model') == model
                                for item in response.json().get('models', []))
            elif settings.model_backend == 'vllm':
                response = await client.get(f'{settings.vllm_base_url.rstrip("/")}/v1/models')
                response.raise_for_status()
                available = any(item.get('id') == model for item in response.json().get('data', []))
    except (httpx.HTTPError, ValueError):
        pass
    from app.agent.registry import REGISTRY
    return {'status': 'ready' if available and not settings.mock_models else 'unavailable',
            'provider': settings.model_backend, 'model': model, 'mock_mode': settings.mock_models,
            'adaptation': 'Requires trained adapter and held-out benchmark evidence',
            'capabilities': REGISTRY}
