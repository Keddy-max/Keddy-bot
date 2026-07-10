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
    session_id = data.get("session_id") if isinstance(data, dict) else None
    if not isinstance(session_id, str) or not session_id.strip():
        # Stateless fallback (first message / unknown session)
        session_id = "anonymous"

    # In-memory per-session history (best-effort; resets on server restart).
    # IMPORTANT: This is separate from WhatsApp in-memory history.
    if not hasattr(chat, "session_data"):
        chat.session_data = {}

    session_data: Dict[str, Any] = chat.session_data  # type: ignore[attr-defined]
    if session_id not in session_data:
        session_data[session_id] = {"history": []}

    history = session_data[session_id].get("history") or []
    if not isinstance(history, list):
        history = []

    # Optional: allow widget to request language style.
    mode = data.get("mode") if isinstance(data, dict) else None
    reply = get_bot_response(message=message.strip(), history=history, mode=mode or "formal")

    # Update stored history.
    history.append({"role": "user", "content": message.strip()})
    history.append({"role": "assistant", "content": reply})

    # Keep last turns reasonable for cost/latency.
    if len(history) > 24:
        history[:] = history[-24:]

    session_data[session_id]["history"] = history

    return jsonify({"reply": reply}), 200


