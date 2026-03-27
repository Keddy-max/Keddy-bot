"""
Utility helpers for the Keddy bot.
Currently contains a simple function to sanitize user input.
"""

def sanitize_input(text: str) -> str:
    """
    Basic sanitization: strip leading/trailing whitespace and limit length.
    """
    return text.strip()[:500]  # limit to 500 chars to avoid abuse