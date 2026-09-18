from datetime import datetime
from app.extensions import db


class ServiceRequest(db.Model):
    __tablename__ = "service_requests"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    family_member_id = db.Column(db.Integer, db.ForeignKey("family_members.id"), nullable=True)
    health_facility_id = db.Column(db.Integer, db.ForeignKey("health_facilities.id"), nullable=False)
    service_type = db.Column(db.String(30), nullable=False)  # GENERAL, DENTAL, MATERNAL, SPECIALIST, OTHER
    scheduled_date = db.Column(db.Date, nullable=True)
    complaint_summary = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="SUBMITTED")  # SUBMITTED, VERIFIED, SCHEDULED, COMPLETED, CANCELLED, REJECTED
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    participant = db.relationship("Participant", back_populates="service_requests")
    family_member = db.relationship("FamilyMember", back_populates="service_requests")
    health_facility = db.relationship("HealthFacility", back_populates="service_requests")
    histories = db.relationship("ServiceHistory", back_populates="service_request", order_by="ServiceHistory.created_at")

    def __repr__(self):
        return f"<ServiceRequest {self.id}:{self.request_number}>"
