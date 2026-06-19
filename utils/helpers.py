"""
Utility helper functions for the Keddy bot.

Provides input validation and sanitization to ensure secure processing
of user-supplied data.
"""

from typing import Optional

# Configuration constants
MAX_INPUT_LENGTH: int = 500


def sanitize_input(text: Optional[str]) -> str:
    """
    Sanitize and validate user input text.

    Performs basic sanitization by stripping whitespace and enforcing
    a maximum length limit to prevent abuse and resource exhaustion.

    Args:
        text: Raw text input from user. Can be None or any value.

    Returns:
        Sanitized text string, limited to MAX_INPUT_LENGTH characters.

    Raises:
        ValueError: If text is not a string or None.

    Example:
        >>> sanitize_input("  Hello  ")
        'Hello'
        >>> len(sanitize_input("x" * 600))
        500
    """
    # Validate input type
    if text is None:
        return ""

    if not isinstance(text, str):
        raise ValueError(f"Expected string, got {type(text).__name__}")

    # Strip whitespace and limit length
    sanitized: str = text.strip()[:MAX_INPUT_LENGTH]
    return sanitized