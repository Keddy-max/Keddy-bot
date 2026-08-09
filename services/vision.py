"""
Vision service for Keddy.

Provides a reusable, configurable image-understanding wrapper around the
project's AI provider (Groq). Images are analyzed in memory — no permanent
file storage — and the multimodal request always includes BOTH the actual
image bytes and the user's text caption/question.

Configuration (environment variables):
    VISION_MODEL     Model name for image analysis.
                     Default: llama-3.2-11b-vision-preview (Groq)
    VISION_API_URL   Optional generic vision endpoint. If set, a plain HTTPS
                     POST (OpenAI-style payload) is used instead of the Groq SDK.
    VISION_API_KEY   Optional override for the vision API key.
                     Falls back to GROQ_API_KEY.

    No keys are hard-coded. Credentials always come from environment variables.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from typing import Dict, List, Optional, Union

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (env-driven, no hard-coded secrets)
# ---------------------------------------------------------------------------
DEFAULT_VISION_MODEL: str = "llama-3.2-11b-vision-preview"
VISION_MODEL: str = os.getenv("VISION_MODEL", DEFAULT_VISION_MODEL)
VISION_API_URL: Optional[str] = os.getenv("VISION_API_URL") or None
VISION_API_KEY: Optional[str] = os.getenv("VISION_API_KEY") or os.getenv("GROQ_API_KEY")

# Correct Groq base URL. The SDK appends /chat/completions to this.
# If VISION_API_URL is set to a wrong host (e.g. console.groq.com) or a
# partial path, requests fail with "Unknown request URL" — so we normalize it.
GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

VISION_TIMEOUT_SECONDS: int = int(os.getenv("VISION_TIMEOUT_SECONDS", "60"))
VISION_MAX_TOKENS: int = int(os.getenv("VISION_MAX_TOKENS", "600"))
VISION_TEMPERATURE: float = float(os.getenv("VISION_TEMPERATURE", "0.22"))

MAX_HISTORY_TURNS: int = 6

# Prompt used when an image is sent with no caption/question.
NO_CAPTION_PROMPT: str = (
    "Describe what is visible in this image briefly (1-3 sentences), "
    "then ask 1 short question to offer further help (e.g., check the "
    "content, read text, or explain a chart). Do not write a long essay."
)

DEFAULT_ERROR_MESSAGE: str = (
    "Sorry, I couldn't process that image right now. "
    "Please try sending it again."
)


class VisionError(RuntimeError):
    """Raised for vision-processing failures that should not reach users."""


# ---------------------------------------------------------------------------
# MIME / format helpers
# ---------------------------------------------------------------------------
SUPPORTED_IMAGE_MIME_TYPES: Dict[str, str] = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/avif": "avif",
}


def is_supported_image(content_type: str) -> bool:
    """Return True if the MIME type is in the supported image allowlist."""
    return (content_type or "").split(";")[0].strip().lower() in SUPPORTED_IMAGE_MIME_TYPES


def normalize_mime(content_type: str) -> str:
    """Return the base MIME type (strip params) lowercased."""
    return (content_type or "").split(";")[0].strip().lower()


def normalize_vision_url(url: Optional[str]) -> Optional[str]:
    """Normalize a user-supplied VISION_API_URL to a valid chat endpoint.

    The Groq SDK appends ``/chat/completions`` to its base URL. If a user
    sets VISION_API_URL to a bare host (e.g. ``https://console.groq.com``) or
    to a base like ``https://api.groq.com/openai/v1``, requests will fail with
    "Unknown request URL" because the path is wrong. This helper corrects it
    to the full Groq chat-completions URL, or returns None if it's not a
    Groq URL (so the caller can fall back to the SDK).
    """
    if not url:
        return None
    stripped = url.strip().rstrip("/")
    if not stripped:
        return None

    # Correct the most common mistakes: console.groq.com (invalid API host)
    # or a partial base URL that's missing the full chat path.
    if "console.groq.com" in stripped:
        return GROQ_BASE_URL + "/chat/completions"
    if "api.groq.com" in stripped and not stripped.endswith("/chat/completions"):
        return GROQ_BASE_URL + "/chat/completions"

    # If it's already a full chat/completions URL, use as-is.
    if stripped.endswith("/chat/completions"):
        return stripped

    # Unknown host — return as-is and let the request fail with a clear log.
    return stripped


# ---------------------------------------------------------------------------
# History/memory helper (keeps follow-up questions about a previous image)
# ---------------------------------------------------------------------------
def _build_context_note(history: Optional[List[Dict[str, str]]]) -> str:
    """Build a short text note from recent history for vision follow-ups.

    This helps the model understand references such as "it" or "this" when
    a user follows up about a previously analyzed image.
    """
    if not history:
        return ""

    recent = history[-MAX_HISTORY_TURNS:]
    parts: List[str] = []
    for item in recent:
        role = (item.get("role") or "").lower()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            parts.append(f"User: {content[:400]}")
        elif role == "assistant":
            parts.append(f"You: {content[:400]}")

    if not parts:
        return ""
    note = "Conversation context for this image analysis:\n" + "\n".join(parts)
    return note[:1200]


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------
def _groq_analyze(
    image_bytes: bytes,
    mime: str,
    prompt: str,
    context_note: str,
    history: Optional[List[Dict[str, str]]],
    system_prompt: str,
) -> str:
    """Send the image + text prompt to Groq's vision model via the SDK."""
    from groq import Groq

    if not VISION_API_KEY:
        raise VisionError("Missing VISION_API_KEY / GROQ_API_KEY")

    # Use the default Groq client (no base_url override) — this matches the
    # working text path in groq_api.py. Overriding the base_url or pointing
    # VISION_API_URL at a wrong Groq host (e.g. console.groq.com) produces
    # "Unknown request URL: GET /openai/v1/chat/completions" errors.
    client = Groq(api_key=VISION_API_KEY)

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64_image}"

    user_content: List[Dict[str, Union[str, Dict[str, str]]]] = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    messages: List[Dict[str, object]] = [
        {"role": "system", "content": system_prompt}
    ]
    if history:
        messages.extend(history[-MAX_HISTORY_TURNS:])
    if context_note:
        messages.append({"role": "system", "content": context_note})
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=VISION_TEMPERATURE,
            max_tokens=VISION_MAX_TOKENS,
            timeout=VISION_TIMEOUT_SECONDS,
        )
    except Exception as error:
        logger.error(f"Groq vision error: {type(error).__name__}: {error}")
        raise VisionError("Vision API request failed") from error

    if not response.choices or not response.choices[0].message:
        raise VisionError("Vision API returned no choices")

    reply = (response.choices[0].message.content or "").strip()
    if not reply:
        raise VisionError("Vision API returned an empty response")
    return reply


