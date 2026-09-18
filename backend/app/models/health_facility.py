from datetime import datetime
from app.extensions import db


class HealthFacility(db.Model):
    __tablename__ = "health_facilities"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    facility_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    facility_type = db.Column(db.String(30), nullable=False)  # PUSKESMAS, CLINIC, HOSPITAL, DENTAL_CLINIC, OTHER
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    latitude = db.Column(db.Numeric(10, 7), nullable=True)
    longitude = db.Column(db.Numeric(10, 7), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    service_requests = db.relationship("ServiceRequest", back_populates="health_facility")

    def __repr__(self):
        return f"<HealthFacility {self.id}:{self.facility_code}>"
