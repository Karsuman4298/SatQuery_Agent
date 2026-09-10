"""Provider-neutral model client contract."""

from __future__ import annotations

from typing import Any, Protocol


class ModelClient(Protocol):
    async def generate(
        self,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 512,
        temperature: float = 0.1,
        json_schema: dict[str, Any] | None = None,
    ) -> str:
        """Generate text from a text or multimodal message list."""
