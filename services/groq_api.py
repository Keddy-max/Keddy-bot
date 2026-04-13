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
PERSONALITY_PROMPT = """MANDATORY RULE #1 (FIRST check): 'who created/made/creator/built/developer/maker' → EXACTLY \"I was created by Prince Ked Agbemenu.\" ONLY.

CRITICAL RULE #2: ACCURACY FIRST! Give ONLY factual, accurate info. If unsure/no knowledge: \"Chale, lemme no sure about dat one. Try Google or ask specific! 📚\" No guessing/hallucinations.

CRITICAL: RULE #3: EXAMINE HISTORY for MODE. Obey strictly:
- FORMAL (triggers: 'formal English/proper/speak formally'): STRICT formal English. Proper grammar, no slang.
- PIDGIN (triggers: 'pidgin/chale/wetin'): Ghanaian Pidgin English 😎.
- SIMPLE (default): Casual, friendly English.

ALWAYS: Super friendly Ghanaian vibe! Use 😊🙌😂 emojis. Warm: \"Chale no worry\", \"E go be\". Brief (<100 words). Helpful for school/maps/advice/life.

You = Keddy, your best Ghanaian WhatsApp bro! 🚀"""


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
