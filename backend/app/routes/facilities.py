from flask import Blueprint, render_template, request, abort
from sqlalchemy import select, or_
from app.extensions import db
from app.models.health_facility import HealthFacility

facilities_bp = Blueprint("facilities", __name__, url_prefix="/facilities")

FACILITY_TYPE_LABELS = {
    "PUSKESMAS": "Puskesmas",
    "CLINIC": "Klinik",
    "HOSPITAL": "Rumah Sakit",
    "DENTAL_CLINIC": "Klinik Gigi",
    "OTHER": "Lainnya",
}


@facilities_bp.route("")
def list_facilities():
    search_query = request.args.get("search", "").strip()
    selected_type = request.args.get("facility_type", "").strip()
    selected_city = request.args.get("city", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    # Base query: only active facilities for public view
    query = select(HealthFacility).filter(HealthFacility.is_active.is_(True))

    # Search filter
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                HealthFacility.name.ilike(search_pattern),
                HealthFacility.facility_code.ilike(search_pattern),
                HealthFacility.city.ilike(search_pattern),
                HealthFacility.address.ilike(search_pattern),
            )
        )

    # Type filter (validate against whitelist, ignore invalid)
    if selected_type in FACILITY_TYPE_LABELS:
        query = query.filter(HealthFacility.facility_type == selected_type)

    # City filter
    if selected_city:
        query = query.filter(HealthFacility.city == selected_city)

    # Order
    query = query.order_by(HealthFacility.name.asc())

    # Pagination with Flask-SQLAlchemy 3.x
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    facilities = pagination.items

    # List of distinct cities for filter dropdown
    distinct_cities = db.session.execute(
        select(HealthFacility.city)
        .filter(HealthFacility.is_active.is_(True), HealthFacility.city.isnot(None), HealthFacility.city != "")
        .distinct()
        .order_by(HealthFacility.city.asc())
    ).scalars().all()

    # Map markers data
    map_facilities = []
    for f in facilities:
        if f.latitude is not None and f.longitude is not None:
            map_facilities.append({
                "id": f.id,
                "name": f.name,
                "code": f.facility_code,
                "type": f.facility_type,
                "type_label": FACILITY_TYPE_LABELS.get(f.facility_type, f.facility_type),
                "address": f.address or "",
                "city": f.city or "",
                "phone": f.phone or "-",
                "lat": float(f.latitude),
                "lng": float(f.longitude),
            })

    return render_template(
        "public/facilities/list.html",
        facilities=facilities,
        pagination=pagination,
        search_query=search_query,
        selected_type=selected_type,
        selected_city=selected_city,
        facility_types=FACILITY_TYPE_LABELS,
        cities=distinct_cities,
        map_facilities=map_facilities,
    )


@facilities_bp.route("/<int:facility_id>")
def detail_facility(facility_id):
    facility = db.session.execute(
        select(HealthFacility).filter_by(id=facility_id, is_active=True)
    ).scalar_one_or_none()

    if not facility:
        abort(404)

    map_facility = None
    if facility.latitude is not None and facility.longitude is not None:
        map_facility = {
            "id": facility.id,
            "name": facility.name,
            "code": facility.facility_code,
            "type_label": FACILITY_TYPE_LABELS.get(facility.facility_type, facility.facility_type),
            "address": facility.address or "",
            "city": facility.city or "",
            "phone": facility.phone or "-",
            "lat": float(facility.latitude),
            "lng": float(facility.longitude),
        }

    return render_template(
        "public/facilities/detail.html",
        facility=facility,
        type_label=FACILITY_TYPE_LABELS.get(facility.facility_type, facility.facility_type),
        map_facility=map_facility,
    )
