"""
Flask Blueprint for handling Twilio WhatsApp webhook requests.

Supports text messages, voice notes, and images via Twilio media attachments.

Vision flow (image messages):
    WhatsApp user -> webhook -> parse/download media -> vision service
    -> AI response -> reply to WhatsApp.

Text and voice-note flows are preserved unchanged.
"""

import os
from typing import Dict, Any, List, Optional
from flask import Blueprint, request, Response
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import logging

from services.groq_api import get_keddy_reply, get_keddy_image_reply, transcribe_audio
from services.media import (
    parse_incoming_message,
    IncomingMessage,
    MediaAttachment,
    audio_filename,
)
from services.vision import VisionError, analyze_image
from utils.helpers import sanitize_input
from utils.compliance import (
    mask_phone,
    is_opted_out,
    opt_out,
    opt_in,
    is_keyword_command,
    is_blocked_content,
    STOP_KEYWORDS,
    START_KEYWORDS,
    HELP_KEYWORDS,
    DELETE_KEYWORDS,
    PRIVACY_KEYWORDS,
    get_help_message,
    get_welcome_message,
    get_stop_message,
    get_start_message,
    get_delete_message,
    get_privacy_message,
    get_opted_out_reply,
    BLOCKED_CONTENT_REPLY,
)

DEFAULT_MODE: str = "formal"
MAX_HISTORY_LENGTH: int = 12
EMPTY_MESSAGE_REPLY: str = (
    "Hello! I'm Keddy, your AI WhatsApp assistant. "
    "Send a text message, voice note, or image — or type HELP for commands."
)
ERROR_REPLY: str = (
    "Hmm — I ran into a problem. Please try again in a moment."
)
MEDIA_ERROR_REPLY: str = (
    "I couldn’t process that attachment. "
    "Try sending a voice note or image (up to ~6MB), and I’ll handle it."
)
IMAGE_ERROR_REPLY: str = (
    "Sorry, I couldn't process that image right now. "
    "Please try sending it again."
)
UNSUPPORTED_MEDIA_REPLY: str = (
    "I can read voice notes and images (JPEG, PNG, WebP). "
    "Send one of those formats and we’re good."
)


TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
BASE_URL: str = os.getenv("BASE_URL", "https://keddy-bot.onrender.com").rstrip("/")

session_data: Dict[str, Dict[str, Any]] = {}

whatsapp_bp: Blueprint = Blueprint("whatsapp", __name__)


def _validate_twilio_request() -> bool:
    """Validate incoming webhook request signature from Twilio."""
    if not TWILIO_AUTH_TOKEN:
        logging.warning("TWILIO_AUTH_TOKEN not set — skipping webhook validation")
        return True

    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = request.url

    if request.headers.get("X-Forwarded-Proto") == "https":
        url = url.replace("http://", "https://", 1)

    return validator.validate(url, request.form, signature)


def _detect_mode(user_message: str, current_mode: str) -> str:
    """Detect if user requested a language mode change."""
    user_lower: str = user_message.lower()

    formal_triggers = [
        "formal english", "proper english", "speak formally",
        "standard english", "formal",
    ]
    pidgin_triggers = [
        "pidgin", "nigerian english", "speak pidgin", "talk pidgin",
        "abeg", "wetin", "abi", "jare", "eh", "sef",
    ]

    if any(trigger in user_lower for trigger in pidgin_triggers):
        return "pidgin"
    if any(trigger in user_lower for trigger in formal_triggers):
        return "formal"

    return current_mode


def _handle_compliance_command(
    phone: str, message: str, data: Dict[str, Any]
) -> Optional[str]:
    """Handle STOP, START, HELP, DELETE, and PRIVACY commands."""
    if is_keyword_command(message, STOP_KEYWORDS):
        opt_out(phone)
        data["history"] = []
        data["last_image_context"] = ""
        return get_stop_message()

    if is_keyword_command(message, START_KEYWORDS):
        opt_in(phone)
        data["welcomed"] = True
        return get_start_message()

    if is_keyword_command(message, HELP_KEYWORDS):
        return get_help_message(BASE_URL)

    if is_keyword_command(message, DELETE_KEYWORDS):
        data["history"] = []
        data["last_image_context"] = ""
        return get_delete_message()

    if is_keyword_command(message, PRIVACY_KEYWORDS):
        return get_privacy_message(BASE_URL)

    return None


