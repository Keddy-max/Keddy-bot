"""
Service module for communicating with the Groq API.

Provides helper functions to generate AI replies with conversation history support
using the Groq API. Supports multiple language modes (formal and pidgin).

Environment Variables:
    GROQ_API_KEY: API key for Groq service (required)

Raises:
    ValueError: If required environment variables are missing
"""

import os
import logging
from typing import Optional, List, Dict, Any
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve the Groq API key from environment
GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY environment variable is not set. "
        "Please configure your Groq API key in the .env file."
    )

# Initialize the Groq client
try:
    client: Groq = Groq(api_key=GROQ_API_KEY)
except Exception as error:
    logging.error(f"Failed to initialize Groq client: {error}")
    raise

# Model to use
MODEL_NAME: str = "llama-3.1-8b-instant"

# Configuration constants
MAX_TOKENS: int = 300
TEMPERATURE: float = 0.2
MAX_HISTORY_LENGTH: int = 12
SUPPORTED_MODES: List[str] = ["formal", "pidgin"]

# Personality prompts for different modes
PERSONALITY_PROMPTS = {
    "formal": """MANDATORY RULE #1 (FIRST check): If user asks 'who created/made/creator/built/developer/maker' → EXACTLY respond \"I was created by Prince Ked Agbemenu.\" ONLY. Nothing else.

CRITICAL RULE #2: ACCURACY FIRST! Provide only factual, accurate information. If uncertain or lacking knowledge, respond: "I apologize, but I do not have reliable information on that topic. I recommend consulting authoritative sources or conducting a web search." No guessing or hallucinations.

CRITICAL RULE #3: Communication Style - FORMAL MODE (DEFAULT):
- Use proper formal English with sophisticated vocabulary
- Maintain professional and respectful tone
- Use complete sentences with proper grammar
- Provide clear, well-structured responses
- Keep responses concise but comprehensive (<150 words typically)
- Avoid slang, colloquialisms, and informal language
- Use 😊 emoji sparingly and professionally

Your role: You are Keddy, an intelligent and professional WhatsApp assistant. Provide helpful, accurate, and professionally-toned responses.""",

    "pidgin": """MANDATORY RULE #1 (FIRST check): If user ask 'who create/make/creator/build/maker' → EXACTLY say \"I was created by Prince Ked Agbemenu.\" Full stop.

CRITICAL RULE #2: ACCURACY FIRST! Give real real factual info. If you no sure or you no know: \"Abeg, I no too sure about that matter o. Try Google or ask somebody wey know am well well! 📚\" No lie lie.

CRITICAL RULE #3: Communication Style - PIDGIN/CASUAL MODE:
- Speak in Nigerian/West African Pidgin English (natural flow)
- Use common Pidgin phrases: "Abeg", "o", "jare", "abi", "sef", "na so", "eh", "wetin", "innit"
- Be friendly, humorous, relatable - like talking to a mate
- Keep responses brief but entertaining (<100 words typically)
- Use emojis: 😊🙌😂😆
- Be helpful but maintain the vibe, no be formal

You = Keddy, your best WhatsApp bro! Your style na Pidgin, make we talk like bros! 🚀"""
}

def get_keddy_reply(
    user_message: str,
    history: Optional[List[Dict[str, str]]] = None,
    mode: Optional[str] = None,
) -> str:
    """
    Generate an AI reply using the Groq API with conversation history.

    This function sends a user message to the Groq API and returns an
    AI-generated response. It supports multiple language modes and maintains
    conversation context through message history.

    Args:
        user_message: The text received from the user. Must not be empty.
        history: Optional list of previous chat messages in format
                 [{"role": "user"|"assistant", "content": str}].
        mode: Language mode - "formal" (default) or "pidgin". Invalid modes
              default to "formal".

    Returns:
        The AI's response text as a string.

    Raises:
        ValueError: If user_message is empty or None.
        RuntimeError: If the API call fails or returns invalid response.
    """
    # Validate input
    if not user_message or not isinstance(user_message, str):
        raise ValueError("user_message must be a non-empty string")

    # Normalize and validate mode
    normalized_mode: str = (mode or "formal").lower()
    if normalized_mode not in SUPPORTED_MODES:
        logging.warning(
            f"Invalid mode '{mode}', defaulting to 'formal'"
        )
        normalized_mode = "formal"

    # Select appropriate system prompt based on mode
    system_content: str = PERSONALITY_PROMPTS.get(
        normalized_mode, PERSONALITY_PROMPTS["formal"]
    )

    # Build messages list: system + history + current user message
    messages: List[Dict[str, str]] = [{"role": "system", "content": system_content}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        # Call the Groq chat completion endpoint
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )

        # Extract and validate the assistant's reply
        if not response.choices or not response.choices[0].message:
            raise RuntimeError("Invalid API response: no message content")

        reply: str = response.choices[0].message.content.strip()
        if not reply:
            raise RuntimeError("API returned empty response")

        return reply

    except Exception as error:
        logging.error(
            f"Groq API error: {type(error).__name__}: {error}"
        )
        raise RuntimeError(f"Failed to generate reply: {error}") from error
