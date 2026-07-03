"""
Media download and processing for Twilio WhatsApp attachments.

Downloads images and voice notes from Twilio media URLs and prepares
them for Groq vision and speech-to-text APIs.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")

# WhatsApp/Twilio media size can be slightly larger than advertised depending
# on encoding/metadata. Add a small buffer to avoid false "exceeds limit".
MAX_MEDIA_BYTES: int = 6 * 1024 * 1024  # bytes

DOWNLOAD_TIMEOUT_SECONDS: int = 30

AUDIO_PREFIXES = ("audio/",)
IMAGE_PREFIXES = ("image/",)


@dataclass
class MediaAttachment:
    """A single media file attached to an incoming WhatsApp message."""

    url: str
    content_type: str
    data: bytes

    @property
    def is_audio(self) -> bool:
        return self.content_type.startswith(AUDIO_PREFIXES)

    @property
    def is_image(self) -> bool:
        return self.content_type.startswith(IMAGE_PREFIXES)


@dataclass
class IncomingMessage:
    """Parsed Twilio WhatsApp webhook payload."""

    phone_number: str
    text: str
    media: Optional[MediaAttachment] = None


def parse_incoming_message(request_form: Any) -> IncomingMessage:
    """
    Parse phone, text, and optional media from a Twilio webhook form.

    Raises:
        ValueError: If required fields are missing or media is invalid.
    """
    phone_number: Optional[str] = request_form.get("From")
    if not phone_number:
        raise ValueError("Missing 'From' field in request")

    raw_message = request_form.get("Body")
    if raw_message is None:
        raise ValueError("Missing 'Body' field in request")

    text = raw_message.strip()
    num_media = int(request_form.get("NumMedia", 0) or 0)

    media: Optional[MediaAttachment] = None
    if num_media > 0:
        media_url = request_form.get("MediaUrl0")
        content_type = request_form.get("MediaContentType0", "")
        if not media_url or not content_type:
            raise ValueError("Media attachment metadata is incomplete")
        media = download_twilio_media(media_url, content_type)

    if not text and not media:
        raise ValueError("Message contains no text or media")

    return IncomingMessage(phone_number=phone_number, text=text, media=media)


def download_twilio_media(url: str, content_type: str) -> MediaAttachment:
    """
    Download media from Twilio using HTTP Basic Auth.

    Raises:
        RuntimeError: If credentials are missing or download fails.
        ValueError: If media type or size is unsupported.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise RuntimeError(
            "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are required to process media"
        )

    if not (content_type.startswith(AUDIO_PREFIXES) or content_type.startswith(IMAGE_PREFIXES)):
        raise ValueError(f"Unsupported media type: {content_type}")

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=DOWNLOAD_TIMEOUT_SECONDS,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logging.error(f"Failed to download Twilio media: {error}")
        raise RuntimeError("Could not download media attachment") from error

    data = response.content

    if len(data) > MAX_MEDIA_BYTES:
        raise ValueError("Media file exceeds the 5MB size limit")

    # Some clients report a smaller size than the decoded bytes due to
    # transcoding/encoding differences. If Twilio returns exactly-at-limit
    # payloads, allow a small grace via MAX_MEDIA_BYTES buffer above.


    if not data:
        raise ValueError("Media file is empty")

    return MediaAttachment(url=url, content_type=content_type, data=data)


def audio_filename(content_type: str) -> str:
    """Return a filename extension hint for Groq Whisper uploads."""
    mapping = {
        "audio/ogg": "voice.ogg",
        "audio/mpeg": "voice.mp3",
        "audio/mp4": "voice.m4a",
        "audio/amr": "voice.amr",
        "audio/webm": "voice.webm",
        "audio/wav": "voice.wav",
    }
    return mapping.get(content_type.split(";")[0].strip(), "voice.ogg")
