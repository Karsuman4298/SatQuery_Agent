"""OpenRouter client for text and multimodal model requests."""

from __future__ import annotations

import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings

SchemaModel = TypeVar("SchemaModel", bound=BaseModel)

class SchemaValidationFailed(Exception):
    """Raised when a model repeatedly fails to produce JSON matching the requested schema."""
    pass

import functools
from typing import Callable, Awaitable

def with_graceful_degradation(fallback_factory: Callable[[], Any]):
    """Decorator to catch SchemaValidationFailed and return a fallback typed object instead."""
    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                result = await func(*args, **kwargs)
                if args and hasattr(args[0], "model_used"):
                    args[0].model_used = model_used_ctx.get()
                return result
            except SchemaValidationFailed as e:
                print(f"Graceful degradation triggered in {func.__name__}: {e}")
                
                fallback_val = fallback_factory()
                
                # Check if this is a LangGraph node (first arg is state with 'errors')
                if args and hasattr(args[0], "errors"):
                    state = args[0]
                    state.errors.append({"node": func.__name__, "error": str(e), "recovered": True})
                    state.model_used = model_used_ctx.get()
                    
                    if hasattr(fallback_val, "observations"):
                        state.scene_observations = fallback_val.observations
                    elif hasattr(fallback_val, "judgments"):
                        # If JudgeResponse, don't assign it anywhere directly, but mark evidence unsupported
                        state.unsupported.extend(item.text for item in state.evidence if item.source_type == "interpretation")
                    else:
                        # Otherwise it's a tool output (AnswerResponse, ChangeSummary, etc)
                        if hasattr(fallback_val, "model_dump"):
                            state.tool_result = fallback_val.model_dump()
                        elif isinstance(fallback_val, dict):
                            state.tool_result = fallback_val
                            
                    return state
                
                # If it's just a regular tool function, return the fallback value directly
                # If it's a BaseModel, return its dump to match tool dict return types
                if hasattr(fallback_val, "model_dump"):
                    return fallback_val.model_dump()
                return fallback_val
        return wrapper
    return decorator


def strip_reasoning(text: str) -> str:
    """Remove provider reasoning blocks before structured parsing."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<reasoning>.*?</reasoning>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
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
    """Call the configured primary model (Ollama first, fallback to OpenRouter) and return its text response."""
    # 1. Attempt Ollama Local Call
    try:
        ollama_payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            ollama_payload["response_format"] = {"type": "json_object"}
        if json_schema:
            ollama_payload["response_format"] = {
                "type": "json_object",
                "schema": json_schema
            }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions",
                json=ollama_payload,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if choices:
                content = choices[0].get("message", {}).get("content") or ""
                if isinstance(content, str) and content.strip():
                    return strip_reasoning(content)
    except Exception as e:
        print(f"Ollama local model failed: {e}. Falling back to OpenRouter.")

    # 2. Fallback to OpenRouter
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


import contextvars
from app.model_clients.cloudflare_client import RateLimitError, CloudflareClient

model_used_ctx = contextvars.ContextVar("model_used_ctx", default="")

async def call_model_with_schema(
    messages: list[dict],
    response_model: type[SchemaModel],
    *,
    max_tokens: int = 1024,
    temperature: float = 0.0,
    max_retries: int = 1,
    role: str | None = None,
) -> tuple[SchemaModel, str | None]:
    """Call the configured provider and return (validated Pydantic data, internal reasoning)."""
    import json
    
    schema = response_model.model_json_schema()
    
    # Inject internal_reasoning explicitly if it's a local model
    if settings.model_backend == "ollama":
        if "properties" not in schema:
            schema["properties"] = {}
        schema["properties"]["internal_reasoning"] = {
            "type": "string",
            "description": "Your internal step-by-step reasoning. MUST be provided."
        }
        if "required" not in schema:
            schema["required"] = []
        if "internal_reasoning" not in schema["required"]:
            schema["required"].append("internal_reasoning")

    # Role-based client selection
    allowed_cf_roles = {"classifier_disambiguation", "conversational_agent", "region_followup_agent"}
    
    # Initialize the default local client
    if settings.model_backend == "ollama":
        from app.model_clients.ollama_client import OllamaClient
        local_client = OllamaClient()
        local_model_name = "ollama/qwen2.5-vl"
    else:
        from app.model_clients.openrouter_client import OpenRouterClient
        local_client = OpenRouterClient()
        local_model_name = "openrouter/remote"
        
    client = local_client
    model_name = local_model_name
    
    # Override with Cloudflare if allowed and configured
    if role in allowed_cf_roles and settings.cloudflare_account_id:
        client = CloudflareClient()
        model_name = "cloudflare/llama-4-scout"

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            payload_messages = [
                *messages,
                {
                    "role": "user",
                    "content": "Return ONLY valid JSON matching this schema, with no markdown or other text: "
                    + str(schema),
                },
            ]
            if attempt > 0:
                payload_messages.append({
                    "role": "user",
                    "content": "Your previous response was invalid. You MUST return ONLY valid JSON matching the schema."
                })
            
            try:
                raw = await client.generate(
                    payload_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_schema=schema,
                )
                model_used_ctx.set(model_name)
            except RateLimitError as e:
                # Fallback to local on 429
                print(f"Cloudflare 429 RateLimitError, falling back to {local_model_name}")
                client = local_client
                model_name = local_model_name
                raw = await client.generate(
                    payload_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_schema=schema,
                )
                model_used_ctx.set(model_name)
            
            clean_raw = strip_reasoning(raw)
            try:
                data = json.loads(clean_raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Failed to parse JSON: {exc}") from exc
                
            reasoning = data.pop("internal_reasoning", None)
            
            # Now validate the REST of the dict against the original schema model
            return response_model.model_validate(data), reasoning
            
        except (ValidationError, ValueError, TypeError) as exc:
            last_error = exc
    raise SchemaValidationFailed(f"Structured model response validation failed: {last_error}") from last_error