from datetime import datetime
from app.extensions import db


class FamilyMember(db.Model):
    __tablename__ = "family_members"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    member_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    relationship = db.Column(db.String(20), nullable=False)  # SPOUSE, CHILD, PARENT, OTHER
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # MALE / FEMALE
    membership_status = db.Column(db.String(20), nullable=False, default="ACTIVE")  # ACTIVE / INACTIVE
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    participant = db.relationship("Participant", back_populates="family_members")
    service_requests = db.relationship("ServiceRequest", back_populates="family_member")

    def __repr__(self):
        return f"<FamilyMember {self.id}:{self.member_number}>"
