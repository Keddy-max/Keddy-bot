"""
Service module for communicating with the Groq API.

Provides helper functions to generate AI replies with conversation history support
using the Groq API. Supports multiple language modes (formal and pidgin).

Environment Variables:
    GROQ_API_KEY: API key for Groq service (required)

Raises:
    ValueError: If required environment variables are missing
"""

import os
import logging
import base64
from typing import Optional, List, Dict, Union
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. "
        "Please configure your Groq API key in the .env file."
    )

try:
    client: Groq = Groq(api_key=GROQ_API_KEY)
except Exception as error:
    logging.error(f"Failed to initialize Groq client: {error}")
    raise

MODEL_NAME: str = "llama-3.1-8b-instant"
WHISPER_MODEL: str = "whisper-large-v3-turbo"
VISION_MODEL: str = "llama-3.2-11b-vision-preview"

# Generation tuning tuned for more natural, conversational replies.
MAX_TOKENS: int = 450
TEMPERATURE: float = 0.22
TOP_P: float = 0.88


# Penalties: Groq supports these in many compatible APIs. We pass defensively.
FREQUENCY_PENALTY: float = 0.2
PRESENCE_PENALTY: float = 0.1

MAX_HISTORY_LENGTH: int = 12
MAX_RECENT_TURNS: int = 8
SUPPORTED_MODES: List[str] = ["formal", "pidgin"]

# History/memory helpers
MEMORY_MAX_CHARS: int = 800

from services.prompting import get_system_prompt

def _build_memory_from_history(
    history: Optional[List[Dict[str, str]]],
    mode: str,
) -> str:
    """Create a compact memory string from recent turns.

    We avoid extra LLM calls for memory (to keep latency low).
    The goal is to remind the model about unresolved context and preferences
    that likely appear in the last few turns.

    Input history format is preserved as {role, content}.
    """
    if not history:
        return ""

    # Take the last few turns, then heuristically summarize into a short note.
    recent = history[-MAX_RECENT_TURNS:]
    user_texts: List[str] = []
    assistant_texts: List[str] = []
    for item in recent:
        role = (item.get("role") or "").lower()
        content = (item.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            user_texts.append(content)
        elif role == "assistant":
            assistant_texts.append(content)

    if not user_texts and not assistant_texts:
        return ""

    # Simple pattern-based “memory”:
    # - last user intent/question (last user message)
    # - last assistant outcome (last assistant message)
    last_user = user_texts[-1] if user_texts else ""
    last_assistant = assistant_texts[-1] if assistant_texts else ""

    # Also include a small window of prior user messages for continuity.
    prior_user = " | ".join(user_texts[-3:])

    # Mode-specific style hint.
    if mode.lower() == "pidgin":
        note = (
            f"Conversation memory (for continuity):\n"
            f"- Last thing you asked: {last_user[:240]}\n"
            f"- What I last said: {last_assistant[:240]}\n"
            f"- Recent topics: {prior_user[:420]}"
        )
    else:
        note = (
            f"Conversation memory (for continuity):\n"
            f"- Last thing you asked: {last_user[:240]}\n"
            f"- What I last said: {last_assistant[:240]}\n"
            f"- Recent topics: {prior_user[:420]}"
        )

    return note[:MEMORY_MAX_CHARS].strip()


def _post_process_reply(text: str) -> str:
    """Clean up reply text to feel less robotic.

    - normalize excessive blank lines
    - trim repeated leading/trailing whitespace
    - remove duplicated consecutive lines
    """
    if not text:
        return text

    cleaned = text.replace("\r\n", "\n").strip()
    # Collapse 3+ newlines to 2
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")

    lines = cleaned.split("\n")
    deduped: List[str] = []
    prev = None
    for ln in lines:
        ln_stripped = ln.strip()
        if not ln_stripped:
            # keep one blank line between content blocks
            if deduped and deduped[-1] != "":
                deduped.append("")
            prev = ln_stripped
            continue
        if prev is not None and ln_stripped == prev:
            continue
        deduped.append(ln)
        prev = ln_stripped

    return "\n".join(deduped).strip()


def get_keddy_reply(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: Optional[str] = None,
) -> str:
    """Generate an AI reply using the Groq API."""
    if not user_message or not isinstance(user_message, str):
        raise ValueError("user_message must be a non-empty string")

    normalized_mode: str = (mode or "formal").lower()
    if normalized_mode not in SUPPORTED_MODES:
        logging.warning(f"Invalid mode '{mode}', defaulting to 'formal'")
        normalized_mode = "formal"

    system_content: str = get_system_prompt(normalized_mode)

    # Build a short memory note from the existing WhatsApp history.
    memory_note: str = _build_memory_from_history(history=history, mode=normalized_mode)

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
    if memory_note:
        messages.append({"role": "system", "content": memory_note})

    if history:
        messages.extend(history[-MAX_HISTORY_LENGTH:])

    messages.append({"role": "user", "content": user_message})

    try:
        # Groq SDK compatibility: some clients accept penalties, some may not.
        # We attempt with penalties, and fall back if the server rejects them.
        def _create_call(msgs: List[Dict[str, str]], temp: float) -> str:
            try:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=msgs,
                    temperature=temp,
                    top_p=TOP_P,
                    frequency_penalty=FREQUENCY_PENALTY,
                    presence_penalty=PRESENCE_PENALTY,
                    max_tokens=MAX_TOKENS,
                )
            except TypeError:
                resp = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=msgs,
                    temperature=temp,
                    top_p=TOP_P,
                    max_tokens=MAX_TOKENS,
                )

            if not resp.choices or not resp.choices[0].message:
                raise RuntimeError("Invalid API response: no message content")

            out = (resp.choices[0].message.content or "").strip()
            if not out:
                raise RuntimeError("API returned empty response")
            return out

        # First attempt
        reply_raw = _create_call(messages=messages, temp=TEMPERATURE).strip()

        # One-shot accuracy retry if the reply seems too short or looks generic.
        needs_retry = len(reply_raw) < 10 or reply_raw.lower() in {"ok", "okay", "sure"}
        if needs_retry:
            retry_system = (
                "You must produce a helpful, specific answer. "
                "If the user request is ambiguous, ask 1 short clarifying question. "
                "Do not guess facts, numbers, or specific details."
            )
            retry_messages = [{"role": "system", "content": retry_system}] + messages
            reply_raw = _create_call(messages=retry_messages, temp=0.12).strip()

        return _post_process_reply(reply_raw)


    except Exception as error:
        logging.error(f"Groq API error: {type(error).__name__}: {error}")
        raise RuntimeError(f"Failed to generate reply: {error}") from error



