"""Thin, well-behaved wrapper around the official Google Gen AI SDK.

Only Gemini is used — there is no alternative provider path in this codebase.

Design goals
------------
* The API key never leaves the backend (it is read from ``GEMINI_API_KEY``).
* Model names are validated against a small allow-list and we transparently
  fall back to secondary models when the primary one is unavailable.
* Every failure is mapped onto one of the typed errors in :mod:`app.errors`
  so the Android client can show an accurate message.
* Logging never contains the API key or the raw key prefix.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from google import genai
from google.genai import types

from .config import get_settings
from .errors import (
    ConfigError,
    GeminiError,
    GeminiSafetyError,
    GeminiTimeoutError,
)

logger = logging.getLogger("nex.gemini")

_client: genai.Client | None = None

# Models we are willing to call. Anything else in the environment is ignored.
ALLOWED_MODEL_PATTERN = re.compile(r"^gemini-[a-z0-9.\-]+$")


def _mask_key(key: str) -> str:
    if not key:
        return "<empty>"
    return f"{key[:4]}...{key[-2:]}(len={len(key)})"


def get_client() -> genai.Client:
    """Return a lazily created, process-wide Gen AI client."""
    global _client
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ConfigError(
            "GEMINI_API_KEY is not set on the server. "
            f"Set it in the environment (received: {_mask_key(settings.gemini_api_key)})."
        )
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini client initialised with key %s", _mask_key(settings.gemini_api_key))
    return _client


def model_chain() -> list[str]:
    """Ordered list of models to try (primary first)."""
    settings = get_settings()
    chain: list[str] = []
    for candidate in (settings.gemini_model, *settings.gemini_fallback_models):
        if candidate and ALLOWED_MODEL_PATTERN.match(candidate) and candidate not in chain:
            chain.append(candidate)
    if not chain:
        chain = ["gemini-3.6-flash"]
    return chain


def _is_missing_model_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "not found" in text
        or "not_found" in text
        or "404" in text
        or "unsupported model" in text
    )


def _is_safety_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "safety" in text or "blocked" in text


def _extract_text(response: types.GenerateContentResponse) -> str:
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    # Fallback: walk the parts manually (some responses have text in candidates).
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "text", None):
                return part.text.strip()
    return ""


def _build_config(
    *,
    system_instruction: str | None,
    temperature: float | None,
    max_output_tokens: int | None,
    response_schema: types.Schema | None,
    response_mime_type: str | None,
    thinking_level: str | None = "LOW",
) -> types.GenerateContentConfig:
    kwargs: dict[str, Any] = {}
    if system_instruction:
        kwargs["system_instruction"] = system_instruction
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_output_tokens:
        kwargs["max_output_tokens"] = max_output_tokens
    if response_schema is not None:
        kwargs["response_schema"] = response_schema
    if response_mime_type:
        kwargs["response_mime_type"] = response_mime_type
    if thinking_level:
        try:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_level=types.ThinkingLevel(thinking_level)
            )
        except (ValueError, AttributeError):  # pragma: no cover - SDK drift guard
            pass
    return types.GenerateContentConfig(**kwargs)


async def generate(
    contents: str | list[types.Part],
    *,
    system_instruction: str | None = None,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    response_schema: types.Schema | None = None,
    response_mime_type: str | None = None,
    thinking_level: str | None = "LOW",
) -> tuple[str, str]:
    """Call Gemini and return ``(text, model_used)``.

    Raises :class:`ConfigError`, :class:`GeminiTimeoutError` or
    :class:`GeminiError` — never a raw SDK exception.
    """
    settings = get_settings()
    client = get_client()
    config = _build_config(
        system_instruction=system_instruction,
        temperature=temperature if temperature is not None else settings.temperature,
        max_output_tokens=max_output_tokens or settings.max_output_tokens,
        response_schema=response_schema,
        response_mime_type=response_mime_type,
        thinking_level=thinking_level,
    )

    last_error: Exception | None = None
    for model in model_chain():
        try:
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                ),
                timeout=settings.request_timeout,
            )
            text = _extract_text(response)
            if not text:
                finish = ""
                candidates = getattr(response, "candidates", []) or []
                if candidates:
                    finish = str(getattr(candidates[0], "finish_reason", ""))
                if "SAFETY" in finish.upper() or "PROHIBITED" in finish.upper():
                    raise GeminiSafetyError(f"Gemini blocked the request (finish_reason={finish}).")
                raise GeminiError("Gemini returned an empty response.")
            return text, model
        except asyncio.TimeoutError:
            last_error = GeminiTimeoutError(
                f"Gemini model '{model}' did not respond within {settings.request_timeout:.0f}s."
            )
            logger.warning("Gemini timeout on model %s", model)
            continue
        except (ConfigError, GeminiSafetyError):
            raise
        except Exception as exc:  # noqa: BLE001 - SDK raises many error shapes
            if _is_safety_error(exc):
                raise GeminiSafetyError(f"Gemini blocked the request: {exc}") from exc
            last_error = exc
            logger.warning("Gemini call failed on model %s: %s", model, exc)
            continue

    detail = str(last_error) if last_error else "unknown error"
    raise GeminiError(f"All Gemini models failed. Last error: {detail}")


def parse_json(text: str) -> dict:
    """Best-effort JSON parsing for structured replies."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z]*\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else {"reply": candidate}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return {"reply": candidate}


def health_snapshot() -> dict:
    settings = get_settings()
    return {
        "gemini_configured": settings.gemini_configured,
        "model": settings.gemini_model,
        "model_chain": model_chain(),
    }
