"""
Flask Blueprint for handling Twilio WhatsApp webhook requests with logging, sanitization, and conversation history.
"""

from flask import Blueprint, request, Response
from twilio.twiml.messaging_response import MessagingResponse
import logging
from collections import defaultdict

from services.groq_api import get_keddy_reply
from utils.helpers import sanitize_input

# Default locked mode: formal English
DEFAULT_MODE = "formal"

# Persistent session storage (use Redis in production)
session_data = {}

# Create a Blueprint for WhatsApp routes
whatsapp_bp = Blueprint("whatsapp", __name__)


@whatsapp_bp.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    """
    Endpoint that Twilio POSTs to when WhatsApp message received.
    Sanitizes input, maintains simple session history, calls Groq, responds.
    """
    # Extract phone and message
    phone_number = request.form.get("From", "unknown")
    raw_message = request.form.get("Body", "")
    user_message = sanitize_input(raw_message)

    logging.info(f"Incoming message from {phone_number}: {user_message}")

    # Initialize or retrieve session data for this phone
    if phone_number not in session_data:
        session_data[phone_number] = {"history": [], "mode": DEFAULT_MODE}
    
    data = session_data[phone_number]
    history = data["history"]

    # Prepare Twilio response
    twiml_response = MessagingResponse()

    if not user_message:
        twiml_response.message("Hi! Send me a message and I'll reply. 😊")
        return Response(str(twiml_response), mimetype="application/xml")

    # Detect language mode from user message.
    # Start with current mode, only switch if explicitly triggered
    user_lower = user_message.lower()

    formal_triggers = [
        "formal english",
        "proper english",
        "speak formally",
        "standard english",
    ]
    pidgin_triggers = [
        "pidgin",
        "chale mode",
        "speak pidgin",
        # common pidgin tokens
        "weyin",
        "wetin",
        "chale",
        "e no",
        "make we",
        "abeg",
    ]

    # Only switch mode if explicit trigger is found
    if any(k in user_lower for k in pidgin_triggers):
        data["mode"] = "pidgin"
        logging.info(f"Switched {phone_number} to pidgin mode")
    elif any(k in user_lower for k in formal_triggers):
        data["mode"] = "formal"
        logging.info(f"Switched {phone_number} to formal mode")
    
    mode = data["mode"]
    logging.info(f"Using mode: {mode} for {phone_number}")

    try:
        # Get AI reply with history and mode
        ai_reply = get_keddy_reply(user_message, history, mode)
        twiml_response.message(ai_reply)

        # Update history (keep last 6 exchanges ~12 msgs)
        data["history"].append({"role": "user", "content": user_message})
        data["history"].append({"role": "assistant", "content": ai_reply})
        if len(data["history"]) > 12:
            data["history"][:] = data["history"][-12:]

        logging.info(f"Replied to {phone_number}")
    except Exception as e:
        logging.error(f"Error processing message for {phone_number}: {e}")
        fallback = "Sorry, I'm having a little trouble right now. Please try again! 🙏"
        twiml_response.message(fallback)

    # Return Twilio TwiML XML
    return Response(str(twiml_response), mimetype="application/xml")