def transcribe_audio(audio_bytes: bytes, filename: str = "voice.ogg") -> str:
    """
    Transcribe a voice note using Groq Whisper.

    Args:
        audio_bytes: Raw audio file bytes from Twilio.
        filename: Filename hint for the audio format.

    Returns:
        Transcribed text.

    Raises:
        RuntimeError: If transcription fails or returns empty text.
    """
    if not audio_bytes:
        raise RuntimeError("Audio file is empty")

    try:
        response = client.audio.transcriptions.create(
            file=(filename, audio_bytes),
            model=WHISPER_MODEL,
            response_format="text",
        )
        text = response.strip() if isinstance(response, str) else str(response).strip()
        if not text:
            raise RuntimeError("Transcription returned empty text")
        return text
    except Exception as error:
        logging.error(f"Groq Whisper error: {type(error).__name__}: {error}")
        raise RuntimeError(f"Failed to transcribe audio: {error}") from error


def get_keddy_image_reply(
    image_bytes: bytes,
    content_type: str,
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: Optional[str] = None,
) -> str:
    """
    Analyze an image and generate a reply using Groq vision.

    Args:
        image_bytes: Raw image bytes from Twilio.
        content_type: MIME type (e.g. image/jpeg).
        user_message: Optional caption or question about the image.
        history: Optional conversation history (text only).
        mode: Language mode - "formal" or "pidgin".

    Returns:
        AI response describing or answering about the image.
    """
    if not image_bytes:
        raise ValueError("image_bytes must not be empty")

    normalized_mode: str = (mode or "formal").lower()
    if normalized_mode not in SUPPORTED_MODES:
        normalized_mode = "formal"

    system_content: str = get_system_prompt(normalized_mode)

    prompt = user_message or "Please describe this image and offer helpful insights."

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime = content_type.split(";")[0].strip()
    data_url = f"data:{mime};base64,{b64_image}"

    user_content: List[Dict[str, Union[str, Dict[str, str]]]] = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]

    messages: List[Dict[str, object]] = [{"role": "system", "content": system_content}]
    if history:
        messages.extend(history[-MAX_HISTORY_LENGTH:])
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        if not response.choices or not response.choices[0].message:
            raise RuntimeError("Invalid vision API response")

        reply: str = response.choices[0].message.content.strip()
        if not reply:
            raise RuntimeError("Vision API returned empty response")

        return reply

    except Exception as error:
        logging.error(f"Groq vision error: {type(error).__name__}: {error}")
        raise RuntimeError(f"Failed to analyze image: {error}") from error

