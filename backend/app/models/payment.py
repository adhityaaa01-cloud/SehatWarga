from datetime import datetime
from app.extensions import db


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    contribution_id = db.Column(db.Integer, db.ForeignKey("contributions.id"), nullable=False)
    payment_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_method = db.Column(db.String(40), nullable=False)  # SIMULATION_CASH, SIMULATION_TRANSFER, SIMULATION_VIRTUAL_ACCOUNT
    status = db.Column(db.String(20), nullable=False, default="PENDING")  # PENDING, SUCCESS, FAILED
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    contribution = db.relationship("Contribution", back_populates="payments")

    def __repr__(self):
        return f"<Payment {self.id}:{self.payment_number}>"
