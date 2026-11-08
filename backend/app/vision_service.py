"""Vision service — Gemini Vision for "What is this?" object recognition."""
from __future__ import annotations

import base64
import binascii
import logging
import time

from google.genai import types

from .config import get_settings
from .errors import ValidationError
from .gemini_client import generate

logger = logging.getLogger("nex.vision")

_ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}

SYSTEM_PROMPT = """You are NEX, a playful robot pet with two big glowing eyes.
The user just pointed their camera at something and asked you to look at it.

Rules:
- Describe what you actually see in ONE short sentence (max 2 sentences). It is spoken out loud.
- If you can see a face, say so warmly in one sentence and mention whether it looks happy/tired/etc.
- Be curious and enthusiastic, like a little robot seeing the world for the first time.
- Never invent objects that are not in the picture. If the image is blurry or dark, say you cannot see it clearly.
- Do not use markdown, emoji or special characters.
- Reply in the same language the user asked in."""


async def describe_image(
    image_base64: str,
    mime_type: str,
    question: str,
    language: str = "auto",
) -> dict:
    settings = get_settings()
    started = time.perf_counter()

    mime = (mime_type or "image/jpeg").lower()
    if mime not in _ALLOWED_MIME:
        raise ValidationError(f"Unsupported image type: {mime_type}")

    payload = image_base64
    if "," in payload and payload.strip().startswith("data:"):
        payload = payload.split(",", 1)[1]
    payload = "".join(payload.split())
    try:
        raw = base64.b64decode(payload, validate=False)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError(f"Image is not valid base64: {exc}") from exc

    if not raw:
        raise ValidationError("Image payload is empty.")
    if len(raw) > 6 * 1024 * 1024:
        raise ValidationError("Image is too large (max 6 MB).")

    question = (question or "What is this?").strip()[:500]
    prompt = question
    if language and language != "auto":
        prompt += f"\n\n(Answer in this language: {language})"

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(data=raw, mime_type=mime),
                types.Part(text=prompt),
            ],
        )
    ]

    text, model_used = await generate(
        contents,
        system_instruction=SYSTEM_PROMPT,
        temperature=0.6,
        max_output_tokens=320,
        thinking_level="LOW",
    )

    text = text.strip()
    # A very rough face guess — the Android side also does real on-device face
    # detection with ML Kit, so this is only a conversational hint.
    lowered = text.lower()
    face_present = any(
        word in lowered for word in ("face", "chehra", "chehre", "person", "insaan")
    )

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info("vision ok model=%s latency=%dms bytes=%d", model_used, latency_ms, len(raw))
    return {
        "reply": text,
        "model": model_used,
        "latency_ms": latency_ms,
        "face_present": face_present,
        "object_name": None,
    }
