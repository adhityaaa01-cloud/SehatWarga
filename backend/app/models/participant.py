from datetime import datetime
from app.extensions import db


class Participant(db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    participant_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # MALE / FEMALE
    membership_status = db.Column(db.String(20), nullable=False, default="ACTIVE")  # ACTIVE / INACTIVE
    service_class = db.Column(db.String(20), nullable=False)  # CLASS_1 / CLASS_2 / CLASS_3
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship("User", back_populates="participant")
    family_members = db.relationship("FamilyMember", back_populates="participant")
    service_requests = db.relationship("ServiceRequest", back_populates="participant")
    contributions = db.relationship("Contribution", back_populates="participant")

    def __repr__(self):
        return f"<Participant {self.id}:{self.participant_number}>"
