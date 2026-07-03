"""
Compliance utilities for Keddy WhatsApp bot.

Handles opt-out management, keyword commands, privacy-conscious logging,
and basic content safety checks required for Meta/WhatsApp platform approval.
"""

import hashlib
import re
from typing import Optional, Set

# Users who have opted out via STOP
opted_out_users: Set[str] = set()

# Standard messaging compliance keywords (case-insensitive, whole-word)
STOP_KEYWORDS = frozenset({"stop", "unsubscribe", "cancel", "quit", "end"})
START_KEYWORDS = frozenset({"start", "subscribe", "unstop"})
HELP_KEYWORDS = frozenset({"help", "info", "commands"})
DELETE_KEYWORDS = frozenset({"delete", "forget", "clear data", "erase"})
PRIVACY_KEYWORDS = frozenset({"privacy", "policy", "terms"})

# Patterns for potentially harmful user input (basic pre-AI filter)
BLOCKED_PATTERNS = [
    re.compile(r"\b(kill\s+yourself|kys)\b", re.IGNORECASE),
    re.compile(r"\b(bomb\s+making|how\s+to\s+make\s+a\s+bomb)\b", re.IGNORECASE),
]

BLOCKED_CONTENT_REPLY = (
    "I'm unable to assist with that request. "
    "If you need support, please contact a qualified professional or local authorities."
)


def mask_phone(phone: str) -> str:
    """Return a privacy-safe identifier for logging (hashed prefix)."""
    if not phone:
        return "unknown"
    digest = hashlib.sha256(phone.encode()).hexdigest()[:12]
    return f"user_{digest}"


def normalize_command(message: str) -> str:
    """Normalize message for keyword command matching."""
    return message.strip().lower()


def is_keyword_command(message: str, keywords: frozenset) -> bool:
    """Check if message is an exact keyword command."""
    return normalize_command(message) in keywords


def is_opted_out(phone: str) -> bool:
    """Check if user has opted out of the service."""
    return phone in opted_out_users


def opt_out(phone: str) -> None:
    """Mark user as opted out."""
    opted_out_users.add(phone)


def opt_in(phone: str) -> None:
    """Remove user from opt-out list."""
    opted_out_users.discard(phone)


def is_blocked_content(message: str) -> bool:
    """Basic content safety check before sending to AI."""
    if not message:
        return False
    return any(pattern.search(message) for pattern in BLOCKED_PATTERNS)


def get_help_message(base_url: str) -> str:
    """Return professional help menu text."""
    return (
        "Welcome to Keddy — your AI WhatsApp assistant.\n\n"
        "How to use:\n"
        "• Send any text message to chat with Keddy\n"
        "• Send a voice note — Keddy will listen and reply\n"
        "• Send an image — Keddy can describe it or answer questions\n"
        "• Say \"formal\" or \"pidgin\" to switch language style\n\n"
        "Commands:\n"
        "• HELP — Show this menu\n"
        "• STOP — Opt out of messages\n"
        "• START — Re-subscribe\n"
        "• DELETE — Clear your conversation history\n"
        "• PRIVACY — Privacy policy link\n\n"
        f"Privacy Policy: {base_url}/privacy\n"
        f"Terms of Service: {base_url}/terms\n\n"
        "Keddy uses AI (Groq) to generate replies. "
        "Do not rely on Keddy for medical, legal, or financial advice."
    )


def get_welcome_message(base_url: str) -> str:
    """Return first-contact welcome with consent disclosure."""
    return (
        "Hello! I'm Keddy, your AI WhatsApp assistant, created by Prince Ked Agbemenu.\n\n"
        "By continuing this conversation, you agree to our Privacy Policy and Terms:\n"
        f"{base_url}/privacy\n"
        f"{base_url}/terms\n\n"
        "Send HELP for commands. You can send text, voice notes, or images.\n"
        "Reply STOP at any time to opt out."
    )


def get_stop_message() -> str:
    """Return opt-out confirmation."""
    return (
        "You have been unsubscribed from Keddy and will no longer receive messages. "
        "Send START to re-subscribe. Message and data rates may apply."
    )


def get_start_message() -> str:
    """Return re-subscribe confirmation."""
    return (
        "Welcome back to Keddy! You are now re-subscribed. "
        "Send HELP for commands or ask me anything."
    )


def get_delete_message() -> str:
    """Return data deletion confirmation."""
    return (
        "Your conversation history has been cleared from our session. "
        "Send a new message anytime to start fresh."
    )


def get_privacy_message(base_url: str) -> str:
    """Return privacy policy link."""
    return (
        f"Keddy Privacy Policy: {base_url}/privacy\n"
        f"Terms of Service: {base_url}/terms\n\n"
        "Send DELETE to clear your conversation history, or STOP to opt out."
    )


def get_opted_out_reply() -> str:
    """Return message when opted-out user tries to chat."""
    return (
        "You are currently unsubscribed from Keddy. "
        "Send START to re-subscribe and continue chatting."
    )
