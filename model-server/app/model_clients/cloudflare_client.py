"""Cloudflare Workers AI client implementation."""
from __future__ import annotations
from typing import Any
import httpx
from pydantic import BaseModel
import json

from app.config import settings
from app.model_clients.base import ModelClient

class RateLimitError(Exception):
    """Raised when the API returns an HTTP 429 Too Many Requests response."""
    pass

class CloudflareClient(ModelClient):
    """ModelClient implementation for Cloudflare Workers AI."""
    
    def __init__(self) -> None:
        if not settings.cloudflare_account_id or not settings.cloudflare_api_token:
            raise ValueError("Cloudflare credentials not configured in environment (CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN)")
            
        self.account_id = settings.cloudflare_account_id
        self.api_token = settings.cloudflare_api_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/v1/chat/completions"
        self.default_model = "@cf/meta/llama-4-scout-17b-16e-instruct"

    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload,
            )
            
            if response.status_code == 429:
                raise RateLimitError(f"Cloudflare Rate Limit Exceeded: {response.text}")
                
            if response.is_error:
                raise RuntimeError(f"Cloudflare API Error {response.status_code}: {response.text[:500]}")
                
            data = response.json()
            
            if "result" in data and "response" in data["result"]:
                return data["result"]["response"]
            elif "result" in data and "choices" in data["result"]:
                return data["result"]["choices"][0]["message"]["content"]
            elif "choices" in data:
                return data["choices"][0]["message"]["content"]
            else:
                raise RuntimeError(f"Unexpected Cloudflare response format: {data}")