def _history_label_for_media(incoming: IncomingMessage) -> str:
    """Build a history-friendly label for media messages."""
    image_count = sum(1 for m in incoming.media if m.is_image)
    audio_count = sum(1 for m in incoming.media if m.is_audio)

    if image_count:
        prefix = f"[{image_count} Image{'s' if image_count > 1 else ''}]"
    elif audio_count:
        prefix = f"[{audio_count} Voice note{'s' if audio_count > 1 else ''}]"
    else:
        return incoming.text

    if incoming.text:
        return f"{prefix} {incoming.text}"
    return prefix


def _resolve_user_input(
    incoming: IncomingMessage,
    mode: str,
) -> tuple[str, str, Optional[str]]:
    """
    Convert incoming message (text/media) into AI input.

    Returns:
        Tuple of (ai_input, history_entry, ai_reply_or_none).
        - Audio is transcribed and returned as text input (ai_reply is None).
        - Images are returned with ai_reply=None so the caller runs vision.
        - Pure text returns text as ai_input.
    """
    text = sanitize_input(incoming.text) if incoming.text else ""

    if not incoming.media:
        return text, text, None

    media = incoming.media
    images = [m for m in media if m.is_image]
    audios = [m for m in media if m.is_audio]

    # Audio only (no images): transcribe and treat as text.
    if audios and not images:
        transcripts: List[str] = []
        for m in audios:
            transcript = transcribe_audio(m.data, audio_filename(m.content_type))
            transcripts.append(transcript)
        joined = " | ".join(transcripts)
        if text:
            ai_input = f"{text}\n\n[Voice note]: {joined}"
            history_entry = f"[Voice note] {text}: {joined}"
        else:
            ai_input = joined
            history_entry = f"[Voice note]: {joined}"
        return ai_input, history_entry, None

    # Any images present: handled by the caller via the vision service.
    if images:
        history_entry = _history_label_for_media(incoming)
        return text or "[Image sent]", history_entry, None

    raise ValueError(f"Unsupported media type: {[m.content_type for m in media]}")


def _analyze_images(
    images: List[MediaAttachment],
    user_text: str,
    history: List[Dict[str, str]],
    mode: str,
) -> str:
    """Analyze one or more images via the vision service.

    The actual image bytes and the user's text are both sent to the model.
    A short context note is included so follow-up questions about a previously
    analyzed image keep working.
    """
    if len(images) == 1:
        return analyze_image(
            image_bytes=images[0].data,
            content_type=images[0].content_type,
            user_prompt=user_text,
            history=history,
            mode=mode,
        )

    # Multiple images: analyze each and combine concise results.
    combined: List[str] = []
    for idx, img in enumerate(images, start=1):
        prompt = user_text if user_text else f"Describe image {idx} briefly."
        if user_text:
            prompt = f"About image {idx} of {len(images)}: {user_text}"
        combined.append(
            analyze_image(
                image_bytes=img.data,
                content_type=img.content_type,
                user_prompt=prompt,
                history=history,
                mode=mode,
            )
        )
    return "\n\n".join(combined)


