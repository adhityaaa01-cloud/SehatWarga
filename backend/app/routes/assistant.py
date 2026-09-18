import logging
from flask import Blueprint, render_template, request, jsonify
from app.services.assistant_service import process_assistant_chat, process_location_recommendation

logger = logging.getLogger(__name__)

assistant_bp = Blueprint("assistant", __name__, url_prefix="/assistant")


@assistant_bp.route("", methods=["GET"])
def chat_page():
    """
    Render the dedicated Asisten SehatWarga chat interface.
    Available to both public and authenticated citizens.
    """
    return render_template("assistant/chat.html")


@assistant_bp.route("/chat", methods=["POST"])
def chat_api():
    """
    API endpoint for conversation with Asisten SehatWarga.
    Accepts JSON: { message: str, user_location?: { latitude, longitude }, conversation_history?: list }
    Returns JSON response with intent, answer, and optional facility recommendations.
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body harus berupa JSON.",
            "message": "Permintaan tidak valid.",
        }), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Body JSON harus berupa objek."}), 400
    message = data.get("message", "")
    user_location = data.get("user_location")
    conversation_history = data.get("conversation_history")

    result, status = process_assistant_chat(
        message=message,
        user_location=user_location,
        conversation_history=conversation_history,
    )
    return jsonify(result), status


@assistant_bp.route("/location", methods=["POST"])
def location_api():
    """
    Dedicated endpoint to fetch nearest facilities after browser geolocation consent.
    Accepts JSON: { latitude: float, longitude: float, facility_type?: str }
    Returns JSON with recommended facilities and natural response message.
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body harus berupa JSON.",
            "message": "Permintaan tidak valid.",
        }), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "Body JSON harus berupa objek."}), 400
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    facility_type = data.get("facility_type")

    result, status = process_location_recommendation(
        latitude=latitude,
        longitude=longitude,
        facility_type=facility_type,
    )
    return jsonify(result), status
