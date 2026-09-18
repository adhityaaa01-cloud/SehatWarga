import secrets
import string
from datetime import datetime, timezone, date
from sqlalchemy import select
from app.extensions import db
from app.models.complaint import Complaint

STATUS_OPEN = "OPEN"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_RESOLVED = "RESOLVED"
STATUS_REJECTED = "REJECTED"

VALID_COMPLAINT_STATUSES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_RESOLVED, STATUS_REJECTED]

COMPLAINT_STATUS_LABELS = {
    STATUS_OPEN: "Baru",
    STATUS_IN_PROGRESS: "Sedang Diproses",
    STATUS_RESOLVED: "Selesai",
    STATUS_REJECTED: "Ditolak",
}

COMPLAINT_STATUS_BADGES = {
    STATUS_OPEN: "badge-info",
    STATUS_IN_PROGRESS: "badge-purple",
    STATUS_RESOLVED: "badge-success",
    STATUS_REJECTED: "badge-danger",
}

# Strict state machine
ALLOWED_TRANSITIONS = {
    STATUS_OPEN: {STATUS_IN_PROGRESS, STATUS_REJECTED},
    STATUS_IN_PROGRESS: {STATUS_RESOLVED, STATUS_REJECTED},
    STATUS_RESOLVED: set(),
    STATUS_REJECTED: set(),
}


