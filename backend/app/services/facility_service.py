import math
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from app.extensions import db
from app.models.health_facility import HealthFacility

FACILITY_TYPE_LABELS = {
    "PUSKESMAS": "Puskesmas",
    "CLINIC": "Klinik",
    "HOSPITAL": "Rumah Sakit",
    "DENTAL_CLINIC": "Klinik Gigi",
    "OTHER": "Lainnya",
}



SERVICE_FACILITY_TYPES = {
    "GENERAL": ("PUSKESMAS", "CLINIC"),
    "DENTAL": ("DENTAL_CLINIC", "CLINIC"),
    "MATERNAL": ("PUSKESMAS", "CLINIC", "HOSPITAL"),
    "SPECIALIST": ("HOSPITAL",),
    "OTHER": tuple(FACILITY_TYPE_LABELS.keys()),
}

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance in kilometers between two geographic coordinates
    using the Haversine formula. Consistent with frontend implementation.
    """
    R = 6371.0  # Earth's radius in kilometers
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 1)


def format_facility_dict(facility: HealthFacility, distance_km: Optional[float] = None) -> Dict[str, Any]:
    """
    Format a HealthFacility model into a safe, clean dictionary for API responses.
    Does not expose sensitive internal attributes.
    """
    data = {
        "id": facility.id,
        "name": facility.name,
        "facility_code": facility.facility_code,
        "facility_type": facility.facility_type,
        "facility_type_label": FACILITY_TYPE_LABELS.get(facility.facility_type, facility.facility_type),
        "address": facility.address or "",
        "city": facility.city or "",
        "phone": facility.phone or "-",
        "latitude": float(facility.latitude) if facility.latitude is not None else None,
        "longitude": float(facility.longitude) if facility.longitude is not None else None,
    }
    if distance_km is not None:
        data["distance_km"] = distance_km
    return data


def find_nearest_facilities(
    latitude: float,
    longitude: float,
    facility_type: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find nearest active facilities with valid coordinates, ordered ascending by Haversine distance.
    Filters by facility_type if specified and valid.
    """
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (ValueError, TypeError):
        return []

    # Base query: strictly active facilities with non-null coordinates
    stmt = select(HealthFacility).filter(
        HealthFacility.is_active.is_(True),
        HealthFacility.latitude.isnot(None),
        HealthFacility.longitude.isnot(None),
    )

    if facility_type:
        norm_type = facility_type.upper().strip()
        if norm_type in FACILITY_TYPE_LABELS:
            stmt = stmt.filter(HealthFacility.facility_type == norm_type)

    facilities = db.session.execute(stmt).scalars().all()

    # Calculate Haversine distance for each active facility
    ranked = []
    for f in facilities:
        f_lat = float(f.latitude)
        f_lon = float(f.longitude)
        dist = haversine_distance(lat, lon, f_lat, f_lon)
        item = format_facility_dict(f, distance_km=dist)
        ranked.append(item)

    # Sort ascending by distance
    ranked.sort(key=lambda x: x["distance_km"])
    return ranked[:limit]


def search_facilities(
    query: Optional[str] = None,
    facility_type: Optional[str] = None,
    city: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search active facilities by text query, facility type, or city.
    """
    stmt = select(HealthFacility).filter(HealthFacility.is_active.is_(True))

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.filter(
            or_(
                HealthFacility.name.ilike(pattern),
                HealthFacility.facility_code.ilike(pattern),
                HealthFacility.city.ilike(pattern),
                HealthFacility.address.ilike(pattern),
            )
        )

    if facility_type:
        norm_type = facility_type.upper().strip()
        if norm_type in FACILITY_TYPE_LABELS:
            stmt = stmt.filter(HealthFacility.facility_type == norm_type)

    if city:
        stmt = stmt.filter(HealthFacility.city.ilike(f"%{city.strip()}%"))

    stmt = stmt.order_by(HealthFacility.name.asc()).limit(limit)
    facilities = db.session.execute(stmt).scalars().all()

    return [format_facility_dict(f) for f in facilities]



def recommend_facilities_for_service(
    service_type: str,
    city: Optional[str] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Mengambil fasilitas aktif yang cocok dari database."""
    normalized = (service_type or "").upper().strip()
    compatible_types = SERVICE_FACILITY_TYPES.get(normalized)

    if not compatible_types:
        return []

    stmt = select(HealthFacility).filter(
        HealthFacility.is_active.is_(True),
        HealthFacility.facility_type.in_(compatible_types),
    )

    if city:
        stmt = stmt.filter(
            HealthFacility.city.ilike(f"%{city.strip()}%")
        )

    facilities = db.session.execute(
        stmt.order_by(HealthFacility.name.asc()).limit(limit)
    ).scalars().all()

    return [
        format_facility_dict(facility)
        for facility in facilities
    ]

def get_facility_by_id(facility_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a single active facility by ID.
    """
    facility = db.session.execute(
        select(HealthFacility).filter_by(id=facility_id, is_active=True)
    ).scalar_one_or_none()

    if not facility:
        return None
    return format_facility_dict(facility)
