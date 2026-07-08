"""
Main entry point for the Keddy WhatsApp AI chatbot.

Initializes Flask application, loads configuration, sets up logging,
and registers route blueprints.

Environment Variables:
    FLASK_ENV: Environment mode ('development' or 'production')
    PORT: Port to run server on (default: 5000)
    BASE_URL: Public URL for privacy/terms links (required in production)
    TWILIO_AUTH_TOKEN: Required for webhook signature validation
    GROQ_API_KEY: Required for AI responses
"""

import os
import logging
from typing import Dict, Any, Tuple
from flask import Flask
from flask_cors import CORS

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

DEFAULT_PORT: int = int(os.getenv("PORT", "5000"))
FLASK_ENV: str = os.getenv("FLASK_ENV", "production")
BASE_URL: str = os.getenv("BASE_URL", "https://keddy-bot.onrender.com").rstrip("/")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

app: Flask = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

app.config.update(
    DEBUG=False,
    ENV="production",
    TRAP_HTTP_EXCEPTIONS=True,
    JSON_SORT_KEYS=False,
)

logger.info(f"Initializing Keddy bot in {FLASK_ENV} mode")

# Enable CORS for the REST API (web widget calls POST /chat)
CORS(app)


try:
    from routes.whatsapp import whatsapp_bp, whatsapp_webhook
    from routes.chat_api import chat_bp

    from routes.legal import legal_bp

    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(chat_bp)

    app.register_blueprint(legal_bp)
    limiter.limit("30 per minute")(whatsapp_webhook)
    logger.info("Routes registered successfully")
except ImportError as error:
    logger.error(f"Failed to import routes: {error}")
    raise


@app.route("/status", methods=["GET"])
def status() -> Tuple[Dict[str, Any], int]:
    """Health check endpoint."""
    return (
        {
            "status": "healthy",
            "bot": "Keddy",
            "version": "2.0.0",
            "service": "WhatsApp AI Assistant",
        },
        200,
    )


@app.route("/", methods=["GET"])
def index() -> Tuple[Dict[str, Any], int]:
    """Root endpoint with service info and compliance links."""
    return (
        {
            "message": "Keddy WhatsApp AI Assistant is running",
            "service": "WhatsApp AI Assistant",
            "creator": "Prince Ked Agbemenu",
            "privacy_policy": f"{BASE_URL}/privacy",
            "terms_of_service": f"{BASE_URL}/terms",
            "webhook": f"{BASE_URL}/whatsapp",
        },
        200,
    )


@app.errorhandler(404)
def not_found(error: Exception) -> Tuple[Dict[str, str], int]:
    """Handle 404 errors."""
    logger.warning(f"404 error: {error}")
    return ({"error": "Endpoint not found"}, 404)


@app.errorhandler(500)
def internal_error(error: Exception) -> Tuple[Dict[str, str], int]:
    """Handle 500 errors."""
    logger.error(f"500 error: {error}", exc_info=True)
    return ({"error": "Internal server error"}, 500)


if __name__ == "__main__":
    logger.info(f"Starting server on port {DEFAULT_PORT}")
    app.run(
        host="0.0.0.0",
        port=DEFAULT_PORT,
        debug=False,
        use_reloader=False,
    )
