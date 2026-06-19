"""
Main entry point for the Keddy WhatsApp AI chatbot.

Initializes Flask application, loads configuration, sets up logging,
and registers route blueprints.

Environment Variables:
    FLASK_ENV: Environment mode ('development' or 'production')
    FLASK_DEBUG: Enable debug mode (should be False in production)
    PORT: Port to run server on (default: 5000)
"""

import os
import logging
from typing import Dict, Any, Tuple
from flask import Flask, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration constants
DEFAULT_PORT: int = int(os.getenv("PORT", "5000"))
FLASK_ENV: str = os.getenv("FLASK_ENV", "production")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger: logging.Logger = logging.getLogger(__name__)

# Create Flask app
app: Flask = Flask(__name__)

# Security configuration
app.config.update(
    DEBUG=False,  # Never enable debug in production
    ENV="production",
    TRAP_HTTP_EXCEPTIONS=True,
    JSON_SORT_KEYS=False,
)

logger.info(f"Initializing Keddy bot in {FLASK_ENV} mode")

# Import routes after app creation to avoid circular imports
try:
    from routes.whatsapp import whatsapp_bp
    app.register_blueprint(whatsapp_bp)
    logger.info("WhatsApp routes registered successfully")
except ImportError as error:
    logger.error(f"Failed to import routes: {error}")
    raise


@app.route("/status", methods=["GET"])
def status() -> Tuple[Dict[str, str], int]:
    """
    Health check endpoint.

    Returns:
        JSON response with health status and HTTP 200.
    """
    return (
        {
            "status": "healthy",
            "bot": "Keddy",
            "version": "1.0.0",
        },
        200,
    )


@app.route("/", methods=["GET"])
def index() -> Tuple[Dict[str, str], int]:
    """
    Root endpoint.

    Returns:
        JSON response with bot information and HTTP 200.
    """
    return (
        {
            "message": "Keddy bot is running",
            "service": "WhatsApp AI Assistant",
        },
        200,
    )


@app.errorhandler(404)
def not_found(error: Exception) -> Tuple[Dict[str, str], int]:
    """
    Handle 404 errors.

    Args:
        error: The exception that was raised.

    Returns:
        JSON error response and HTTP 404.
    """
    logger.warning(f"404 error: {error}")
    return ({"error": "Endpoint not found"}, 404)


@app.errorhandler(500)
def internal_error(error: Exception) -> Tuple[Dict[str, str], int]:
    """
    Handle 500 errors.

    Args:
        error: The exception that was raised.

    Returns:
        JSON error response and HTTP 500.
    """
    logger.error(f"500 error: {error}", exc_info=True)
    return ({"error": "Internal server error"}, 500)


if __name__ == "__main__":
    # Run Flask development server
    # In production, use a WSGI server like gunicorn:
    # gunicorn -w 4 -b 0.0.0.0:5000 app:app
    logger.info(f"Starting server on port {DEFAULT_PORT}")
    app.run(
        host="0.0.0.0",
        port=DEFAULT_PORT,
        debug=False,  # Security: Never enable debug in production
        use_reloader=False,
    )