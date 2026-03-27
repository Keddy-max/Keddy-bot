"""
Main entry point for the Keddy WhatsApp AI chatbot.
Sets up Flask, loads environment variables, and registers routes.
"""

import os
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Create Flask app
app = Flask(__name__)

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50/hour"]
)

# Import routes after app creation to avoid circular imports
from routes.whatsapp import whatsapp_bp

# Register the WhatsApp Blueprint
app.register_blueprint(whatsapp_bp)

# Health check routes
@app.route("/status", methods=["GET"])
def status():
    return {"status": "healthy", "bot": "Keddy ready to chat!"}, 200

@app.route("/", methods=["GET"])
def index():
    return "Keddy bot is running!"

if __name__ == "__main__":
    # Run the Flask development server
    # In production, use a WSGI server like gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)