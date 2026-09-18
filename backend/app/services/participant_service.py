import secrets
import string
from datetime import datetime, timezone
from sqlalchemy import select
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant


def generate_participant_number(year: int = None) -> str:
    """
    Generate a cryptographically secure, unique participant number for SehatWarga.
    Format: SW-YYYY-XXXXXXXX
    Example: SW-2026-A8K4M2Q7
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    charset = string.ascii_uppercase + string.digits

    max_attempts = 100
    for _ in range(max_attempts):
        random_suffix = "".join(secrets.choice(charset) for _ in range(8))
        candidate = f"SW-{year}-{random_suffix}"

        # Check for collision in database
        existing = db.session.execute(
            select(Participant.id).filter_by(participant_number=candidate)
        ).scalar_one_or_none()

        if not existing:
            return candidate

    raise RuntimeError("Gagal menghasilkan nomor peserta unik setelah beberapa kali percobaan.")


def register_citizen(
    name: str,
    email: str,
    password: str,
    birth_date,
    gender: str,
    service_class: str,
) -> tuple[User, Participant]:
    """
    Atomically creates a citizen User and associated Participant record.
    If any step fails, the entire transaction is rolled back.
    """
    if gender not in {"MALE", "FEMALE"}:
        raise ValueError("Jenis kelamin tidak valid.")
    if service_class not in {"CLASS_1", "CLASS_2", "CLASS_3"}:
        raise ValueError("Kelas layanan tidak valid.")
    cleaned_name = name.strip()
    cleaned_email = email.strip().lower()

    # Double check unique email
    existing_user = db.session.execute(
        select(User.id).filter_by(email=cleaned_email)
    ).scalar_one_or_none()
    if existing_user:
        raise ValueError("Email sudah terdaftar.")

    # Generate participant number
    participant_num = generate_participant_number()

    try:
        # Create User
        user = User(
            name=cleaned_name,
            email=cleaned_email,
            role="citizen",
            is_active=True,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # Populates user.id

        # Create Participant
        participant = Participant(
            user_id=user.id,
            participant_number=participant_num,
            full_name=user.name,
            birth_date=birth_date,
            gender=gender,
            membership_status="ACTIVE",
            service_class=service_class,
            registered_at=datetime.now(timezone.utc),
        )
        db.session.add(participant)
        db.session.commit()

        return user, participant
    except Exception:
        db.session.rollback()
        raise
