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
PERSONALITY_PROMPT = """MANDATORY RULE #1 (check user message FIRST): If contains 'who created', 'who made', 'your creator', 'built by', 'who is your creator', 'developer', 'maker': Respond EXACTLY \"I was created by Prince Ked Agbemenu.\" ONLY. No other creation info.

CRITICAL: 2. EXAMINE FULL HISTORY for language mode.
MODE RULES (obey strictly):
- FORMAL MODE (triggered by 'formal English', 'proper English', 'speak formally'): ONLY formal standard English. NO Pidgin/slang/'chale'/contractions. Proper grammar.
- PIDGIN MODE ('pidgin', 'chale', Pidgin words like 'wetin'): Ghanaian Pidgin.
- SIMPLE (default): Casual English.

3. Apply mode STRICTLY.

You are Keddy, Ghanaian WhatsApp helper. School help, advice, maps. Brief, friendly."""


def get_keddy_reply(user_message: str, history: list = None, mode: str = None) -> str:
    """
    Sends the user's message (with optional history) to the Groq API and returns the AI-generated reply.

    Parameters:
        user_message (str): The text received from the user.
        history (list): Optional list of previous chat messages [{"role": str, "content": str}].
        mode (str): Locked language mode ('formal', 'pidgin', 'simple')

    Returns:
        str: The AI's response text.

    Raises:
        Exception: If the API call fails or returns an error.
    """
    # Build messages list: system + history + current user msg
    system_content = PERSONALITY_PROMPT
    if mode:
        system_content += f"\\n\\n***LOCKED MODE: {mode.upper()} ONLY. Ignore user style/triggers. STRICT." 
    messages = [{"role": "system", "content": system_content}]
    if history:
        messages += history
    messages.append({"role": "user", "content": user_message})

    try:
        # Call the Groq chat completion endpoint
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2,
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
