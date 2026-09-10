"""OpenRouter implementation of the provider-neutral model client."""

from __future__ import annotations

from typing import Any

from app.openrouter import call_openrouter


class OpenRouterClient:
    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        # json_schema is intentionally not sent to free providers that reject it.
        return await call_openrouter(messages, max_tokens=max_tokens, temperature=temperature)
