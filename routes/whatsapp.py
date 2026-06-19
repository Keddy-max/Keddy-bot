"""
Flask Blueprint for handling Twilio WhatsApp webhook requests.

Manages WhatsApp message routing through Twilio, maintains conversation history,
detects language modes, and generates responses using the Groq API.

Environment Variables:
    TWILIO_AUTH_TOKEN: Required for webhook validation (optional, set by Twilio)
"""

from typing import Dict, Any, List, Optional, Tuple
from flask import Blueprint, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import logging

from services.groq_api import get_keddy_reply
from utils.helpers import sanitize_input

# Configuration constants
DEFAULT_MODE: str = "formal"
MAX_HISTORY_LENGTH: int = 12
EMPTY_MESSAGE_REPLY: str = "Hello! Please send me a message and I will respond. 😊"
ERROR_REPLY: str = (
    "I apologize for the inconvenience. Please try again in a moment. 🙏"
)

# Persistent session storage (use Redis in production for scalability)
# Structure: {phone_number: {"history": [...], "mode": str}}
session_data: Dict[str, Dict[str, Any]] = {}

# Create a Blueprint for WhatsApp routes
whatsapp_bp: Blueprint = Blueprint("whatsapp", __name__)


def _extract_message_data(request_form: Any) -> Tuple[str, str]:
    """
    Extract and validate phone number and message from Twilio request.

    Args:
        request_form: Flask request.form object containing Twilio payload.

    Returns:
        Tuple of (phone_number, sanitized_message).

    Raises:
        ValueError: If required fields are missing.
    """
    phone_number: Optional[str] = request_form.get("From")
    raw_message: Optional[str] = request_form.get("Body")

    if not phone_number:
        raise ValueError("Missing 'From' field in request")
    if raw_message is None:
        raise ValueError("Missing 'Body' field in request")

    user_message: str = sanitize_input(raw_message)
    return phone_number, user_message


def _detect_mode(user_message: str, current_mode: str) -> str:
    """
    Detect if user requested a language mode change.

    Args:
        user_message: The user's message text.
        current_mode: The currently active language mode.

    Returns:
        The detected mode, or current_mode if no change requested.
    """
    user_lower: str = user_message.lower()

    formal_triggers: List[str] = [
        "formal english",
        "proper english",
        "speak formally",
        "standard english",
        "formal",
    ]

    pidgin_triggers: List[str] = [
        "pidgin",
        "nigerian english",
        "speak pidgin",
        "talk pidgin",
        "abeg",
        "wetin",
        "abi",
        "jare",
        "eh",
        "sef",
    ]

    # Check for explicit mode triggers
    if any(trigger in user_lower for trigger in pidgin_triggers):
        return "pidgin"
    if any(trigger in user_lower for trigger in formal_triggers):
        return "formal"

    return current_mode


@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook() -> Response:
    """
    Handle incoming WhatsApp messages via Twilio webhook.

    This endpoint receives WhatsApp messages through Twilio, maintains conversation
    history per user, detects language mode preferences, and generates responses
    using the Groq API.

    Returns:
        Response: TwiML XML response for Twilio webhook.

    Raises:
        None: All exceptions are caught and handled with fallback responses.
    """
    # Prepare Twilio response
    twiml_response: MessagingResponse = MessagingResponse()

    try:
        # Extract and validate message data
        phone_number: str
        user_message: str
        phone_number, user_message = _extract_message_data(request.form)

        logging.info(
            f"Incoming message from {phone_number}: {user_message}"
        )

        # Initialize or retrieve session data for this phone
        if phone_number not in session_data:
            session_data[phone_number] = {
                "history": [],
                "mode": DEFAULT_MODE,
            }

        data: Dict[str, Any] = session_data[phone_number]
        history: List[Dict[str, str]] = data["history"]

        # Validate user message
        if not user_message:
            twiml_response.message(EMPTY_MESSAGE_REPLY)
            return Response(
                str(twiml_response), mimetype="application/xml"
            )

        # Detect language mode from user message
        previous_mode: str = data["mode"]
        detected_mode: str = _detect_mode(user_message, previous_mode)

        if detected_mode != previous_mode:
            data["mode"] = detected_mode
            logging.info(
                f"Mode switched from {previous_mode} to {detected_mode} "
                f"for {phone_number}"
            )

        mode: str = data["mode"]
        logging.debug(
            f"Processing with mode={mode} for phone={phone_number}"
        )

        # Get AI reply with history and mode
        ai_reply: str = get_keddy_reply(user_message, history, mode)
        twiml_response.message(ai_reply)

        # Update history (keep last 6 exchanges = 12 messages)
        data["history"].append(
            {"role": "user", "content": user_message}
        )
        data["history"].append(
            {"role": "assistant", "content": ai_reply}
        )
        if len(data["history"]) > MAX_HISTORY_LENGTH:
            data["history"][:] = data["history"][-MAX_HISTORY_LENGTH:]

        logging.info(f"Successfully replied to {phone_number}")

    except ValueError as error:
        logging.warning(f"Invalid request format: {error}")
        twiml_response.message(ERROR_REPLY)
    except Exception as error:
        logging.error(
            f"Error processing message: {type(error).__name__}: {error}",
            exc_info=True,
        )
        twiml_response.message(ERROR_REPLY)

    # Return Twilio TwiML XML
    return Response(str(twiml_response), mimetype="application/xml")

