import logging
from typing import Dict, Any, Optional, List, Tuple
from app.services.facility_service import (
    find_nearest_facilities,
    recommend_facilities_for_service,
    search_facilities,
)
from app.services.ai_service import (
    get_ai_provider,
    FallbackAIProvider,
    extract_facility_filter,
    extract_city_filter,
    extract_service_type,
)
from app.services.assistant_safety import deterministic_safety
from app.services.service_request_service import VALID_SERVICE_TYPES
from flask import url_for
from flask_login import current_user

logger = logging.getLogger(__name__)


def validate_user_message(message: Any) -> Tuple[bool, str]:
    """
    Validate user chat input.
    Rejects empty, whitespace-only, or overly long inputs (> 2000 chars).
    """
    if not isinstance(message, str):
        return False, "Format pesan tidak valid."

    stripped = message.strip()
    if not stripped:
        return False, "Pesan tidak boleh kosong."

    if len(stripped) > 2000:
        return False, "Pesan terlalu panjang (maksimal 2000 karakter)."

    return True, stripped


def process_assistant_chat(
    message: str,
    user_location: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Core orchestrator for chat messages.
    Returns (response_dict, http_status_code).
    """
    is_valid, validated_msg = validate_user_message(message)
    if not is_valid:
        return {
            "success": False,
            "error": validated_msg,
            "message": validated_msg,
        }, 400

    if conversation_history is not None and (
        not isinstance(conversation_history, list) or len(conversation_history) > 10 or
        any(not isinstance(item, dict) or set(item) - {"role", "content"} or
            item.get("role") not in {"user", "assistant"} or
            not isinstance(item.get("content"), str) or len(item["content"]) > 2000
            for item in conversation_history)
    ):
        return {"success": False, "message": "Riwayat percakapan tidak valid."}, 400

    if user_location is not None:
        import math
        try:
            if not isinstance(user_location, dict) or any(type(user_location.get(k)) not in (int, float) for k in ('latitude', 'longitude')):
                raise ValueError()
            lat, lon = user_location['latitude'], user_location['longitude']
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError()
        except (ValueError, TypeError):
            return {"success": False, "message": "Koordinat tidak valid."}, 400

    # Safety lokal selalu berjalan sebelum Gemini.
    safety = deterministic_safety(validated_msg)

    local_provider = FallbackAIProvider()
    local_intent = local_provider.classify_intent(validated_msg)

    if safety:
        intent = safety
        ai_provider = local_provider
    elif local_intent == "MEMBERSHIP_SUMMARY":
        intent = local_intent
        ai_provider = local_provider
    else:
        ai_provider = get_ai_provider()
        intent = ai_provider.classify_intent(validated_msg)

    facility_type = extract_facility_filter(validated_msg)
    city = extract_city_filter(validated_msg)
    service_type = extract_service_type(validated_msg)

    classification = getattr(ai_provider, "classification", None)

    if classification:
        facility_type = (
            classification.get("facility_type")
            or facility_type
        )
        city = classification.get("city") or city
        service_type = classification.get("service_type") or service_type
    if intent == "MEMBERSHIP_SUMMARY":
        if not current_user.is_authenticated:
            return {"success": False, "intent": intent, "message": "Silakan masuk sebagai warga untuk melihat ringkasan kepesertaan Anda."}, 401
        if not current_user.is_active or current_user.role != "citizen":
            return {"success": False, "intent": intent, "message": "Ringkasan hanya tersedia untuk akun warga aktif."}, 403
        participant = current_user.participant
        if not participant:
            return {"success": False, "intent": intent, "message": "Data kepesertaan belum tersedia."}, 404
        return {"success": True, "intent": intent, "message":
            f"Status kepesertaan Anda: {participant.membership_status}. "
            f"Kelas layanan: {participant.service_class}. "
            "Lihat rincian tagihan dan pengajuan pada dashboard Anda.",
            "requires_location": False, "facilities": []}, 200

    # Health Navigator: AI memahami bahasa, backend menentukan fakta.
    if intent == "SERVICE_RECOMMENDATION":
        if service_type not in VALID_SERVICE_TYPES:
            return {
                "success": True,
                "intent": intent,
                "message": (
                    "Sebutkan kebutuhan secara umum, misalnya pemeriksaan umum, "
                    "layanan gigi, layanan ibu dan anak, atau layanan spesialis."
                ),
                "requires_location": False,
                "service_recommendation": None,
                "facilities": [],
            }, 200

        facilities = recommend_facilities_for_service(
            service_type=service_type,
            city=city,
            limit=5,
        )

        is_citizen = (
            current_user.is_authenticated
            and current_user.is_active
            and current_user.role == "citizen"
        )

        for facility in facilities:
            if is_citizen:
                facility["action_url"] = url_for(
                    "citizen.service_request_create",
                    health_facility_id=facility["id"],
                    service_type=service_type,
                )

        label = VALID_SERVICE_TYPES[service_type]
        area = f" di {city}" if city else ""

        if facilities:
            message_text = (
                f"Kebutuhan Anda cocok dengan kategori {label}. "
                f"Saya menemukan {len(facilities)} fasilitas aktif{area} "
                "dari database SehatWarga."
            )
        else:
            message_text = (
                f"Kebutuhan Anda cocok dengan kategori {label}, tetapi "
                f"belum ada fasilitas aktif{area} yang sesuai di database."
            )

        return {
            "success": True,
            "intent": intent,
            "message": message_text,
            "requires_location": False,
            "service_type": service_type,
            "service_recommendation": {
                "service_type": service_type,
                "label": label,
                "basis": "Klasifikasi kebutuhan dan data fasilitas terverifikasi",
                "disclaimer": "Rekomendasi administratif, bukan diagnosis medis.",
            },
            "facilities": facilities,
        }, 200

    # 1. Handle FACILITY_NEARBY
    if intent == "FACILITY_NEARBY":
        # Check if coordinates were provided with the request
        valid_coords = False
        lat, lon = None, None
        if user_location and isinstance(user_location, dict):
            try:
                lat = float(user_location.get("latitude"))
                lon = float(user_location.get("longitude"))
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    valid_coords = True
            except (ValueError, TypeError):
                valid_coords = False

        if not valid_coords:
            type_label = f" ({facility_type})" if facility_type else ""
            return {
                "success": True,
                "message": (
                    f"Untuk mencari fasilitas kesehatan{type_label} terdekat, "
                    "izinkan akses lokasi Anda melalui tombol di bawah."
                ),
                "intent": "FACILITY_NEARBY",
                "requires_location": True,
                "facility_type": facility_type,
                "user_location": None,
                "facilities": [],
            }, 200

        # Location is available, query nearest active facilities from database
        facilities = find_nearest_facilities(
            latitude=lat,
            longitude=lon,
            facility_type=facility_type,
            limit=5,
        )

        if not facilities:
            return {
                "success": True,
                "message": "Maaf, tidak ditemukan fasilitas kesehatan aktif di sekitar lokasi Anda.",
                "intent": "FACILITY_NEARBY",
                "requires_location": False,
                "facility_type": facility_type,
                "user_location": {"latitude": lat, "longitude": lon},
                "facilities": [],
            }, 200

        nearest = facilities[0]
        has_coords = any(f.get("latitude") is not None and f.get("longitude") is not None for f in facilities)
        
        map_note = (
            "Saya juga menampilkan lokasinya pada peta di bawah."
            if has_coords
            else "Data lokasi peta untuk fasilitas ini belum tersedia."
        )

        bot_message = (
            f"Saya menemukan beberapa fasilitas kesehatan terdekat dari lokasi Anda.\n\n"
            f"Yang paling dekat adalah {nearest['name']} dengan perkiraan jarak {nearest['distance_km']} km (perkiraan garis lurus).\n\n"
            f"Koordinat:\n{nearest['latitude']}, {nearest['longitude']}\n\n"
            f"{map_note}"
        )

        return {
            "success": True,
            "message": bot_message,
            "intent": "FACILITY_NEARBY",
            "requires_location": False,
            "facility_type": facility_type,
            "user_location": {"latitude": lat, "longitude": lon},
            "facilities": facilities,
        }, 200

    # 2. Handle FACILITY_SEARCH (text search or by city)
    if intent == "FACILITY_SEARCH":
        facilities = search_facilities(
            query=validated_msg,
            facility_type=facility_type,
            city=city,
            limit=5,
        )

        if not facilities:
            # Fallback search by type or city if raw query was too specific
            if facility_type or city:
                facilities = search_facilities(
                    query=None,
                    facility_type=facility_type,
                    city=city,
                    limit=5,
                )

        if not facilities:
            return {
                "success": True,
                "message": "Tidak ditemukan fasilitas kesehatan yang cocok dengan kriteria pencarian Anda.",
                "intent": "FACILITY_SEARCH",
                "requires_location": False,
                "facility_type": facility_type,
                "user_location": None,
                "facilities": [],
            }, 200

        names = [f"- {f['name']} ({f['facility_type_label']}) - {f['city']}" for f in facilities]
        bot_message = (
            f"Berikut fasilitas kesehatan yang ditemukan:\n"
            + "\n".join(names)
            + "\n\nAnda dapat melihat informasi lengkap pada kartu rincian di bawah."
        )

        return {
            "success": True,
            "message": bot_message,
            "intent": "FACILITY_SEARCH",
            "requires_location": False,
            "facility_type": facility_type,
            "user_location": None,
            "facilities": facilities,
        }, 200

    # 3. Handle informational guides & safety responses
    try:
        response_text = ai_provider.generate_response(
            message=validated_msg,
            intent=intent,
            context={"conversation_history": (conversation_history or [])[-10:]},
        )
    except Exception:
        response_text = FallbackAIProvider().generate_response(validated_msg, intent)

    return {
        "success": True,
        "message": response_text,
        "intent": intent,
        "requires_location": False,
        "facility_type": facility_type,
        "user_location": None,
        "facilities": [],
    }, 200


def process_location_recommendation(
    latitude: Any,
    longitude: Any,
    facility_type: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Dedicated handler for location-only queries (e.g. POST /assistant/location).
    Calculates nearest facilities without storing coordinates.
    """
    try:
        if isinstance(latitude, bool) or isinstance(longitude, bool):
            raise ValueError()
        lat = float(latitude)
        lon = float(longitude)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return {
                "success": False,
                "error": "Koordinat latitude atau longitude di luar rentang valid.",
                "message": "Koordinat tidak valid.",
            }, 400
    except (ValueError, TypeError):
        return {
            "success": False,
            "error": "Koordinat latitude dan longitude harus berupa angka.",
            "message": "Format koordinat salah.",
        }, 400

    if facility_type is not None and (not isinstance(facility_type, str) or facility_type not in {"HOSPITAL", "PUSKESMAS", "CLINIC", "DENTAL_CLINIC", "OTHER"}):
        return {"success": False, "message": "Jenis fasilitas tidak valid."}, 400
    facilities = find_nearest_facilities(
        latitude=lat,
        longitude=lon,
        facility_type=facility_type,
        limit=5,
    )

    if not facilities:
        return {
            "success": True,
            "message": "Maaf, tidak ditemukan fasilitas kesehatan aktif di sekitar lokasi Anda.",
            "intent": "FACILITY_NEARBY",
            "requires_location": False,
            "facility_type": facility_type,
            "user_location": {"latitude": lat, "longitude": lon},
            "facilities": [],
        }, 200

    nearest = facilities[0]
    has_coords = any(f.get("latitude") is not None and f.get("longitude") is not None for f in facilities)
    map_note = (
        "Saya juga menampilkan lokasinya pada peta di bawah."
        if has_coords
        else "Data lokasi peta untuk fasilitas ini belum tersedia."
    )

    bot_message = (
        f"Saya menemukan beberapa fasilitas kesehatan terdekat dari lokasi Anda.\n\n"
        f"Yang paling dekat adalah {nearest['name']} dengan perkiraan jarak {nearest['distance_km']} km (perkiraan garis lurus).\n\n"
        f"Koordinat:\n{nearest['latitude']}, {nearest['longitude']}\n\n"
        f"{map_note}"
    )

    return {
        "success": True,
        "message": bot_message,
        "intent": "FACILITY_NEARBY",
        "requires_location": False,
        "facility_type": facility_type,
        "user_location": {"latitude": lat, "longitude": lon},
        "facilities": facilities,
    }, 200
