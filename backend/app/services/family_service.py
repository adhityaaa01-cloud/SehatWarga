import secrets
import string
from datetime import datetime, timezone
from sqlalchemy import select
from app.extensions import db
from app.models.family_member import FamilyMember


def generate_family_member_number(year: int = None) -> str:
    """
    Generate a cryptographically secure, unique family member number for SehatWarga.
    Format: SWF-YYYY-XXXXXXXX
    Example: SWF-2026-K8P4T2Q1
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    charset = string.ascii_uppercase + string.digits

    max_attempts = 100
    for _ in range(max_attempts):
        random_suffix = "".join(secrets.choice(charset) for _ in range(8))
        candidate = f"SWF-{year}-{random_suffix}"

        # Check for collision in database
        existing = db.session.execute(
            select(FamilyMember.id).filter_by(member_number=candidate)
        ).scalar_one_or_none()

        if not existing:
            return candidate

    raise RuntimeError("Gagal menghasilkan nomor anggota keluarga unik setelah beberapa kali percobaan.")


def create_family_member(
    participant_id: int,
    full_name: str,
    relationship: str,
    birth_date,
    gender: str,
) -> FamilyMember:
    """
    Creates a new FamilyMember attached to the specified participant.
    """
    cleaned_name = full_name.strip()
    member_number = generate_family_member_number()

    try:
        member = FamilyMember(
            participant_id=participant_id,
            member_number=member_number,
            full_name=cleaned_name,
            relationship=relationship,
            birth_date=birth_date,
            gender=gender,
            membership_status="ACTIVE",
        )
        db.session.add(member)
        db.session.commit()
        return member
    except Exception:
        db.session.rollback()
        raise


def update_family_member(
    member: FamilyMember,
    full_name: str,
    relationship: str,
    birth_date,
    gender: str,
) -> FamilyMember:
    """
    Updates editable fields of an existing FamilyMember using a strict whitelist.
    """
    try:
        member.full_name = full_name.strip()
        member.relationship = relationship
        member.birth_date = birth_date
        member.gender = gender
        db.session.commit()
        return member
    except Exception:
        db.session.rollback()
        raise


def deactivate_family_member(member: FamilyMember) -> FamilyMember:
    """
    Deactivates a FamilyMember without deleting the row to preserve administrative audit trail.
    ACTIVE -> INACTIVE
    """
    try:
        member.membership_status = "INACTIVE"
        db.session.commit()
        return member
    except Exception:
        db.session.rollback()
        raise
