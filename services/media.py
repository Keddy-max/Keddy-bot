"""
Media download and processing for Twilio WhatsApp attachments.

Downloads images and voice notes from Twilio media URLs and prepares
them for Groq vision and speech-to-text APIs.

Security & validation:
- Only allowlisted MIME types are accepted (images + audio).
- File size is enforced to prevent resource exhaustion.
- Media is downloaded in memory (no permanent storage).
- Twilio credentials are used for authenticated downloads and never exposed.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, List, Optional

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

# Allowlisted image MIME types supported by the vision provider.
SUPPORTED_IMAGE_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/avif",
    }
)

# Allowlisted audio MIME types for Whisper.
SUPPORTED_AUDIO_MIME_TYPES = frozenset(
    {
        "audio/ogg",
        "audio/mpeg",
        "audio/mp4",
        "audio/amr",
        "audio/webm",
        "audio/wav",
    }
)


@dataclass
class MediaAttachment:
    """A single media file attached to an incoming WhatsApp message."""

    url: str
    content_type: str
    data: bytes

    @property
    def is_audio(self) -> bool:
        return (self.content_type or "").split(";")[0].strip().lower() in SUPPORTED_AUDIO_MIME_TYPES

    @property
    def is_image(self) -> bool:
        return (self.content_type or "").split(";")[0].strip().lower() in SUPPORTED_IMAGE_MIME_TYPES


@dataclass
class IncomingMessage:
    """Parsed Twilio WhatsApp webhook payload."""

    phone_number: str
    text: str
    media: List[MediaAttachment] = field(default_factory=list)

    @property
    def has_media(self) -> bool:
        return len(self.media) > 0

    @property
    def first_media(self) -> Optional[MediaAttachment]:
        return self.media[0] if self.media else None


def _base_mime(content_type: str) -> str:
    """Return the base MIME type (strip params) lowercased."""
    return (content_type or "").split(";")[0].strip().lower()


def parse_incoming_message(request_form: Any) -> IncomingMessage:
    """
    Parse phone, text, and optional media from a Twilio webhook form.

    Supports multiple media attachments (NumMedia > 0). For each attachment it
    reads MediaUrlN and MediaContentTypeN and downloads the binary data.

    Raises:
        ValueError: If required fields are missing or all media is invalid.
    """
    phone_number: Optional[str] = request_form.get("From")
    if not phone_number:
        raise ValueError("Missing 'From' field in request")

    raw_message = request_form.get("Body")
    if raw_message is None:
        raise ValueError("Missing 'Body' field in request")

    text = raw_message.strip()
    num_media = int(request_form.get("NumMedia", 0) or 0)

    media: List[MediaAttachment] = []
    if num_media > 0:
        for i in range(num_media):
            media_url = request_form.get(f"MediaUrl{i}")
            content_type = request_form.get(f"MediaContentType{i}", "")
            if not media_url or not content_type:
                # Skip incomplete attachments rather than failing the whole batch;
                # but if nothing valid is found we raise below.
                logging.warning(f"Media attachment {i} metadata is incomplete, skipping")
                continue
            try:
                media.append(download_twilio_media(media_url, content_type))
            except (RuntimeError, ValueError) as error:
                logging.warning(f"Skipping media attachment {i}: {error}")
                continue

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

    base_type = _base_mime(content_type)
    if not (base_type in SUPPORTED_IMAGE_MIME_TYPES or base_type in SUPPORTED_AUDIO_MIME_TYPES):
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
        raise RuntimeError("Could not download media attachment (it may be expired or invalid)") from error

    data = response.content

    if not data:
        raise ValueError("Media file is empty")

    if len(data) > MAX_MEDIA_BYTES:
        raise ValueError("Media file exceeds the 6MB size limit")

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
    return mapping.get(_base_mime(content_type), "voice.ogg")
