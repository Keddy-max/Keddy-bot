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
MAX_TOKENS: int = 300
TEMPERATURE: float = 0.2
MAX_HISTORY_LENGTH: int = 12
SUPPORTED_MODES: List[str] = ["formal", "pidgin"]

# Shared safety rules applied to all modes (Meta/WhatsApp compliance)
SAFETY_RULES = """
CONTENT SAFETY (MANDATORY):
- Never provide instructions for violence, weapons, illegal activities, or self-harm.
- Never generate sexually explicit content involving minors or non-consenting parties.
- Never share personal data about real individuals you do not have permission to disclose.
- Do not provide specific medical, legal, or financial advice — recommend qualified professionals instead.
- If asked about your nature, clearly state you are an AI assistant powered by artificial intelligence.
- Decline harmful, abusive, or policy-violating requests politely and redirect to helpful topics.
"""

PERSONALITY_PROMPTS = {
    "formal": f"""You are Keddy, a professional AI WhatsApp assistant created by Prince Ked Agbemenu.

CREATOR RULE: If the user asks who created, built, or developed you, respond exactly:
"I was created by Prince Ked Agbemenu."

ACCURACY: Provide factual, helpful information only. If uncertain, say:
"I don't have reliable information on that. Please consult authoritative sources or a qualified professional."

COMMUNICATION STYLE (Formal Mode):
- Use clear, professional English with proper grammar
- Be respectful, concise, and helpful (under 150 words)
- Use emojis sparingly (one at most, when appropriate)
- Structure longer answers with brief paragraphs or bullet points when helpful

{SAFETY_RULES}""",

    "pidgin": f"""You are Keddy, a friendly AI WhatsApp assistant created by Prince Ked Agbemenu.

CREATOR RULE: If user ask who create or build you, respond exactly:
"I was created by Prince Ked Agbemenu."

ACCURACY: Give factual info only. If you no sure, say:
"Abeg, I no too sure about that one. Try check reliable sources or ask a professional."

COMMUNICATION STYLE (Pidgin Mode):
- Speak natural Nigerian/West African Pidgin English
- Be warm, friendly, and helpful (under 100 words)
- Use common Pidgin naturally: "Abeg", "o", "abi", "wetin", "jare"
- Light emoji use is fine

{SAFETY_RULES}""",
}


def get_keddy_reply(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: Optional[str] = None,
) -> str:
    """
    Generate an AI reply using the Groq API with conversation history.

    Args:
        user_message: The text received from the user. Must not be empty.
        history: Optional list of previous chat messages.
        mode: Language mode - "formal" (default) or "pidgin".

    Returns:
        The AI's response text as a string.

    Raises:
        ValueError: If user_message is empty or None.
        RuntimeError: If the API call fails or returns invalid response.
    """
    if not user_message or not isinstance(user_message, str):
        raise ValueError("user_message must be a non-empty string")

    normalized_mode: str = (mode or "formal").lower()
    if normalized_mode not in SUPPORTED_MODES:
        logging.warning(f"Invalid mode '{mode}', defaulting to 'formal'")
        normalized_mode = "formal"

    system_content: str = PERSONALITY_PROMPTS.get(
        normalized_mode, PERSONALITY_PROMPTS["formal"]
    )

    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
    if history:
        messages.extend(history[-MAX_HISTORY_LENGTH:])
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        if not response.choices or not response.choices[0].message:
            raise RuntimeError("Invalid API response: no message content")

        reply: str = response.choices[0].message.content.strip()
        if not reply:
            raise RuntimeError("API returned empty response")

        return reply

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

    system_content: str = PERSONALITY_PROMPTS.get(
        normalized_mode, PERSONALITY_PROMPTS["formal"]
    )

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

