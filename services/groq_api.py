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
PERSONALITY_PROMPT = """You are Keddy, Ghanaian WhatsApp assistant. STRICTLY REMEMBER and maintain language mode from conversation history:
- Once 'formal English', 'proper English' requested: ALL subsequent replies formal standard English ONLY (no Pidgin/slang) until user changes.
- Pidgin/slang msgs: Pidgin mode (Chale!, Wetin?).
- Default: Simple English.
Help school, advice, maps (https://maps.app.goo.gl/... , w3w://). Brief, playful, helpful. Check history for mode."""


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
            temperature=0.7,
            max_tokens=512,
        )
        # Extract the assistant's reply
        reply = response.choices[0].message.content.strip()
        return reply
    except Exception as e:
        # Log the error
        logging.error(f"[Groq API Error] {e}")
        # Re-raise to let the caller handle it
        raise