def generate_ticket_number(target_date: date = None) -> str:
    """
    Generate a cryptographically secure, unique complaint ticket number for SehatWarga.
    Format: SWT-YYYYMMDD-XXXXXXXX
    Example: SWT-20260906-K8Q2M4P7
    - SWT = SehatWarga Ticket
    - YYYYMMDD = Date ticket created
    - XXXXXXXX = 8 uppercase alphanumeric random characters (secrets)
    Backend-generated, collision checked, strictly independent from User.id, email, NIK, etc.
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    date_str = target_date.strftime("%Y%m%d")
    charset = string.ascii_uppercase + string.digits

    max_attempts = 100
    for _ in range(max_attempts):
        random_suffix = "".join(secrets.choice(charset) for _ in range(8))
        candidate = f"SWT-{date_str}-{random_suffix}"

        # Collision check in complaints table
        existing = db.session.execute(
            select(Complaint.id).filter_by(ticket_number=candidate)
        ).scalar_one_or_none()

        if not existing:
            return candidate

    raise RuntimeError("Gagal menghasilkan nomor tiket unik setelah beberapa kali percobaan.")


def validate_subject(subject: str) -> str:
    """
    Validates complaint subject:
    - Required
    - Trimmed whitespace
    - 5 to 150 characters
    - Not whitespace-only
    """
    if not subject or not isinstance(subject, str):
        raise ValueError("Judul pengaduan wajib diisi.")
    cleaned = subject.strip()
    if not cleaned:
        raise ValueError("Judul pengaduan tidak boleh hanya berupa spasi.")
    if len(cleaned) < 5 or len(cleaned) > 150:
        raise ValueError("Judul pengaduan harus memiliki panjang antara 5 hingga 150 karakter.")
    return cleaned


def validate_message(message: str) -> str:
    """
    Validates complaint message:
    - Required
    - Trimmed whitespace
    - 10 to 5000 characters
    - Not whitespace-only
    """
    if not message or not isinstance(message, str):
        raise ValueError("Isi pengaduan wajib diisi.")
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("Isi pengaduan tidak boleh hanya berupa spasi.")
    if len(cleaned) < 10 or len(cleaned) > 5000:
        raise ValueError("Isi pengaduan harus memiliki panjang antara 10 hingga 5000 karakter.")
    return cleaned


def validate_admin_response(response: str) -> str:
    """
    Validates admin response / rejection reason:
    - Required
    - Trimmed whitespace
    - 10 to 5000 characters
    - Not whitespace-only
    """
    if not response or not isinstance(response, str):
        raise ValueError("Tanggapan admin wajib diisi.")
    cleaned = response.strip()
    if not cleaned:
        raise ValueError("Tanggapan admin tidak boleh hanya berupa spasi.")
    if len(cleaned) < 10 or len(cleaned) > 5000:
        raise ValueError("Tanggapan admin harus memiliki panjang antara 10 hingga 5000 karakter.")
    return cleaned


def validate_transition(current_status: str, target_status: str) -> bool:
    """
    Check if transitioning from current_status to target_status is allowed.
    """
    return target_status in ALLOWED_TRANSITIONS.get(current_status, set())


def create_complaint(user_id: int, subject: str, message: str) -> Complaint:
    """
    Creates a new complaint for a citizen.
    Enforces server-side ticket generation, initial OPEN status, and NULL admin_response.
    Protects against mass assignment by strictly mapping only validated user fields.
    """
    cleaned_subject = validate_subject(subject)
    cleaned_message = validate_message(message)
    ticket_num = generate_ticket_number()

    now = datetime.now(timezone.utc)
    try:
        complaint = Complaint(
            ticket_number=ticket_num,
            user_id=user_id,
            subject=cleaned_subject,
            message=cleaned_message,
            status=STATUS_OPEN,
            admin_response=None,
            created_at=now,
            updated_at=now,
        )
        db.session.add(complaint)
        db.session.commit()
        return complaint
    except Exception:
        db.session.rollback()
        raise


def start_complaint_processing(complaint: Complaint) -> Complaint:
    """
    Admin starts processing an OPEN complaint: OPEN -> IN_PROGRESS.
    """
    if complaint.status != STATUS_OPEN:
        raise ValueError(
            f"Tidak dapat memulai proses. Pengaduan berstatus '{COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}'."
        )

    try:
        complaint.status = STATUS_IN_PROGRESS
        complaint.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return complaint
    except Exception:
        db.session.rollback()
        raise


def resolve_complaint(complaint: Complaint, admin_response: str) -> Complaint:
    """
    Admin resolves an IN_PROGRESS complaint: IN_PROGRESS -> RESOLVED.
    Requires validated admin_response.
    """
    if complaint.status != STATUS_IN_PROGRESS:
        raise ValueError(
            f"Tidak dapat menyelesaikan pengaduan. Status saat ini '{COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}'. Harus 'Sedang Diproses'."
        )

    cleaned_response = validate_admin_response(admin_response)

    try:
        complaint.status = STATUS_RESOLVED
        complaint.admin_response = cleaned_response
        complaint.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return complaint
    except Exception:
        db.session.rollback()
        raise


def reject_complaint(complaint: Complaint, reason: str) -> Complaint:
    """
    Admin rejects an OPEN or IN_PROGRESS complaint: OPEN/IN_PROGRESS -> REJECTED.
    Requires validated reason.
    """
    if complaint.status not in (STATUS_OPEN, STATUS_IN_PROGRESS):
        raise ValueError(
            f"Tidak dapat menolak pengaduan. Status saat ini '{COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}' sudah final."
        )

    cleaned_reason = validate_admin_response(reason)

    try:
        complaint.status = STATUS_REJECTED
        complaint.admin_response = cleaned_reason
        complaint.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return complaint
    except Exception:
        db.session.rollback()
        raise


def transition_complaint(complaint: Complaint, target_status: str, admin_response: str = None) -> Complaint:
    """
    Central dispatcher for complaint status transitions with strict validation.
    """
    if not validate_transition(complaint.status, target_status):
        raise ValueError(
            f"Perubahan status dari '{complaint.status}' ke '{target_status}' tidak diizinkan."
        )

    if target_status == STATUS_IN_PROGRESS:
        return start_complaint_processing(complaint)
    elif target_status == STATUS_RESOLVED:
        return resolve_complaint(complaint, admin_response)
    elif target_status == STATUS_REJECTED:
        return reject_complaint(complaint, admin_response)
    else:
        raise ValueError(f"Target status '{target_status}' tidak valid.")
