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
app.include_router(debug.router, tags=["debug"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "model-server",
        "mock_mode": settings.mock_models,
    }
