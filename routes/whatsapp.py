"""
Flask Blueprint for handling Twilio WhatsApp webhook requests with logging, sanitization, and conversation history.
"""

from flask import Blueprint, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from services.groq_api import get_keddy_reply
import logging
from collections import defaultdict
from utils.helpers import sanitize_input

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

    # Simple in-memory session history per phone (use Redis in prod)
    session_history = defaultdict(list)
    history = session_history[phone_number]

    # Prepare Twilio response
    twiml_response = MessagingResponse()

    if not user_message:
        twiml_response.message("Hi! Send me a message and I'll reply. 😊")
        return Response(str(twiml_response), mimetype="application/xml")

    try:
        # Get AI reply with history
        ai_reply = get_keddy_reply(user_message, history)
        twiml_response.message(ai_reply)

        # Update history (keep last 6 exchanges ~12 msgs)
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": ai_reply})
        if len(history) > 12:
            history[:] = history[-12:]

        logging.info(f"Replied to {phone_number}")
    except Exception as e:
        logging.error(f"Error processing message for {phone_number}: {e}")
        fallback = "Sorry, I'm having a little trouble right now. Please try again! 🙏"
        twiml_response.message(fallback)

    # Return Twilio TwiML XML
    return Response(str(twiml_response), mimetype="application/xml")
