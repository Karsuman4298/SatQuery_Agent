"""OpenAI-compatible local vLLM client for a future fine-tuned model."""

from __future__ import annotations

from typing import Any

import httpx

from app.openrouter import strip_reasoning


class LocalVLLMClient:
    def __init__(self, base_url: str, model: str, api_key: str = "local"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "include_reasoning": False,
        }
        if json_schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": {"name": "analysis", "schema": json_schema}}
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        return strip_reasoning(data["choices"][0]["message"].get("content") or "")