def _generic_analyze(
    image_bytes: bytes,
    mime: str,
    prompt: str,
    context_note: str,
    history: Optional[List[Dict[str, str]]],
    system_prompt: str,
    url: Optional[str] = None,
) -> str:
    """Send the image + text prompt to a generic OpenAI-style vision endpoint.

    Used only when VISION_API_URL is set. The request body mirrors the OpenAI
    chat-completions multimodal format so it works with many compatible
    providers (OpenAI, OpenRouter, etc.).

    Args:
        url: The normalized full chat/completions URL. Defaults to the
            module-level VISION_API_URL (normalized at call time).
    """
    effective_url = normalize_vision_url(url or VISION_API_URL)
    if not effective_url:
        raise VisionError("VISION_API_URL is not configured")

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if VISION_API_KEY:
        headers["Authorization"] = f"Bearer {VISION_API_KEY}"

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime};base64,{b64_image}"

    user_content: List[Dict[str, Union[str, Dict[str, str]]]] = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    messages: List[Dict[str, object]] = [
        {"role": "system", "content": system_prompt}
    ]
    if history:
        messages.extend(history[-MAX_HISTORY_TURNS:])
    if context_note:
        messages.append({"role": "system", "content": context_note})
    messages.append({"role": "user", "content": user_content})

    payload: Dict[str, object] = {
        "model": VISION_MODEL,
        "messages": messages,
        "temperature": VISION_TEMPERATURE,
        "max_tokens": VISION_MAX_TOKENS,
    }

    try:
        resp = requests.post(
            effective_url,
            headers=headers,
            json=payload,
            timeout=VISION_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
    except requests.RequestException as error:
        logger.error(f"Generic vision API error: {type(error).__name__}: {error}")
        raise VisionError("Vision API request failed") from error

    try:
        data = resp.json()
    except ValueError as error:
        logger.error(f"Vision API returned non-JSON response: {error}")
        raise VisionError("Vision API returned an invalid response") from error

    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        logger.error(f"Unexpected vision API response shape: {data}")
        raise VisionError("Vision API returned an unexpected response") from error

    reply = (reply or "").strip()
    if not reply:
        raise VisionError("Vision API returned an empty response")
    return reply


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyze_image(
    image_bytes: bytes,
    content_type: str,
    user_prompt: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    mode: str = "formal",
) -> str:
    """Analyze an image with the configured vision model.

    The multimodal request ALWAYS contains the actual image plus the user's
    text (caption/question). If no caption is provided, a default brief
    description prompt is used.

    Args:
        image_bytes: Raw image bytes.
        content_type: MIME type of the image (e.g. image/jpeg).
        user_prompt: Optional caption or question about the image.
        history: Optional conversation history for follow-up context.
        mode: Language style ("formal" or "pidgin") for the system prompt.

    Returns:
        The AI's text response.

    Raises:
        VisionError: On any failure (download not included here).
        ValueError: If the image MIME type is unsupported or bytes are empty.
    """
    if not image_bytes:
        raise ValueError("image_bytes must not be empty")

    mime = normalize_mime(content_type)
    if not is_supported_image(content_type):
        raise ValueError(f"Unsupported image type: {content_type}")

    # Keep user prompt short and sanitized for safety.
    prompt = (user_prompt or "").strip()
    if not prompt:
        prompt = NO_CAPTION_PROMPT

    # System prompt from the shared prompting module (concise, vision-focused).
    # Using the full Keddy-Bot identity prompt here can overflow the vision
    # model's smaller context window when combined with a large base64 image.
    from services.prompting import get_vision_system_prompt
    system_prompt = get_vision_system_prompt(mode or "formal")

    context_note = _build_context_note(history)

    if VISION_API_URL:
        return _generic_analyze(
            image_bytes=image_bytes,
            mime=mime,
            prompt=prompt,
            context_note=context_note,
            history=history,
            system_prompt=system_prompt,
        )

    return _groq_analyze(
        image_bytes=image_bytes,
        mime=mime,
        prompt=prompt,
        context_note=context_note,
        history=history,
        system_prompt=system_prompt,
    )


# Backwards-compatible alias matching the requested naming convention.
def analyzeImage(image_bytes: bytes, user_prompt: str = "", **kwargs):
    """Backwards-compatible alias for analyze_image (camelCase)."""
    return analyze_image(image_bytes, user_prompt=user_prompt, **kwargs)
