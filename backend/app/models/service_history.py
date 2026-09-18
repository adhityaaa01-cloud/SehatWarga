from datetime import datetime
from app.extensions import db


class ServiceHistory(db.Model):
    __tablename__ = "service_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey("service_requests.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text, nullable=True)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    service_request = db.relationship("ServiceRequest", back_populates="histories")
    actor = db.relationship("User", back_populates="serviced_histories", foreign_keys=[changed_by])

    def __repr__(self):
        return f"<ServiceHistory {self.id}:req_{self.service_request_id}:{self.status}>"