@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook() -> Response:
    """Handle incoming WhatsApp messages including text, voice notes, and images."""
    twiml_response: MessagingResponse = MessagingResponse()

    try:
        if not _validate_twilio_request():
            logging.warning("Invalid Twilio webhook signature — request rejected")
            return Response("Forbidden", status=403)

        incoming = parse_incoming_message(request.form)
        phone_number = incoming.phone_number
        user_id = mask_phone(phone_number)

        media_type = "none"
        if incoming.media:
            if any(m.is_image for m in incoming.media):
                media_type = "image"
            elif any(m.is_audio for m in incoming.media):
                media_type = "audio"
        logging.info(f"Incoming {media_type} message from {user_id}")

        if phone_number not in session_data:
            session_data[phone_number] = {
                "history": [],
                "mode": DEFAULT_MODE,
                "welcomed": False,
                "last_image_context": "",
            }

        data: Dict[str, Any] = session_data[phone_number]
        text_for_commands = sanitize_input(incoming.text) if incoming.text else ""

        if text_for_commands:
            compliance_reply = _handle_compliance_command(
                phone_number, text_for_commands, data
            )
            if compliance_reply is not None:
                twiml_response.message(compliance_reply)
                return Response(str(twiml_response), mimetype="application/xml")

        if is_opted_out(phone_number):
            twiml_response.message(get_opted_out_reply())
            return Response(str(twiml_response), mimetype="application/xml")

        if not incoming.text and not incoming.media:
            twiml_response.message(EMPTY_MESSAGE_REPLY)
            return Response(str(twiml_response), mimetype="application/xml")

        if not data.get("welcomed"):
            data["welcomed"] = True
            twiml_response.message(get_welcome_message(BASE_URL))

        mode: str = data["mode"]
        history: List[Dict[str, str]] = data["history"]

        if incoming.text:
            detected_mode = _detect_mode(text_for_commands, mode)
            if detected_mode != mode:
                data["mode"] = detected_mode
                mode = detected_mode
                logging.info(f"Mode switched to {detected_mode} for {user_id}")

        try:
            ai_input, history_entry, direct_reply = _resolve_user_input(
                incoming, mode
            )
        except ValueError as error:
            logging.warning(f"Unsupported media: {error}")
            twiml_response.message(UNSUPPORTED_MEDIA_REPLY)
            return Response(str(twiml_response), mimetype="application/xml")
        except (RuntimeError, VisionError) as error:
            logging.error(f"Media processing failed: {error}")
            twiml_response.message(IMAGE_ERROR_REPLY)
            return Response(str(twiml_response), mimetype="application/xml")

        if ai_input and is_blocked_content(ai_input):
            twiml_response.message(BLOCKED_CONTENT_REPLY)
            return Response(str(twiml_response), mimetype="application/xml")

        # Determine whether this message contains images to analyze.
        images = [m for m in incoming.media if m.is_image]

        if images:
            # Vision flow: include stored image context for follow-up questions.
            context_history = list(history)
            if data.get("last_image_context"):
                context_history.append(
                    {"role": "assistant", "content": data["last_image_context"]}
                )
            try:
                ai_reply = _analyze_images(
                    images=images,
                    user_text=ai_input or "",
                    history=context_history,
                    mode=mode,
                )
            except (VisionError, RuntimeError, ValueError) as error:
                logging.error(f"Vision processing failed for {user_id}: {error}")
                twiml_response.message(IMAGE_ERROR_REPLY)
                return Response(str(twiml_response), mimetype="application/xml")

            # Remember a short summary of the image description for follow-ups.
            data["last_image_context"] = ai_reply[:300]
        elif direct_reply:
            ai_reply = direct_reply
        else:
            # Shared bot logic (text-only) reused by web chat as well.
            from services.bot_engine import get_bot_response

            ai_reply = get_bot_response(message=ai_input, history=history, mode=mode)

        twiml_response.message(ai_reply)

        data["history"].append({"role": "user", "content": history_entry or ai_input})
        data["history"].append({"role": "assistant", "content": ai_reply})
        if len(data["history"]) > MAX_HISTORY_LENGTH:
            data["history"][:] = data["history"][-MAX_HISTORY_LENGTH:]

        logging.info(f"Successfully replied to {user_id}")

    except ValueError as error:
        logging.warning(f"Invalid request format: {error}")
        twiml_response.message(EMPTY_MESSAGE_REPLY)
    except Exception as error:
        logging.error(
            f"Error processing message: {type(error).__name__}: {error}",
            exc_info=True,
        )
        twiml_response.message(ERROR_REPLY)

    return Response(str(twiml_response), mimetype="application/xml")
