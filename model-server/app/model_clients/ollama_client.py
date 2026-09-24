"""Ollama client for local model requests."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from app.model_clients.base import ModelClient

class OllamaClient(ModelClient):
    """Client for local Ollama API."""
    
    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        """Generate text using Ollama's chat endpoint."""
        ollama_messages = []
        for msg in messages:
            if isinstance(msg.get("content"), list):
                text_parts = []
                images = []
                for part in msg["content"]:
                    if part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        url = part.get("image_url", {}).get("url", "")
                        # Remove data URI prefix if present
                        if "," in url:
                            url = url.split(",", 1)[1]
                        images.append(url)
                
                new_msg = {
                    "role": msg["role"],
                    "content": "\n".join(text_parts)
                }
                if images:
                    new_msg["images"] = images
                ollama_messages.append(new_msg)
            else:
                ollama_messages.append(msg)

        payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            }
        }
        
        if json_schema:
            payload["format"] = json_schema
            
        async with httpx.AsyncClient(timeout=120.0) as client:
            print(f"[OllamaClient] Invoking {settings.ollama_model} at {settings.ollama_base_url}")
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            
            data = response.json()
            message = data.get("message", {})
            return message.get("content", "")

    async def embed(self, text: str, model: str = "nomic-embed-text") -> list[float]:
        """Get text embeddings from Ollama's embedding endpoint."""
        payload = {
            "model": model,
            "prompt": text,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/embeddings",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
