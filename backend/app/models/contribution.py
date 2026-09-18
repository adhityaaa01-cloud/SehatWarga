from datetime import datetime
from app.extensions import db


class Contribution(db.Model):
    __tablename__ = "contributions"
    __table_args__ = (
        db.UniqueConstraint("participant_id", "billing_period", name="uq_participant_billing_period"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=False)
    billing_period = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="UNPAID")  # UNPAID, PAID, OVERDUE
    due_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    participant = db.relationship("Participant", back_populates="contributions")
    payments = db.relationship("Payment", back_populates="contribution")

    @property
    def paid_at(self):
        successful = [p for p in self.payments if p.status == "SUCCESS" and p.paid_at]
        if successful:
            return successful[-1].paid_at
        return None

    def __repr__(self):
        return f"<Contribution {self.id}:part_{self.participant_id}:{self.billing_period}>"
