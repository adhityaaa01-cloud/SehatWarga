import secrets
import string
from datetime import datetime, timezone, date
from sqlalchemy import select
from app.extensions import db
from app.models.service_request import ServiceRequest
from app.models.service_history import ServiceHistory
from app.models.health_facility import HealthFacility
from app.models.family_member import FamilyMember

VALID_SERVICE_TYPES = {
    "GENERAL": "Layanan Umum",
    "DENTAL": "Layanan Gigi",
    "MATERNAL": "Layanan Ibu dan Anak",
    "SPECIALIST": "Layanan Spesialis",
    "OTHER": "Layanan Lainnya",
}

VALID_STATUSES = {
    "SUBMITTED": "Menunggu Verifikasi",
    "VERIFIED": "Terverifikasi",
    "SCHEDULED": "Dijadwalkan",
    "COMPLETED": "Selesai",
    "CANCELLED": "Dibatalkan",
    "REJECTED": "Ditolak",
}

# Allowed status transitions matrix
ALLOWED_TRANSITIONS = {
    "SUBMITTED": ["VERIFIED", "REJECTED", "CANCELLED"],
    "VERIFIED": ["SCHEDULED", "REJECTED", "CANCELLED"],
    "SCHEDULED": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
    "REJECTED": [],
}


def generate_request_number(target_date: date = None) -> str:
    """
    Generate a cryptographically secure, unique service request number for SehatWarga.
    Format: SWR-YYYYMMDD-XXXXXXXX
    Example: SWR-20260904-K8Q2M4P7
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    date_str = target_date.strftime("%Y%m%d")
    charset = string.ascii_uppercase + string.digits

    max_attempts = 100
    for _ in range(max_attempts):
        random_suffix = "".join(secrets.choice(charset) for _ in range(8))
        candidate = f"SWR-{date_str}-{random_suffix}"

        # Collision check
        existing = db.session.execute(
            select(ServiceRequest.id).filter_by(request_number=candidate)
        ).scalar_one_or_none()

        if not existing:
            return candidate

    raise RuntimeError("Gagal menghasilkan nomor pengajuan unik setelah beberapa kali percobaan.")


def create_service_request(
    participant,
    health_facility_id: int,
    service_type: str,
    scheduled_date: date,
    complaint_summary: str,
    beneficiary_type: str,
    family_member_id: int = None,
    user_id: int = None,
) -> ServiceRequest:
    """
    Creates a new service request and initial audit history atomically.
    Validates participant status, family member ownership/status, and facility status.
    """
    # 1. Validate participant status
    if participant.membership_status != "ACTIVE":
        raise ValueError("Status kepesertaan tidak aktif.")

    # 2. Validate beneficiary
    target_family_id = None
    if beneficiary_type == "FAMILY":
        if not family_member_id:
            raise ValueError("Anggota keluarga penerima layanan wajib dipilih.")

        # Query and validate ownership & active status
        family_member = db.session.execute(
            select(FamilyMember).filter_by(id=family_member_id, participant_id=participant.id)
        ).scalar_one_or_none()

        if not family_member:
            raise ValueError("Anggota keluarga tidak ditemukan atau bukan bagian dari kepesertaan Anda.")

        if family_member.membership_status != "ACTIVE":
            raise ValueError("Status kepesertaan anggota keluarga tidak aktif.")

        target_family_id = family_member.id
    elif beneficiary_type == "SELF":
        target_family_id = None
    else:
        raise ValueError("Jenis penerima layanan tidak valid.")

    # 3. Validate health facility
    facility = db.session.execute(
        select(HealthFacility).filter_by(id=health_facility_id, is_active=True)
    ).scalar_one_or_none()
    if not facility:
        raise ValueError("Fasilitas kesehatan tidak ditemukan atau sedang tidak aktif.")

    # 4. Validate service type
    if service_type not in VALID_SERVICE_TYPES:
        raise ValueError("Jenis layanan tidak valid.")

    # 5. Validate scheduled date
    if scheduled_date is None or scheduled_date < date.today():
        raise ValueError("Tanggal layanan tidak boleh di masa lalu.")

    # 6. Validate complaint summary
    cleaned_summary = complaint_summary.strip() if complaint_summary else ""
    if cleaned_summary and len(cleaned_summary) < 5:
        raise ValueError("Keperluan layanan minimal 5 karakter.")

    # Generate request number
    req_number = generate_request_number()

    try:
        service_req = ServiceRequest(
            request_number=req_number,
            participant_id=participant.id,
            family_member_id=target_family_id,
            health_facility_id=facility.id,
            service_type=service_type,
            scheduled_date=scheduled_date,
            complaint_summary=cleaned_summary if cleaned_summary else None,
            status="SUBMITTED",
        )
        db.session.add(service_req)
        db.session.flush()  # Populates service_req.id

        # Initial history record
        history = ServiceHistory(
            service_request_id=service_req.id,
            status="SUBMITTED",
            note="Pengajuan layanan dibuat oleh peserta.",
            changed_by=user_id,
        )
        db.session.add(history)
        db.session.commit()

        return service_req
    except Exception:
        db.session.rollback()
        raise


def transition_service_request_status(
    service_request: ServiceRequest,
    target_status: str,
    user_id: int,
    note: str,
    new_scheduled_date: date = None,
) -> ServiceRequest:
    """
    Transitions the status of a ServiceRequest and logs a ServiceHistory record atomically.
    Enforces the transition state machine.
    """
    current_status = service_request.status

    # Validate transition
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise ValueError(
            f"Perubahan status dari '{current_status}' ke '{target_status}' tidak diizinkan."
        )

    # Validate rejection reason
    if target_status == "REJECTED":
        cleaned_note = note.strip() if note else ""
        if not cleaned_note or len(cleaned_note) < 5:
            raise ValueError("Alasan penolakan wajib diisi minimal 5 karakter.")
        note = cleaned_note

    # Validate schedule date if provided
    if new_scheduled_date is not None:
        if new_scheduled_date < date.today():
            raise ValueError("Jadwal layanan baru tidak boleh di masa lalu.")
        service_request.scheduled_date = new_scheduled_date

    try:
        service_request.status = target_status
        service_request.updated_at = datetime.now(timezone.utc)

        history = ServiceHistory(
            service_request_id=service_request.id,
            status=target_status,
            note=note,
            changed_by=user_id,
        )
        db.session.add(history)
        db.session.commit()

        return service_request
    except Exception:
        db.session.rollback()
        raise
