"""Shared bot logic for both WhatsApp and web chat.

This module exists to avoid duplicating chatbot response generation across
channels (WhatsApp webhook vs. /chat REST API).

Note:
- WhatsApp currently supports voice notes + images. Those flows remain in
  routes/whatsapp.py using `get_keddy_image_reply` and `transcribe_audio`.
- This module focuses on text-only reply generation using `get_keddy_reply`.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional

from services.groq_api import get_keddy_reply


def get_bot_response(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: str = "formal",
) -> str:
    """Generate a chatbot reply for text messages.

    Args:
        message: User message text (must be non-empty string).
        history: Optional conversation history (list of {role, content}).
        mode: Language style: "formal" or "pidgin".

    Returns:
        The assistant reply text.
    """

    # Let downstream enforce strictness; we keep this wrapper small.
    return get_keddy_reply(user_message=message, history=history, mode=mode)

