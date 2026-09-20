import logging
import os

from typing import Dict, Any, Optional, List, Tuple
from groq import Groq

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


# ============================================================
# GROQ FALLBACK
# ============================================================

def generate_groq_response(
    message: str,
    intent: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Provider AI cadangan.

    Digunakan ketika Gemini / provider utama gagal, timeout,
    terkena rate limit, atau quota habis.
    """

    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv(
        "GROQ_MODEL",
        "openai/gpt-oss-20b",
    )

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY belum tersedia di environment."
        )

    client = Groq(
        api_key=api_key,
    )

    messages = [
        {
            "role": "system",
            "content": (
                "Kamu adalah asisten virtual SehatWarga. "
                "Jawab menggunakan Bahasa Indonesia yang jelas, "
                "ramah, natural, dan mudah dipahami. "
                ""
                "Kamu membantu pengguna memahami informasi kesehatan "
                "umum dan layanan SehatWarga. "
                ""
                "Untuk pertanyaan kesehatan, berikan informasi umum "
                "dan edukatif, tetapi jangan mengaku memberikan "
                "diagnosis medis pasti. "
                ""
                "Jika pengguna menyebut kondisi yang tampak darurat "
                "atau berbahaya, sarankan pengguna segera mencari "
                "pertolongan medis atau fasilitas kesehatan terdekat. "
                ""
                "Jangan mengarang nama fasilitas kesehatan, alamat, "
                "lokasi, data kepesertaan, status layanan, ataupun "
                "data pribadi pengguna. Data tersebut ditangani "
                "langsung oleh backend dan database SehatWarga. "
                ""
                "Jangan mengatakan bahwa kamu menggunakan Groq, "
                "Gemini, model tertentu, atau provider AI tertentu "
                "kecuali pengguna secara khusus menanyakannya."
            ),
        }
    ]

    # Ambil riwayat percakapan jika tersedia.
    history = []

    if context:
        history = context.get(
            "conversation_history",
            [],
        )[-10:]

    for item in history:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if (
            role in {"user", "assistant"}
            and isinstance(content, str)
            and content.strip()
        ):
            messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

    # Tambahkan pertanyaan terbaru.
    messages.append(
        {
            "role": "user",
            "content": message,
        }
    )

    response = client.chat.completions.create(
        model=model,
        messages=messages,
    )

    if not response.choices:
        raise RuntimeError(
            "Groq tidak menghasilkan pilihan respons."
        )

    result = response.choices[0].message.content

    if not result or not result.strip():
        raise RuntimeError(
            "Groq menghasilkan respons kosong."
        )

    return result.strip()


def generate_ai_response_with_fallback(
    ai_provider,
    message: str,
    intent: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Urutan provider:

    1. Gemini / provider utama.
    2. Groq.
    3. Fallback lokal SehatWarga.

    Untuk intent yang memang menggunakan FallbackAIProvider,
    request tidak dikirim ke API eksternal.
    """

    # ========================================================
    # INTENT LOKAL
    # ========================================================

    if isinstance(
        ai_provider,
        FallbackAIProvider,
    ):
        return ai_provider.generate_response(
            message,
            intent,
        )

    # ========================================================
    # 1. PROVIDER UTAMA / GEMINI
    # ========================================================

    if ai_provider is not None:
        try:
            response = ai_provider.generate_response(
                message=message,
                intent=intent,
                context=context,
            )

            if response and response.strip():
                logger.info(
                    "AI response generated using primary provider."
                )

                return response.strip()

            logger.warning(
                "Primary AI provider menghasilkan respons kosong."
            )

        except Exception as exc:
            logger.warning(
                "Primary AI provider gagal. "
                "Mencoba Groq fallback. Error: %s",
                exc,
            )

    else:
        logger.warning(
            "Primary AI provider tidak tersedia. "
            "Mencoba Groq fallback."
        )

    # ========================================================
    # 2. GROQ
    # ========================================================

    try:
        response = generate_groq_response(
            message=message,
            intent=intent,
            context=context,
        )

        logger.info(
            "AI response generated using Groq fallback."
        )

        return response

    except Exception as exc:
        logger.warning(
            "Groq fallback gagal. "
            "Menggunakan fallback lokal. Error: %s",
            exc,
        )

    # ========================================================
    # 3. FALLBACK LOKAL
    # ========================================================

    return FallbackAIProvider().generate_response(
        message,
        intent,
    )


# ============================================================
# VALIDASI PESAN
# ============================================================

def validate_user_message(
    message: Any,
) -> Tuple[bool, str]:
    """
    Validate user chat input.

    Rejects:
    - non-string
    - empty
    - whitespace-only
    - lebih dari 2000 karakter
    """

    if not isinstance(message, str):
        return False, "Format pesan tidak valid."

    stripped = message.strip()

    if not stripped:
        return False, "Pesan tidak boleh kosong."

    if len(stripped) > 2000:
        return (
            False,
            "Pesan terlalu panjang (maksimal 2000 karakter).",
        )

    return True, stripped


# ============================================================
# CHAT ASSISTANT
# ============================================================

def process_assistant_chat(
    message: str,
    user_location: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[
        List[Dict[str, str]]
    ] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Core orchestrator untuk chat SehatWarga.

    Returns:
        (response_dict, http_status_code)
    """

    # ========================================================
    # VALIDASI MESSAGE
    # ========================================================

    is_valid, validated_msg = validate_user_message(
        message
    )

    if not is_valid:
        return {
            "success": False,
            "error": validated_msg,
            "message": validated_msg,
        }, 400

    # ========================================================
    # VALIDASI RIWAYAT CHAT
    # ========================================================

    if conversation_history is not None and (
        not isinstance(
            conversation_history,
            list,
        )
        or len(conversation_history) > 10
        or any(
            not isinstance(item, dict)
            or set(item)
            - {
                "role",
                "content",
            }
            or item.get("role")
            not in {
                "user",
                "assistant",
            }
            or not isinstance(
                item.get("content"),
                str,
            )
            or len(
                item["content"]
            )
            > 2000
            for item in conversation_history
        )
    ):
        return {
            "success": False,
            "message": (
                "Riwayat percakapan tidak valid."
            ),
        }, 400

    # ========================================================
    # VALIDASI LOKASI
    # ========================================================

    if user_location is not None:
        import math

        try:
            if (
                not isinstance(
                    user_location,
                    dict,
                )
                or any(
                    type(
                        user_location.get(k)
                    )
                    not in (
                        int,
                        float,
                    )
                    for k in (
                        "latitude",
                        "longitude",
                    )
                )
            ):
                raise ValueError()

            lat = user_location[
                "latitude"
            ]

            lon = user_location[
                "longitude"
            ]

            if not (
                math.isfinite(lat)
                and math.isfinite(lon)
                and -90 <= lat <= 90
                and -180 <= lon <= 180
            ):
                raise ValueError()

        except (
            ValueError,
            TypeError,
        ):
            return {
                "success": False,
                "message": (
                    "Koordinat tidak valid."
                ),
            }, 400

    # ========================================================
    # SAFETY + LOCAL INTENT
    # ========================================================

    # Safety lokal selalu dijalankan terlebih dahulu.
    safety = deterministic_safety(
        validated_msg
    )

    local_provider = (
        FallbackAIProvider()
    )

    local_intent = (
        local_provider.classify_intent(
            validated_msg
        )
    )

    local_required_intents = {
        "MEMBERSHIP_SUMMARY",
        "FACILITY_NEARBY",
        "FACILITY_SEARCH",
    }

    # ========================================================
    # PILIH PROVIDER
    # ========================================================

    if safety:
        intent = safety
        ai_provider = local_provider

    elif (
        local_intent
        in local_required_intents
    ):
        intent = local_intent
        ai_provider = local_provider

    elif (
        local_intent
        == "SERVICE_RECOMMENDATION"
    ):
        # Gemini membantu klasifikasi kebutuhan layanan.
        #
        # Kalau Gemini gagal / quota / timeout,
        # klasifikasi lokal tetap digunakan agar
        # fitur tidak mati.

        try:
            ai_provider = (
                get_ai_provider()
            )

            intent = (
                ai_provider.classify_intent(
                    validated_msg
                )
            )

        except Exception as exc:
            logger.warning(
                "Primary AI classification "
                "gagal. Menggunakan "
                "klasifikasi lokal. Error: %s",
                exc,
            )

            intent = local_intent
            ai_provider = local_provider

    else:
        # Pertanyaan umum.
        #
        # Jawaban akan dicoba dengan:
        #
        # Gemini
        # ↓ gagal
        # Groq
        # ↓ gagal
        # fallback lokal

        intent = local_intent

        try:
            ai_provider = (
                get_ai_provider()
            )

        except Exception as exc:
            logger.warning(
                "Gagal membuat primary "
                "AI provider. Groq akan "
                "digunakan sebagai fallback. "
                "Error: %s",
                exc,
            )

            ai_provider = None

    # ========================================================
    # EXTRACT FILTER
    # ========================================================

    facility_type = (
        extract_facility_filter(
            validated_msg
        )
    )

    city = extract_city_filter(
        validated_msg
    )

    service_type = (
        extract_service_type(
            validated_msg
        )
    )

    classification = getattr(
        ai_provider,
        "classification",
        None,
    )

    if classification:
        facility_type = (
            classification.get(
                "facility_type"
            )
            or facility_type
        )

        city = (
            classification.get(
                "city"
            )
            or city
        )

        service_type = (
            classification.get(
                "service_type"
            )
            or service_type
        )

    # ========================================================
    # MEMBERSHIP SUMMARY
    # ========================================================

    if intent == "MEMBERSHIP_SUMMARY":

        if not current_user.is_authenticated:
            return {
                "success": False,
                "intent": intent,
                "message": (
                    "Silakan masuk sebagai warga "
                    "untuk melihat ringkasan "
                    "kepesertaan Anda."
                ),
            }, 401

        if (
            not current_user.is_active
            or current_user.role
            != "citizen"
        ):
            return {
                "success": False,
                "intent": intent,
                "message": (
                    "Ringkasan hanya tersedia "
                    "untuk akun warga aktif."
                ),
            }, 403

        participant = (
            current_user.participant
        )

        if not participant:
            return {
                "success": False,
                "intent": intent,
                "message": (
                    "Data kepesertaan "
                    "belum tersedia."
                ),
            }, 404

        return {
            "success": True,
            "intent": intent,
            "message": (
                f"Status kepesertaan Anda: "
                f"{participant.membership_status}. "
                f"Kelas layanan: "
                f"{participant.service_class}. "
                "Lihat rincian tagihan dan "
                "pengajuan pada dashboard Anda."
            ),
            "requires_location": False,
            "facilities": [],
        }, 200

    # ========================================================
    # HEALTH NAVIGATOR
    # ========================================================

    if intent == "SERVICE_RECOMMENDATION":

        if (
            service_type
            not in VALID_SERVICE_TYPES
        ):
            return {
                "success": True,
                "intent": intent,
                "message": (
                    "Sebutkan kebutuhan secara umum, "
                    "misalnya pemeriksaan umum, "
                    "layanan gigi, layanan ibu dan anak, "
                    "atau layanan spesialis."
                ),
                "requires_location": False,
                "service_recommendation": None,
                "facilities": [],
            }, 200

        facilities = (
            recommend_facilities_for_service(
                service_type=service_type,
                city=city,
                limit=5,
            )
        )

        is_citizen = (
            current_user.is_authenticated
            and current_user.is_active
            and current_user.role
            == "citizen"
        )

        for facility in facilities:

            if is_citizen:
                facility[
                    "action_url"
                ] = url_for(
                    "citizen.service_request_create",
                    health_facility_id=(
                        facility["id"]
                    ),
                    service_type=service_type,
                )

        label = VALID_SERVICE_TYPES[
            service_type
        ]

        area = (
            f" di {city}"
            if city
            else ""
        )

        if facilities:
            message_text = (
                f"Kebutuhan Anda cocok "
                f"dengan kategori {label}. "
                f"Saya menemukan "
                f"{len(facilities)} "
                f"fasilitas aktif{area} "
                "dari database SehatWarga."
            )

        else:
            message_text = (
                f"Kebutuhan Anda cocok "
                f"dengan kategori {label}, "
                "tetapi belum ada "
                f"fasilitas aktif{area} "
                "yang sesuai di database."
            )

        return {
            "success": True,
            "intent": intent,
            "message": message_text,
            "requires_location": False,
            "service_type": service_type,
            "service_recommendation": {
                "service_type": (
                    service_type
                ),
                "label": label,
                "basis": (
                    "Klasifikasi kebutuhan "
                    "dan data fasilitas "
                    "terverifikasi"
                ),
                "disclaimer": (
                    "Rekomendasi administratif, "
                    "bukan diagnosis medis."
                ),
            },
            "facilities": facilities,
        }, 200

    # ========================================================
    # 1. FACILITY NEARBY
    # ========================================================

    if intent == "FACILITY_NEARBY":

        valid_coords = False

        lat = None
        lon = None

        if (
            user_location
            and isinstance(
                user_location,
                dict,
            )
        ):
            try:
                lat = float(
                    user_location.get(
                        "latitude"
                    )
                )

                lon = float(
                    user_location.get(
                        "longitude"
                    )
                )

                if (
                    -90.0
                    <= lat
                    <= 90.0
                    and -180.0
                    <= lon
                    <= 180.0
                ):
                    valid_coords = True

            except (
                ValueError,
                TypeError,
            ):
                valid_coords = False

        # ====================================================
        # LOCATION BELUM TERSEDIA
        # ====================================================

        if not valid_coords:

            type_label = (
                f" ({facility_type})"
                if facility_type
                else ""
            )

            return {
                "success": True,
                "message": (
                    "Untuk mencari fasilitas "
                    f"kesehatan{type_label} "
                    "terdekat, izinkan akses "
                    "lokasi Anda melalui tombol "
                    "di bawah."
                ),
                "intent": (
                    "FACILITY_NEARBY"
                ),
                "requires_location": True,
                "facility_type": (
                    facility_type
                ),
                "user_location": None,
                "facilities": [],
            }, 200

        # ====================================================
        # CARI FASILITAS TERDEKAT
        # ====================================================

        facilities = (
            find_nearest_facilities(
                latitude=lat,
                longitude=lon,
                facility_type=(
                    facility_type
                ),
                limit=5,
            )
        )

        if not facilities:
            return {
                "success": True,
                "message": (
                    "Maaf, tidak ditemukan "
                    "fasilitas kesehatan aktif "
                    "di sekitar lokasi Anda."
                ),
                "intent": (
                    "FACILITY_NEARBY"
                ),
                "requires_location": False,
                "facility_type": (
                    facility_type
                ),
                "user_location": {
                    "latitude": lat,
                    "longitude": lon,
                },
                "facilities": [],
            }, 200

        nearest = facilities[0]

        has_coords = any(
            f.get("latitude")
            is not None
            and f.get("longitude")
            is not None
            for f in facilities
        )

        map_note = (
            "Saya juga menampilkan "
            "lokasinya pada peta di bawah."
            if has_coords
            else (
                "Data lokasi peta untuk "
                "fasilitas ini belum tersedia."
            )
        )

        bot_message = (
            "Saya menemukan beberapa "
            "fasilitas kesehatan terdekat "
            "dari lokasi Anda.\n\n"
            f"Yang paling dekat adalah "
            f"{nearest['name']} "
            "dengan perkiraan jarak "
            f"{nearest['distance_km']} km "
            "(perkiraan garis lurus).\n\n"
            "Koordinat:\n"
            f"{nearest['latitude']}, "
            f"{nearest['longitude']}\n\n"
            f"{map_note}"
        )

        return {
            "success": True,
            "message": bot_message,
            "intent": (
                "FACILITY_NEARBY"
            ),
            "requires_location": False,
            "facility_type": (
                facility_type
            ),
            "user_location": {
                "latitude": lat,
                "longitude": lon,
            },
            "facilities": facilities,
        }, 200

    # ========================================================
    # 2. FACILITY SEARCH
    # ========================================================

    if intent == "FACILITY_SEARCH":

        facilities = (
            search_facilities(
                query=validated_msg,
                facility_type=(
                    facility_type
                ),
                city=city,
                limit=5,
            )
        )

        # Jika pencarian teks terlalu spesifik,
        # coba berdasarkan filter tipe/kota.

        if not facilities:

            if facility_type or city:

                facilities = (
                    search_facilities(
                        query=None,
                        facility_type=(
                            facility_type
                        ),
                        city=city,
                        limit=5,
                    )
                )

        if not facilities:
            return {
                "success": True,
                "message": (
                    "Tidak ditemukan fasilitas "
                    "kesehatan yang cocok dengan "
                    "kriteria pencarian Anda."
                ),
                "intent": (
                    "FACILITY_SEARCH"
                ),
                "requires_location": False,
                "facility_type": (
                    facility_type
                ),
                "user_location": None,
                "facilities": [],
            }, 200

        names = [
            (
                f"- {f['name']} "
                f"({f['facility_type_label']}) "
                f"- {f['city']}"
            )
            for f in facilities
        ]

        bot_message = (
            "Berikut fasilitas kesehatan "
            "yang ditemukan:\n"
            + "\n".join(names)
            + (
                "\n\nAnda dapat melihat "
                "informasi lengkap pada "
                "kartu rincian di bawah."
            )
        )

        return {
            "success": True,
            "message": bot_message,
            "intent": (
                "FACILITY_SEARCH"
            ),
            "requires_location": False,
            "facility_type": (
                facility_type
            ),
            "user_location": None,
            "facilities": facilities,
        }, 200

    # ========================================================
    # 3. INFORMASI UMUM / HEALTH GUIDE
    #
    # Gemini
    #    ↓ gagal
    # Groq
    #    ↓ gagal
    # Local fallback
    # ========================================================

    response_text = (
        generate_ai_response_with_fallback(
            ai_provider=ai_provider,
            message=validated_msg,
            intent=intent,
            context={
                "conversation_history": (
                    conversation_history
                    or []
                )[-10:]
            },
        )
    )

    return {
        "success": True,
        "message": response_text,
        "intent": intent,
        "requires_location": False,
        "facility_type": (
            facility_type
        ),
        "user_location": None,
        "facilities": [],
    }, 200


# ============================================================
# LOCATION RECOMMENDATION
# ============================================================

def process_location_recommendation(
    latitude: Any,
    longitude: Any,
    facility_type: Optional[str] = None,
) -> Tuple[Dict[str, Any], int]:
    """
    Dedicated handler untuk query lokasi.

    Contoh:
        POST /assistant/location

    Menghitung fasilitas terdekat tanpa
    menyimpan koordinat pengguna.
    """

    # ========================================================
    # VALIDASI KOORDINAT
    # ========================================================

    try:
        if (
            isinstance(
                latitude,
                bool,
            )
            or isinstance(
                longitude,
                bool,
            )
        ):
            raise ValueError()

        lat = float(latitude)
        lon = float(longitude)

        if not (
            -90.0
            <= lat
            <= 90.0
            and -180.0
            <= lon
            <= 180.0
        ):
            return {
                "success": False,
                "error": (
                    "Koordinat latitude atau "
                    "longitude di luar "
                    "rentang valid."
                ),
                "message": (
                    "Koordinat tidak valid."
                ),
            }, 400

    except (
        ValueError,
        TypeError,
    ):
        return {
            "success": False,
            "error": (
                "Koordinat latitude dan "
                "longitude harus berupa angka."
            ),
            "message": (
                "Format koordinat salah."
            ),
        }, 400

    # ========================================================
    # VALIDASI FACILITY TYPE
    # ========================================================

    if facility_type is not None and (
        not isinstance(
            facility_type,
            str,
        )
        or facility_type
        not in {
            "HOSPITAL",
            "PUSKESMAS",
            "CLINIC",
            "DENTAL_CLINIC",
            "OTHER",
        }
    ):
        return {
            "success": False,
            "message": (
                "Jenis fasilitas tidak valid."
            ),
        }, 400

    # ========================================================
    # CARI FASILITAS
    # ========================================================

    facilities = (
        find_nearest_facilities(
            latitude=lat,
            longitude=lon,
            facility_type=(
                facility_type
            ),
            limit=5,
        )
    )

    if not facilities:
        return {
            "success": True,
            "message": (
                "Maaf, tidak ditemukan "
                "fasilitas kesehatan aktif "
                "di sekitar lokasi Anda."
            ),
            "intent": (
                "FACILITY_NEARBY"
            ),
            "requires_location": False,
            "facility_type": (
                facility_type
            ),
            "user_location": {
                "latitude": lat,
                "longitude": lon,
            },
            "facilities": [],
        }, 200

    nearest = facilities[0]

    has_coords = any(
        f.get("latitude")
        is not None
        and f.get("longitude")
        is not None
        for f in facilities
    )

    map_note = (
        "Saya juga menampilkan "
        "lokasinya pada peta di bawah."
        if has_coords
        else (
            "Data lokasi peta untuk "
            "fasilitas ini belum tersedia."
        )
    )

    bot_message = (
        "Saya menemukan beberapa "
        "fasilitas kesehatan terdekat "
        "dari lokasi Anda.\n\n"
        f"Yang paling dekat adalah "
        f"{nearest['name']} "
        "dengan perkiraan jarak "
        f"{nearest['distance_km']} km "
        "(perkiraan garis lurus).\n\n"
        "Koordinat:\n"
        f"{nearest['latitude']}, "
        f"{nearest['longitude']}\n\n"
        f"{map_note}"
    )

    return {
        "success": True,
        "message": bot_message,
        "intent": (
            "FACILITY_NEARBY"
        ),
        "requires_location": False,
        "facility_type": (
            facility_type
        ),
        "user_location": {
            "latitude": lat,
            "longitude": lon,
        },
        "facilities": facilities,
    }, 200