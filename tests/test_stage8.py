import tests
import re
import unittest
from datetime import date
from sqlalchemy import select
from flask import abort
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.family_member import FamilyMember
from app.models.service_request import ServiceRequest
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.models.complaint import Complaint
from app.services.participant_service import register_citizen


class Stage8TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True

        # Register test endpoints before any requests are handled
        @cls.app.route("/test-trigger-400")
        def trigger_400():
            abort(400, description="Test Bad Request Payload")

        @cls.app.route("/test-trigger-500")
        def trigger_500():
            raise RuntimeError("Database connection secret-password-123 failed!")

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.rollback()

        # Clean up test_s8_ users
        test_complaints = db.session.execute(
            select(Complaint)
            .join(Complaint.user)
            .filter(User.email.like("test_s8_%@example.com"))
        ).scalars().all()
        for c in test_complaints:
            db.session.delete(c)

        test_users = db.session.execute(
            select(User).filter(User.email.like("test_s8_%@example.com"))
        ).scalars().all()
        for u in test_users:
            if u.participant:
                for f in u.participant.family_members:
                    db.session.delete(f)
                for sr in u.participant.service_requests:
                    for h in sr.histories:
                        db.session.delete(h)
                    db.session.delete(sr)
                for cb in u.participant.contributions:
                    for p in cb.payments:
                        db.session.delete(p)
                    db.session.delete(cb)
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

    def create_citizen(self, tag):
        user, participant = register_citizen(
            name=f"Citizen S8 {tag}",
            email=f"test_s8_{tag}@example.com",
            password="Password123!",
            birth_date=date(1993, 6, 15),
            gender="MALE",
            service_class="CLASS_2",
        )
        return user, participant

    def create_admin(self, tag):
        admin = User(
            name=f"Admin S8 {tag}",
            email=f"test_s8_{tag}@example.com",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        return admin

    def login(self, email, password):
        csrf_token = self.get_csrf_token("/login")
        return self.client.post(
            "/login",
            data={"email": email, "password": password, "csrf_token": csrf_token},
            follow_redirects=True,
        )

    # -------------------------------------------------------------
    # 1. ERROR HANDLERS (404, 403, 400, 500)
    # -------------------------------------------------------------
    def test_01_custom_404_error_page(self):
        res = self.client.get("/halaman-ini-pasti-tidak-ada-404")
        self.assertEqual(res.status_code, 404)
        html = res.get_data(as_text=True)
        self.assertIn("404", html)
        self.assertIn("Halaman Tidak Ditemukan", html)
        self.assertIn("SehatWarga", html)
        self.assertIn("Beranda", html)

    def test_02_custom_403_error_page(self):
        self.create_citizen("role_403")
        self.login("test_s8_role_403@example.com", "Password123!")

        # Citizen attempts to access admin route
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 403)
        html = res.get_data(as_text=True)
        self.assertIn("403", html)
        self.assertIn("Akses Tidak Diizinkan", html)
        self.assertIn("Anda tidak memiliki hak akses", html)

    def test_03_custom_400_error_page(self):
        res = self.client.get("/test-trigger-400")
        self.assertEqual(res.status_code, 400)
        html = res.get_data(as_text=True)
        self.assertIn("400", html)
        self.assertIn("Permintaan Tidak Dapat Diproses", html)
        self.assertIn("Permintaan yang dikirim tidak valid", html)

    def test_04_custom_500_error_page_does_not_leak_traceback(self):
        prev_propagate = self.app.config.get("PROPAGATE_EXCEPTIONS")
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        try:
            res = self.client.get("/test-trigger-500")
            self.assertEqual(res.status_code, 500)
            html = res.get_data(as_text=True)
            self.assertIn("500", html)
            self.assertIn("Terjadi Kesalahan pada Sistem", html)
            # Must NOT expose sensitive stack trace or database error message
            self.assertNotIn("secret-password-123", html)
            self.assertNotIn("Traceback (most recent call last)", html)
        finally:
            self.app.config["PROPAGATE_EXCEPTIONS"] = prev_propagate

    # -------------------------------------------------------------
    # 2. OPEN REDIRECT SECURITY
    # -------------------------------------------------------------
    def test_05_open_redirect_rejected_external_url(self):
        self.create_citizen("redirect_ext")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=https://malicious-site.test/steal",
            data={
                "email": "test_s8_redirect_ext@example.com",
                "password": "Password123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        # Must redirect safely to citizen dashboard, NOT external site
        self.assertEqual(res.headers.get("Location"), "/citizen/dashboard")

    def test_06_open_redirect_rejected_protocol_relative_url(self):
        self.create_citizen("redirect_proto")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=//malicious-site.test/steal",
            data={
                "email": "test_s8_redirect_proto@example.com",
                "password": "Password123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/citizen/dashboard")

    def test_07_open_redirect_rejected_backslash_url(self):
        self.create_citizen("redirect_slash")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=/\\malicious-site.test",
            data={
                "email": "test_s8_redirect_slash@example.com",
                "password": "Password123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/citizen/dashboard")

    def test_08_open_redirect_citizen_blocked_from_admin_next(self):
        self.create_citizen("redirect_adm")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=/admin/dashboard",
            data={
                "email": "test_s8_redirect_adm@example.com",
                "password": "Password123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/citizen/dashboard")

    def test_09_open_redirect_admin_blocked_from_citizen_next(self):
        self.create_admin("redirect_cit")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=/citizen/dashboard",
            data={
                "email": "test_s8_redirect_cit@example.com",
                "password": "AdminPass123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/admin/dashboard")

    def test_10_open_redirect_safe_relative_url_allowed(self):
        self.create_citizen("redirect_ok")
        csrf_token = self.get_csrf_token("/login")

        res = self.client.post(
            "/login?next=/citizen/services",
            data={
                "email": "test_s8_redirect_ok@example.com",
                "password": "Password123!",
                "csrf_token": csrf_token,
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.headers.get("Location"), "/citizen/services")

    # -------------------------------------------------------------
    # 3. CSRF PROTECTION VALIDATION
    # -------------------------------------------------------------
    def test_11_csrf_protection_rejects_missing_token_on_post(self):
        self.create_citizen("csrf_test")
        self.login("test_s8_csrf_test@example.com", "Password123!")

        res = self.client.post(
            "/citizen/complaints/create",
            data={
                "subject": "Keluhan tanpa token CSRF",
                "message": "Pesan ini dikirim tanpa token pengaman form valid.",
            },
        )
        self.assertEqual(res.status_code, 400)

    # -------------------------------------------------------------
    # 4. DEMO SEED CLI COMMAND & IDEMPOTENCY
    # -------------------------------------------------------------
    def test_12_demo_seed_cli_execution_and_idempotency(self):
        runner = self.app.test_cli_runner()

        # Run 1: Should execute cleanly
        result1 = runner.invoke(
            args=["seed-demo", "--admin-password=AdminDemo123!", "--citizen-password=WargaDemo123!"]
        )
        self.assertEqual(result1.exit_code, 0)
        self.assertIn("HASIL SEED DEMO:", result1.output)
        self.assertIn("Status: SUKSES (Idempoten).", result1.output)

        # Run 2: Idempotent repeat
        result2 = runner.invoke(
            args=["seed-demo", "--admin-password=AdminDemo123!", "--citizen-password=WargaDemo123!"]
        )
        self.assertEqual(result2.exit_code, 0)
        self.assertIn("0 dibuat, 2 dilewati", result2.output)
        self.assertIn("Status: SUKSES (Idempoten).", result2.output)

    def test_13_demo_seeded_data_integrity(self):
        # Verify seeded admin
        admin = db.session.execute(
            select(User).filter_by(email="admin.demo@sehatwarga.test")
        ).scalar_one_or_none()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, "admin")
        self.assertTrue(admin.check_password("AdminDemo123!"))

        # Verify seeded citizen and participant
        citizen = db.session.execute(
            select(User).filter_by(email="warga.demo@sehatwarga.test")
        ).scalar_one_or_none()
        self.assertIsNotNone(citizen)
        self.assertEqual(citizen.role, "citizen")
        self.assertTrue(citizen.check_password("WargaDemo123!"))
        self.assertIsNotNone(citizen.participant)
        self.assertEqual(citizen.participant.service_class, "CLASS_2")

        # Verify family members
        family = db.session.execute(
            select(FamilyMember).filter_by(participant_id=citizen.participant.id)
        ).scalars().all()
        self.assertGreaterEqual(len(family), 2)
        rel_types = {m.relationship for m in family}
        self.assertIn("CHILD", rel_types)
        self.assertIn("SPOUSE", rel_types)

        # Verify service requests covering 5 statuses
        requests = db.session.execute(
            select(ServiceRequest).filter_by(participant_id=citizen.participant.id)
        ).scalars().all()
        sr_statuses = {sr.status for sr in requests}
        for st in ["SUBMITTED", "VERIFIED", "SCHEDULED", "COMPLETED", "REJECTED"]:
            self.assertIn(st, sr_statuses, f"Missing demo service request with status {st}")

        # Verify contributions covering UNPAID, PAID, OVERDUE
        contributions = db.session.execute(
            select(Contribution).filter_by(participant_id=citizen.participant.id)
        ).scalars().all()
        cb_statuses = {cb.status for cb in contributions}
        for st in ["UNPAID", "PAID", "OVERDUE"]:
            self.assertIn(st, cb_statuses, f"Missing demo contribution with status {st}")

        # Verify payment record on PAID contribution
        paid_contrib = next((cb for cb in contributions if cb.status == "PAID"), None)
        self.assertIsNotNone(paid_contrib)
        self.assertGreaterEqual(len(paid_contrib.payments), 1)
        self.assertEqual(paid_contrib.payments[0].status, "SUCCESS")

        # Verify complaints covering OPEN, IN_PROGRESS, RESOLVED
        complaints = db.session.execute(
            select(Complaint).filter_by(user_id=citizen.id)
        ).scalars().all()
        cmp_statuses = {cmp.status for cmp in complaints}
        for st in ["OPEN", "IN_PROGRESS", "RESOLVED"]:
            self.assertIn(st, cmp_statuses, f"Missing demo complaint with status {st}")

    # -------------------------------------------------------------
    # 5. ROUTE ACCESS MATRIX
    # -------------------------------------------------------------
    def test_14_unauthenticated_protected_routes_redirect_to_login(self):
        protected_urls = [
            "/citizen/dashboard",
            "/citizen/family",
            "/citizen/services",
            "/citizen/contributions",
            "/citizen/complaints",
            "/admin/dashboard",
            "/admin/facilities",
            "/admin/services",
            "/admin/contributions",
            "/admin/complaints",
        ]
        for url in protected_urls:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                302,
                f"URL {url} did not redirect unauthenticated user to login",
            )
            self.assertIn("/login", res.headers.get("Location", ""))

    def test_15_public_routes_accessible_without_auth(self):
        public_urls = ["/", "/login", "/register", "/facilities"]
        for url in public_urls:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                200,
                f"Public URL {url} returned non-200 status code {res.status_code}",
            )

    # -------------------------------------------------------------
    # 6. ACADEMIC DISCLAIMER COMPLIANCE
    # -------------------------------------------------------------
    def test_16_academic_disclaimer_present_across_pages(self):
        # 1. Homepage
        home_res = self.client.get("/")
        home_html = home_res.get_data(as_text=True)
        self.assertTrue(
            "kebutuhan akademik" in home_html.lower() or "prototype" in home_html.lower(),
            "Academic prototype disclaimer missing on homepage",
        )
        self.assertIn("bukan situs resmi bpjs", home_html.lower())

        # 2. Login
        login_res = self.client.get("/login")
        login_html = login_res.get_data(as_text=True)
        self.assertIn("bukan situs resmi bpjs", login_html.lower())

        # 3. Facilities
        fac_res = self.client.get("/facilities")
        fac_html = fac_res.get_data(as_text=True)
        self.assertIn("simulasi", fac_html.lower())


if __name__ == "__main__":
    unittest.main()
