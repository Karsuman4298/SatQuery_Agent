import pytest
import httpx
import json
from unittest.mock import patch, AsyncMock

from app.openrouter import call_model_with_schema, model_used_ctx
from app.config import settings
from pydantic import BaseModel

class DummyResponse(BaseModel):
    answer: str

@pytest.mark.asyncio
async def test_cloudflare_fallback_on_429():
    """
    Test that a 429 from Cloudflare transparently falls back to the local model
    for an allowed role, and that the execution summary (via context var) reflects the fallback.
    """
    settings.cloudflare_account_id = "test_account"
    settings.cloudflare_api_token = "test_token"
    settings.model_backend = "ollama"

    with patch("app.model_clients.ollama_client.OllamaClient") as MockOllamaClient:
        mock_ollama_instance = AsyncMock()
        mock_ollama_instance.generate.return_value = '{"answer": "fallback_success"}'
        MockOllamaClient.return_value = mock_ollama_instance
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = httpx.Response(429, text="Rate Limited")
            
            result, reasoning = await call_model_with_schema(
                messages=[{"role": "user", "content": "hello"}],
                response_model=DummyResponse,
                role="conversational_agent"
            )
            
            assert result.answer == "fallback_success"
            assert model_used_ctx.get() == "ollama/qwen2.5-vl"
            assert mock_ollama_instance.generate.called

