import tests
import re
import unittest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.services.participant_service import register_citizen
from app.services.contribution_service import (
    SIMULATED_RATES,
    RATE_DESCRIPTION,
    CONTRIBUTION_STATUS_LABELS,
    get_rate_for_service_class,
    get_billing_period_start,
    get_simulated_due_date,
    generate_monthly_contribution,
    generate_contributions_for_active_participants,
    mark_overdue_contributions,
)
from app.services.payment_service import (
    VALID_PAYMENT_METHODS,
    PAYMENT_STATUS_LABELS,
    SIMULATION_NOTICE,
    generate_payment_number,
    process_simulated_payment,
)


class Stage6TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.rollback()

        # Clean up payments and contributions for test_s6_ users
        test_contributions = db.session.execute(
            select(Contribution)
            .join(Contribution.participant)
            .join(Participant.user)
            .filter(User.email.like("test_s6_%@example.com"))
        ).scalars().all()
        for c in test_contributions:
            for p in c.payments:
                db.session.delete(p)
            db.session.delete(c)

        # Clean up participants and users
        test_users = db.session.execute(
            select(User).filter(User.email.like("test_s6_%@example.com"))
        ).scalars().all()
        for u in test_users:
            if u.participant:
                for fm in u.participant.family_members:
                    db.session.delete(fm)
                db.session.delete(u.participant)
            db.session.delete(u)

        db.session.commit()
        self.ctx.pop()

    def get_csrf_token(self, url):
        res = self.client.get(url)
        html = res.get_data(as_text=True)
        match = re.search(r'name="csrf_token"[^>]*?value="([^"]+)"', html)
        self.assertTrue(match, f"CSRF token not found in {url}")
        return match.group(1)

    def create_citizen(self, tag, service_class="CLASS_1", is_active_membership=True):
        user, participant = register_citizen(
            name=f"Citizen S6 {tag}",
            email=f"test_s6_{tag}@example.com",
            password="Password123!",
            birth_date=date(1990, 1, 1),
            gender="MALE",
            service_class=service_class,
        )
        if not is_active_membership:
            participant.membership_status = "INACTIVE"
            db.session.commit()
        return user, participant

    def create_admin(self, tag):
        admin = User(
            name=f"Admin S6 {tag}",
            email=f"test_s6_{tag}@example.com",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        return admin

    def login(self, email, password="Password123!"):
        csrf_token = self.get_csrf_token("/login")
        return self.client.post(
            "/login",
            data={
                "csrf_token": csrf_token,
                "email": email,
                "password": password,
            },
            follow_redirects=True,
        )

    # ------------------------------------------------------------
    # 1. Rate Mapping & Rate Rules Tests
    # ------------------------------------------------------------
    def test_simulated_rates_mapping(self):
        """Test simulated rates are exact and mapped to CLASS_1, CLASS_2, CLASS_3."""
        self.assertEqual(get_rate_for_service_class("CLASS_1"), Decimal("150000.00"))
        self.assertEqual(get_rate_for_service_class("CLASS_2"), Decimal("100000.00"))
        self.assertEqual(get_rate_for_service_class("CLASS_3"), Decimal("50000.00"))
        self.assertIn("Tarif simulasi SehatWarga", RATE_DESCRIPTION)

        with self.assertRaises(ValueError):
            get_rate_for_service_class("CLASS_UNKNOWN")

    # ------------------------------------------------------------
    # 2. Monthly Contribution Generation Tests
    # ------------------------------------------------------------
    def test_generate_monthly_contribution_active_participant(self):
        """Active participant generates UNPAID contribution for the specified period."""
        user, participant = self.create_citizen("gen_act", service_class="CLASS_2")
        period = date(2026, 4, 1)

        contrib, created = generate_monthly_contribution(participant, period)
        self.assertTrue(created)
        self.assertIsNotNone(contrib.id)
        self.assertEqual(contrib.participant_id, participant.id)
        self.assertEqual(contrib.billing_period, period)
        self.assertEqual(contrib.amount, Decimal("100000.00"))
        self.assertEqual(contrib.due_date, date(2026, 4, 10))
        self.assertEqual(contrib.status, "UNPAID")
        self.assertIsNone(contrib.paid_at)

    def test_generate_monthly_contribution_inactive_participant_rejected(self):
        """Inactive participant is rejected from contribution generation."""
        user, participant = self.create_citizen("gen_inact", is_active_membership=False)
        period = date(2026, 4, 1)

        with self.assertRaises(ValueError) as ctx:
            generate_monthly_contribution(participant, period)
        self.assertIn("Peserta tidak aktif", str(ctx.exception))

    def test_billing_generation_idempotency(self):
        """Generating contribution twice for the same participant and period returns existing without duplicate."""
        user, participant = self.create_citizen("idempotent", service_class="CLASS_3")
        period = date(2026, 5, 1)

        c1, created1 = generate_monthly_contribution(participant, period)
        c2, created2 = generate_monthly_contribution(participant, period)

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(c1.id, c2.id)

        # Count records in db
        count = db.session.execute(
            select(Contribution).filter_by(participant_id=participant.id, billing_period=period)
        ).scalars().all()
        self.assertEqual(len(count), 1)

    def test_unique_constraint_enforcement(self):
        """Unique constraint on (participant_id, billing_period) raises IntegrityError on duplicate insert."""
        user, participant = self.create_citizen("uq_test", service_class="CLASS_1")
        period = date(2026, 6, 1)

        c1 = Contribution(
            participant_id=participant.id,
            billing_period=period,
            amount=Decimal("150000.00"),
            due_date=date(2026, 6, 10),
            status="UNPAID",
        )
        db.session.add(c1)
        db.session.commit()

        c2 = Contribution(
            participant_id=participant.id,
            billing_period=period,
            amount=Decimal("150000.00"),
            due_date=date(2026, 6, 10),
            status="UNPAID",
        )
        db.session.add(c2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_service_class_snapshot_behavior(self):
        """Changing participant service_class does not alter previously generated contribution amount."""
        user, participant = self.create_citizen("snapshot", service_class="CLASS_3")
        period = date(2026, 1, 1)

        contrib, created = generate_monthly_contribution(participant, period)
        self.assertEqual(contrib.amount, Decimal("50000.00"))

        # Update participant class to CLASS_1
        participant.service_class = "CLASS_1"
        db.session.commit()

        # Refresh contrib from db
        db.session.refresh(contrib)
        self.assertEqual(contrib.amount, Decimal("50000.00"))

    # ------------------------------------------------------------
    # 3. Overdue Transition Tests
    # ------------------------------------------------------------
    def test_overdue_transition_logic(self):
        """UNPAID contributions past due_date become OVERDUE; PAID contributions remain untouched."""
        user, participant = self.create_citizen("overdue", service_class="CLASS_1")

        # 1. Past due, UNPAID -> should transition to OVERDUE
        c_past = Contribution(
            participant_id=participant.id,
            billing_period=date(2026, 1, 1),
            amount=Decimal("150000.00"),
            due_date=date(2026, 1, 10),
            status="UNPAID",
        )
        # 2. Past due, PAID -> should remain PAID
        c_paid = Contribution(
            participant_id=participant.id,
            billing_period=date(2026, 2, 1),
            amount=Decimal("150000.00"),
            due_date=date(2026, 2, 10),
            status="PAID",
        )
        # 3. Future due, UNPAID -> should remain UNPAID
        c_future = Contribution(
            participant_id=participant.id,
            billing_period=date(2026, 8, 1),
            amount=Decimal("150000.00"),
            due_date=date(2026, 8, 10),
            status="UNPAID",
        )
        db.session.add_all([c_past, c_paid, c_future])
        db.session.commit()

        # Run overdue updater as of 2026-03-01
        updated = mark_overdue_contributions(as_of_date=date(2026, 3, 1))
        self.assertGreaterEqual(updated, 1)

        db.session.refresh(c_past)
        db.session.refresh(c_paid)
        db.session.refresh(c_future)

        self.assertEqual(c_past.status, "OVERDUE")
        self.assertEqual(c_paid.status, "PAID")
        self.assertEqual(c_future.status, "UNPAID")

    # ------------------------------------------------------------
    # 4. Ownership Protection Tests
    # ------------------------------------------------------------
    def test_citizen_cannot_view_or_pay_other_participant_contribution(self):
        """Citizen A cannot view or pay Citizen B's contribution (404/403)."""
        u_a, p_a = self.create_citizen("own_a", service_class="CLASS_1")
        u_b, p_b = self.create_citizen("own_b", service_class="CLASS_2")

        c_b, _ = generate_monthly_contribution(p_b, date(2026, 3, 1))

        # Login as Citizen A
        self.login(u_a.email)

        # Attempt to view detail of B's contribution
        res_detail = self.client.get(f"/citizen/contributions/{c_b.id}")
        self.assertEqual(res_detail.status_code, 404)

        # Attempt to access payment page of B's contribution
        res_pay_get = self.client.get(f"/citizen/contributions/{c_b.id}/pay")
        self.assertEqual(res_pay_get.status_code, 404)

        # Attempt to post payment for B's contribution
        csrf_token = self.get_csrf_token("/citizen/contributions")
        res_pay_post = self.client.post(
            f"/citizen/contributions/{c_b.id}/pay",
            data={
                "csrf_token": csrf_token,
                "payment_method": "SIMULATION_TRANSFER",
                "agreement": "y",
            },
        )
        self.assertEqual(res_pay_post.status_code, 404)

    # ------------------------------------------------------------
    # 5. Simulated Payment Flow & Atomic Transition Tests
    # ------------------------------------------------------------
    def test_valid_simulated_payment_success(self):
        """Citizen pays their UNPAID contribution: Payment created, Contribution PAID."""
        user, participant = self.create_citizen("pay_succ", service_class="CLASS_2")
        contrib, _ = generate_monthly_contribution(participant, date(2026, 3, 1))

        self.login(user.email)

        pay_url = f"/citizen/contributions/{contrib.id}/pay"
        csrf = self.get_csrf_token(pay_url)

        res = self.client.post(
            pay_url,
            data={
                "csrf_token": csrf,
                "payment_method": "SIMULATION_VIRTUAL_ACCOUNT",
                "agreement": "y",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        # Check DB state
        db.session.refresh(contrib)
        self.assertEqual(contrib.status, "PAID")
        self.assertIsNotNone(contrib.paid_at)

        payments = contrib.payments
        self.assertEqual(len(payments), 1)
        p = payments[0]
        self.assertEqual(p.amount, Decimal("100000.00"))
        self.assertEqual(p.payment_method, "SIMULATION_VIRTUAL_ACCOUNT")
        self.assertEqual(p.status, "SUCCESS")
        self.assertTrue(p.payment_number.startswith("SWP-"))

        # Verify receipt page
        res_receipt = self.client.get(f"/citizen/payments/{p.id}")
        self.assertEqual(res_receipt.status_code, 200)
        self.assertIn("Bukti Pembayaran Iuran Elektronik", res_receipt.get_data(as_text=True))
        self.assertIn(p.payment_number, res_receipt.get_data(as_text=True))

    def test_pay_overdue_contribution(self):
        """Citizen can successfully pay an OVERDUE contribution, which becomes PAID."""
        user, participant = self.create_citizen("pay_ovd", service_class="CLASS_3")
        contrib = Contribution(
            participant_id=participant.id,
            billing_period=date(2026, 1, 1),
            amount=Decimal("50000.00"),
            due_date=date(2026, 1, 10),
            status="OVERDUE",
        )
        db.session.add(contrib)
        db.session.commit()

        self.login(user.email)

        pay_url = f"/citizen/contributions/{contrib.id}/pay"
        csrf = self.get_csrf_token(pay_url)

        res = self.client.post(
            pay_url,
            data={
                "csrf_token": csrf,
                "payment_method": "SIMULATION_CASH",
                "agreement": "y",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        db.session.refresh(contrib)
        self.assertEqual(contrib.status, "PAID")
        self.assertIsNotNone(contrib.paid_at)
        self.assertEqual(len(contrib.payments), 1)
        self.assertEqual(contrib.payments[0].status, "SUCCESS")

    def test_duplicate_payment_rejection(self):
        """Paying an already PAID contribution is rejected and redirected."""
        user, participant = self.create_citizen("dup_pay", service_class="CLASS_1")
        contrib, _ = generate_monthly_contribution(participant, date(2026, 3, 1))

        # First payment
        process_simulated_payment(contrib, "SIMULATION_TRANSFER")
        self.assertEqual(contrib.status, "PAID")

        # Second attempt via service raises ValueError
        with self.assertRaises(ValueError) as ctx:
            process_simulated_payment(contrib, "SIMULATION_CASH")
        self.assertIn("sudah lunas", str(ctx.exception))

        # Second attempt via HTTP redirects with info message
        self.login(user.email)
        pay_url = f"/citizen/contributions/{contrib.id}/pay"
        res = self.client.get(pay_url, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn("sudah lunas", res.get_data(as_text=True))

    def test_payment_amount_tamper_proofing(self):
        """Client cannot alter payment amount; amount is derived strictly from contribution."""
        user, participant = self.create_citizen("tamper", service_class="CLASS_1")
        contrib, _ = generate_monthly_contribution(participant, date(2026, 3, 1))
        self.assertEqual(contrib.amount, Decimal("150000.00"))

        self.login(user.email)

        pay_url = f"/citizen/contributions/{contrib.id}/pay"
        csrf = self.get_csrf_token(pay_url)

        # Attempt to tamper amount via POST payload
        res = self.client.post(
            pay_url,
            data={
                "csrf_token": csrf,
                "payment_method": "SIMULATION_TRANSFER",
                "agreement": "y",
                "amount": "1000",  # Fake amount
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)

        db.session.refresh(contrib)
        payment = contrib.payments[0]
        # Must be exactly 150000.00, not 1000
        self.assertEqual(payment.amount, Decimal("150000.00"))

    def test_payment_method_whitelist_validation(self):
        """Invalid payment method is rejected by service and form."""
        user, participant = self.create_citizen("method_val", service_class="CLASS_2")
        contrib, _ = generate_monthly_contribution(participant, date(2026, 3, 1))

        with self.assertRaises(ValueError) as ctx:
            process_simulated_payment(contrib, "CREDIT_CARD_VISA")
        self.assertIn("tidak valid", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            process_simulated_payment(contrib, "REAL_BANK_TRANSFER")
        self.assertIn("tidak valid", str(ctx.exception))

    def test_payment_agreement_checkbox_required(self):
        """Omitting agreement checkbox fails form validation."""
        user, participant = self.create_citizen("agree_val", service_class="CLASS_1")
        contrib, _ = generate_monthly_contribution(participant, date(2026, 3, 1))

        self.login(user.email)

        pay_url = f"/citizen/contributions/{contrib.id}/pay"
        csrf = self.get_csrf_token(pay_url)

        res = self.client.post(
            pay_url,
            data={
                "csrf_token": csrf,
                "payment_method": "SIMULATION_TRANSFER",
                # agreement not sent
            },
        )
        self.assertEqual(res.status_code, 200)
        # Form error
        self.assertIn("Anda harus menyetujui pernyataan simulasi", res.get_data(as_text=True))
        db.session.refresh(contrib)
        self.assertEqual(contrib.status, "UNPAID")

    def test_payment_privacy_isolation(self):
        """Citizen A cannot view Citizen B's payment detail/receipt."""
        u_a, p_a = self.create_citizen("priv_a", service_class="CLASS_1")
        u_b, p_b = self.create_citizen("priv_b", service_class="CLASS_2")

        c_b, _ = generate_monthly_contribution(p_b, date(2026, 3, 1))
        pay_b = process_simulated_payment(c_b, "SIMULATION_TRANSFER")

        self.login(u_a.email)

        res = self.client.get(f"/citizen/payments/{pay_b.id}")
        self.assertEqual(res.status_code, 404)

    # ------------------------------------------------------------
    # 6. Admin Management Tests
    # ------------------------------------------------------------
    def test_admin_contributions_list_and_filters(self):
        """Admin can access contribution list and filter by status, class, and month."""
        admin = self.create_admin("mgr_1")
        u1, p1 = self.create_citizen("adm_c1", service_class="CLASS_1")
        u2, p2 = self.create_citizen("adm_c2", service_class="CLASS_2")

        c1, _ = generate_monthly_contribution(p1, date(2026, 3, 1))
        c2, _ = generate_monthly_contribution(p2, date(2026, 3, 1))

        self.login(admin.email, "AdminPass123!")

        res = self.client.get("/admin/contributions")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn(p1.participant_number, html)
        self.assertIn(p2.participant_number, html)

        # Filter by service_class
        res_f = self.client.get("/admin/contributions?service_class=CLASS_1")
        self.assertEqual(res_f.status_code, 200)
        html_f = res_f.get_data(as_text=True)
        self.assertIn(p1.participant_number, html_f)

    def test_admin_generate_contributions_post(self):
        """Admin can trigger monthly contribution generation for all active participants."""
        admin = self.create_admin("gen_adm")
        u1, p1 = self.create_citizen("bulk_1", service_class="CLASS_1")
        u2, p2 = self.create_citizen("bulk_2", service_class="CLASS_2")

        self.login(admin.email, "AdminPass123!")

        csrf = self.get_csrf_token("/admin/contributions")
        res = self.client.post(
            "/admin/contributions/generate",
            data={
                "csrf_token": csrf,
                "billing_month": "2026-07",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("berhasil diproses", res.get_data(as_text=True))

        # Verify DB records
        c1 = db.session.execute(
            select(Contribution).filter_by(participant_id=p1.id, billing_period=date(2026, 7, 1))
        ).scalar_one_or_none()
        self.assertIsNotNone(c1)
        self.assertEqual(c1.amount, Decimal("150000.00"))

    def test_admin_payments_list(self):
        """Admin can view the payments history list."""
        admin = self.create_admin("pay_adm")
        u, p = self.create_citizen("pay_adm_u", service_class="CLASS_1")
        contrib, _ = generate_monthly_contribution(p, date(2026, 3, 1))
        payment = process_simulated_payment(contrib, "SIMULATION_CASH")

        self.login(admin.email, "AdminPass123!")

        res = self.client.get("/admin/payments")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn(payment.payment_number, html)
        self.assertIn(p.full_name, html)

    # ------------------------------------------------------------
    # 7. CLI Commands Tests
    # ------------------------------------------------------------
    def test_cli_generate_contributions_and_overdue(self):
        """Test Flask CLI commands 'generate-contributions' and 'update-overdue'."""
        runner = self.app.test_cli_runner()

        # Run generate-contributions
        res_gen = runner.invoke(args=["generate-contributions", "--month", "2026-09"])
        self.assertEqual(res_gen.exit_code, 0)
        self.assertIn("Tagihan periode", res_gen.output)

        # Run update-overdue
        res_ovd = runner.invoke(args=["update-overdue", "--as-of", "2026-09-15"])
        self.assertEqual(res_ovd.exit_code, 0)
        self.assertIn("Pembaruan status overdue selesai", res_ovd.output)


if __name__ == "__main__":
    unittest.main()
