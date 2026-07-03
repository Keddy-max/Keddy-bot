"""Legal and compliance page routes for Meta platform approval."""

from flask import Blueprint, render_template

legal_bp = Blueprint("legal", __name__)


@legal_bp.route("/privacy", methods=["GET"])
def privacy_policy():
    """Serve the privacy policy page (required for Meta/WhatsApp approval)."""
    return render_template("privacy.html")


@legal_bp.route("/terms", methods=["GET"])
def terms_of_service():
    """Serve the terms of service page."""
    return render_template("terms.html")
