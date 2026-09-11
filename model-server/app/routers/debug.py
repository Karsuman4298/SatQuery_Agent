"""Debug endpoints for internal trace and CoT inspection."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/debug", tags=["Debug"])

# In-memory store for traces, keyed by query_id
_DEBUG_TRACES = {}

@router.get("/trace/{query_id}")
async def get_trace(query_id: str):
    """Retrieve the full reasoning trace for a given query ID."""
    if query_id not in _DEBUG_TRACES:
        raise HTTPException(status_code=404, detail="Trace not found for query ID")
    
    # Return the list of TraceEntry dumped as dicts
    return {"query_id": query_id, "trace": [t.model_dump() for t in _DEBUG_TRACES[query_id]]}
