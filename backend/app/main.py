"""
SatQuery Backend API
────────────────────
FastAPI backend that serves as the entrypoint for the frontend.
Handles database interactions, business logic, and routing to the model server.
"""

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine

# Global HTTP client for model server calls
http_client: httpx.AsyncClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global http_client
    # Initialize HTTP client for communicating with the model server
    http_client = httpx.AsyncClient(
        base_url=settings.model_server_url,
        timeout=httpx.Timeout(30.0),
    )
    yield
    # Cleanup
    await http_client.aclose()
    await engine.dispose()


app = FastAPI(
    title="SatQuery API",
    description="Backend API for SatQuery Earth Observation platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For hackathon/development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.routers import images, regions, query, reports
app.include_router(images.router, prefix="/images", tags=["images"])
app.include_router(regions.router, prefix="/regions", tags=["regions"])
app.include_router(query.router, prefix="/agent", tags=["agent"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/health")
async def health_check():
    """Health check endpoint. Checks DB and Model Server connectivity."""
    db_status = "disconnected"
    ms_status = "disconnected"

    # Check DB
    try:
        async with engine.connect() as conn:
            db_status = "connected"
    except Exception:
        pass

    # Check Model Server
    try:
        response = await http_client.get("/health")
        if response.status_code == 200:
            ms_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok" if db_status == "connected" and ms_status == "connected" else "degraded",
        "version": "1.0.0",
        "services": {
            "database": db_status,
            "model_server": ms_status,
        },
    }
