"""REST API routes for web chat.

This endpoint is intentionally separate from the WhatsApp webhook route.
It reuses the same underlying bot response generation logic.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from flask import Blueprint, jsonify, request

from services.bot_engine import get_bot_response


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chat", methods=["POST"])
def chat() -> Tuple[Any, int]:
    """Generate a reply for web chat.

    Expects JSON:
        {"message": "Hello"}

    Returns JSON:
        {"reply": "..."}
    """

    try:
        data: Dict[str, Any] = request.get_json(force=True, silent=False)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    message = data.get("message") if isinstance(data, dict) else None
    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "'message' must be a non-empty string"}), 400

    # Text-only web chat response.
    # Web chat keeps lightweight server-side context per client session.
    # (No change to API shape.)
    history = None
    reply = get_bot_response(message=message.strip(), history=history, mode="formal")

    return jsonify({"reply": reply}), 200

