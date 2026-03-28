"""
Service module for communicating with the Groq API.
Provides a single helper function to get a reply from the AI model with conversation history support.
"""

import os
import logging
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Retrieve the Groq API key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize the Groq client
client = Groq(api_key=GROQ_API_KEY)

# Model to use
MODEL_NAME = "llama-3.1-8b-instant"

# Personality prompt
PERSONALITY_PROMPT = """CRITICAL: 1. EXAMINE FULL HISTORY FIRST.
MODE RULES (obey strictly):
- FORMAL MODE (triggered by user saying 'formal English', 'proper English', 'speak formally', 'standard English'): Use ONLY formal standard English. NO Pidgin, NO slang, NO 'chale', NO contractions. Proper grammar/sentences. Remains until 'pidgin mode'.
- PIDGIN MODE (user says 'pidgin', 'chale', OR uses Pidgin like 'wetin', 'abeg'): Reply in Ghanaian Pidgin.
- SIMPLE (default/no triggers): Casual simple English.

2. Determine mode from history/triggers → APPLY STRICTLY to reply.

You are Keddy, Ghanaian WhatsApp helper. School, advice, maps (https://maps.app.goo.gl/...). Short, friendly."""


def get_keddy_reply(user_message: str, history: list = None) -> str:
    """
    Sends the user's message (with optional history) to the Groq API and returns the AI-generated reply.

    Parameters:
        user_message (str): The text received from the user.
        history (list): Optional list of previous chat messages [{"role": str, "content": str}].

    Returns:
        str: The AI's response text.

    Raises:
        Exception: If the API call fails or returns an error.
    """
    # Build messages list: system + history + current user msg
    messages = [{"role": "system", "content": PERSONALITY_PROMPT}]
    if history:
        messages += history
    messages.append({"role": "user", "content": user_message})

    try:
        # Call the Groq chat completion endpoint
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.3,
            max_tokens=300,
        )
        # Extract the assistant's reply
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        # Log the error
        logging.error(f"[Groq API Error] {e}")
        # Re-raise to let the caller handle it
        raise

