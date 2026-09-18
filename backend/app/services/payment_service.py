import secrets
import string
from datetime import date, datetime, timezone
from sqlalchemy import select
from app.extensions import db
from app.models.contribution import Contribution
from app.models.payment import Payment

VALID_PAYMENT_METHODS = {
    "SIMULATION_CASH": "Simulasi Tunai",
    "SIMULATION_TRANSFER": "Simulasi Transfer",
    "SIMULATION_VIRTUAL_ACCOUNT": "Simulasi Virtual Account",
}

PAYMENT_STATUS_LABELS = {
    "PENDING": "Menunggu",
    "SUCCESS": "Berhasil",
    "FAILED": "Gagal",
}

SIMULATION_NOTICE = (
    "Pembayaran ini merupakan simulasi untuk kebutuhan prototype akademik SehatWarga. "
    "Tidak ada transaksi keuangan nyata dan fitur ini bukan sistem pembayaran BPJS."
)


def generate_payment_number(target_date: date = None) -> str:
    """
    Generates a cryptographically secure, unique payment receipt number.
    Format: SWP-YYYYMMDD-XXXXXXXX
    Example: SWP-20260904-A7M2Q8K4
    """
    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    date_str = target_date.strftime("%Y%m%d")
    charset = string.ascii_uppercase + string.digits

    max_attempts = 100
    for _ in range(max_attempts):
        random_suffix = "".join(secrets.choice(charset) for _ in range(8))
        candidate = f"SWP-{date_str}-{random_suffix}"

        # Collision check
        existing = db.session.execute(
            select(Payment.id).filter_by(payment_number=candidate)
        ).scalar_one_or_none()

        if not existing:
            return candidate

    raise RuntimeError("Gagal menghasilkan nomor pembayaran unik setelah beberapa kali percobaan.")


def process_simulated_payment(contribution: Contribution, payment_method: str) -> Payment:
    """
    Simulates a payment transaction for a Contribution atomically.
    Validates that:
    1. Contribution status is UNPAID or OVERDUE (rejects already PAID).
    2. Payment method is strictly in the whitelist of simulated methods.
    3. Amount is derived solely from Contribution.amount (client input ignored/tamper-proof).
    4. Transitions Contribution.status to PAID and creates Payment record with status SUCCESS.
    """
    # 1. Validate contribution status
    if contribution.status == "PAID":
        raise ValueError("Tagihan iuran ini sudah lunas.")

    if contribution.status not in ["UNPAID", "OVERDUE"]:
        raise ValueError(f"Tagihan dengan status '{contribution.status}' tidak dapat diproses.")

    # 2. Validate payment method
    if payment_method not in VALID_PAYMENT_METHODS:
        raise ValueError(
            f"Metode pembayaran simulasi '{payment_method}' tidak valid. "
            "Pilih salah satu metode simulasi yang tersedia."
        )

    # 3. Generate unique payment number
    payment_number = generate_payment_number()
    now = datetime.now(timezone.utc)

    try:
        payment = Payment(
            contribution_id=contribution.id,
            payment_number=payment_number,
            amount=contribution.amount,  # Strictly server-side source of truth
            payment_method=payment_method,
            status="SUCCESS",
            paid_at=now,
        )
        db.session.add(payment)

        # Update contribution status
        contribution.status = "PAID"
        contribution.updated_at = now

        db.session.commit()
        return payment
    except Exception:
        db.session.rollback()
        raise
