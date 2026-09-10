"""OpenRouter client for text and multimodal model requests."""

from __future__ import annotations

import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

SchemaModel = TypeVar("SchemaModel", bound=BaseModel)


def strip_reasoning(text: str) -> str:
    """Remove provider reasoning blocks before structured parsing."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    return cleaned.strip()


def image_data_uri(image: str, mime_type: str = "image/png") -> str:
    """Return an image as a data URI suitable for OpenAI-compatible APIs."""
    if image.startswith("data:image/"):
        return image
    return f"data:{mime_type};base64,{image}"


async def call_openrouter(
    messages: list[dict],
    *,
    max_tokens: int = 512,
    temperature: float = 0.1,
    json_mode: bool = False,
    json_schema: dict[str, Any] | None = None,
) -> str:
    """Call the configured OpenRouter model and return its text response."""
    if not settings.open_router_api_key:
        raise RuntimeError("OPEN_ROUTER_API_KEY is not configured")
    if not settings.vision_language_model:
        raise RuntimeError("VISION_LANGUAGE_MODEL is not configured")

    payload: dict[str, Any] = {
        "model": settings.vision_language_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "include_reasoning": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if json_schema:
        payload["tools"] = [{
            "type": "function",
            "function": {
                "name": "submit_structured_response",
                "description": "Return the validated structured response.",
                "parameters": json_schema,
            },
        }]
        payload["tool_choice"] = {
            "type": "function",
            "function": {"name": "submit_structured_response"},
        }

    headers = {
        "Authorization": f"Bearer {settings.open_router_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "SatQuery",
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            f"{settings.open_router_base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=payload,
        )
        if response.is_error:
            raise RuntimeError(f"OpenRouter {response.status_code}: {response.text[:500]}")
        data = response.json()

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")
    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = tool_calls[0].get("function", {}).get("arguments")
        if isinstance(arguments, str) and arguments.strip():
            return strip_reasoning(arguments)
    content = message.get("content") or ""
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        reasoning = message.get("reasoning") or ""
        if isinstance(reasoning, str) and reasoning.strip():
            content = reasoning
        else:
            raise RuntimeError("OpenRouter returned neither content nor reasoning")
    return strip_reasoning(content)


async def call_model_with_schema(
    messages: list[dict],
    response_model: type[SchemaModel],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    max_retries: int = 1,
) -> SchemaModel:
    """Call the configured provider and return only validated Pydantic data."""
    schema = response_model.model_json_schema()
    request_messages = messages
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            payload_messages = request_messages
            if attempt:
                payload_messages = [
                    *messages,
                    {
                        "role": "user",
                        "content": "Return ONLY valid JSON matching this schema, with no markdown or other text: "
                        + str(schema),
                    },
                ]
            raw = await call_openrouter(
                payload_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                json_schema=schema,
            )
            return response_model.model_validate_json(strip_reasoning(raw))
        except (ValidationError, ValueError, TypeError) as exc:
            last_error = exc
    raise RuntimeError(f"Structured model response validation failed: {last_error}") from last_error