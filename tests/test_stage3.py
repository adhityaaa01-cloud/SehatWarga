import tests
import re
import unittest
from datetime import date, timedelta
from click.testing import CliRunner
from sqlalchemy import select
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.services.participant_service import generate_participant_number, register_citizen


class Stage3TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        # Keep CSRF enabled to test CSRF token extraction & protection
        cls.app.config["WTF_CSRF_ENABLED"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.runner = self.app.test_cli_runner()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        # Clean up any test records created with prefix test_
        db.session.rollback()
        test_users = db.session.execute(
            select(User).filter(User.email.like("test_%@example.com"))
        ).scalars().all()
        for u in test_users:
            if u.participant:
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

    # ---------------------------------------------------------
    # 33. TEST REGISTER
    # ---------------------------------------------------------
    def test_register_flow(self):
        # A. GET /register returns 200
        res = self.client.get("/register")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Pendaftaran Peserta", res.get_data(as_text=True))

        csrf_token = self.get_csrf_token("/register")

        # B. Register valid citizen
        email = "test_citizen1@example.com"
        post_data = {
            "csrf_token": csrf_token,
            "name": "Budi Santoso",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "birth_date": "1990-05-15",
            "gender": "MALE",
            "service_class": "CLASS_1",
        }
        res_post = self.client.post("/register", data=post_data, follow_redirects=False)
        self.assertEqual(res_post.status_code, 302)
        self.assertIn("/login", res_post.headers["Location"])

        # C. User dibuat with role=citizen
        user = db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none()
        self.assertIsNotNone(user)
        self.assertEqual(user.role, "citizen")
        self.assertTrue(user.is_active)

        # D. Participant dibuat
        participant = user.participant
        self.assertIsNotNone(participant)
        self.assertEqual(participant.full_name, "Budi Santoso")

        # E. Participant number generated backend + unique
        self.assertTrue(participant.participant_number.startswith("SW-"))
        self.assertRegex(participant.participant_number, r"^SW-\d{4}-[A-Z0-9]{8}$")

        # F. Membership status ACTIVE
        self.assertEqual(participant.membership_status, "ACTIVE")

        # G. Password hashed
        self.assertNotEqual(user.password_hash, "Password123!")
        self.assertTrue(user.check_password("Password123!"))
        self.assertFalse(user.check_password("WrongPassword"))

    # ---------------------------------------------------------
    # 34. TEST DUPLICATE EMAIL
    # ---------------------------------------------------------
    def test_duplicate_email_handling(self):
        csrf = self.get_csrf_token("/register")
        email = "test_dup@example.com"
        data = {
            "csrf_token": csrf,
            "name": "User Pertama",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "birth_date": "1992-01-01",
            "gender": "FEMALE",
            "service_class": "CLASS_2",
        }
        res1 = self.client.post("/register", data=data)
        self.assertEqual(res1.status_code, 302)

        # Register second time with same email
        csrf2 = self.get_csrf_token("/register")
        data["csrf_token"] = csrf2
        res2 = self.client.post("/register", data=data)
        self.assertIn(res2.status_code, [200, 400])
        self.assertIn("Email sudah terdaftar", res2.get_data(as_text=True))

        # Check DB only has 1 user with that email
        users = db.session.execute(select(User).filter_by(email=email)).scalars().all()
        self.assertEqual(len(users), 1)

    # ---------------------------------------------------------
    # 35. TEST PASSWORD VALIDATION
    # ---------------------------------------------------------
    def test_password_validation(self):
        # Short password (<8)
        csrf = self.get_csrf_token("/register")
        res = self.client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "Short Pass",
                "email": "test_short@example.com",
                "password": "short",
                "confirm_password": "short",
                "birth_date": "1990-01-01",
                "gender": "MALE",
                "service_class": "CLASS_3",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Kata sandi minimal 8 karakter", res.get_data(as_text=True))

        # Password mismatch
        csrf = self.get_csrf_token("/register")
        res_mismatch = self.client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "Mismatch Pass",
                "email": "test_mismatch@example.com",
                "password": "Password123!",
                "confirm_password": "DifferentPass!",
                "birth_date": "1990-01-01",
                "gender": "MALE",
                "service_class": "CLASS_3",
            },
        )
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertIn("Konfirmasi kata sandi tidak cocok", res_mismatch.get_data(as_text=True))

    # ---------------------------------------------------------
    # 36. TEST DATE / GENDER / SERVICE CLASS
    # ---------------------------------------------------------
    def test_date_gender_service_class_validation(self):
        # Future birth date
        future_date = (date.today() + timedelta(days=10)).strftime("%Y-%m-%d")
        csrf = self.get_csrf_token("/register")
        res = self.client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "Future Person",
                "email": "test_future@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "birth_date": future_date,
                "gender": "MALE",
                "service_class": "CLASS_1",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Tanggal lahir tidak boleh di masa depan", res.get_data(as_text=True))

        # Invalid gender
        csrf = self.get_csrf_token("/register")
        res = self.client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "Invalid Gender",
                "email": "test_invgender@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "birth_date": "1995-01-01",
                "gender": "UNKNOWN_GENDER",
                "service_class": "CLASS_1",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Not a valid choice", res.get_data(as_text=True))

        # Invalid service class
        csrf = self.get_csrf_token("/register")
        res = self.client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "name": "Invalid Class",
                "email": "test_invclass@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "birth_date": "1995-01-01",
                "gender": "MALE",
                "service_class": "VIP_CLASS",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Not a valid choice", res.get_data(as_text=True))

    # ---------------------------------------------------------
    # 37. TEST PRIVILEGE ESCALATION
    # ---------------------------------------------------------
    def test_privilege_escalation_attempt(self):
        csrf = self.get_csrf_token("/register")
        email = "test_hacker@example.com"
        hack_data = {
            "csrf_token": csrf,
            "name": "Attacker",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
            "birth_date": "1990-01-01",
            "gender": "MALE",
            "service_class": "CLASS_1",
            "role": "admin",
            "participant_number": "HACK-999",
            "membership_status": "INACTIVE",
            "user_id": 9999,
        }
        res = self.client.post("/register", data=hack_data)
        self.assertEqual(res.status_code, 302)

        user = db.session.execute(select(User).filter_by(email=email)).scalar_one()
        self.assertEqual(user.role, "citizen")
        self.assertNotEqual(user.id, 9999)

        participant = user.participant
        self.assertNotEqual(participant.participant_number, "HACK-999")
        self.assertTrue(participant.participant_number.startswith("SW-"))
        self.assertEqual(participant.membership_status, "ACTIVE")

    # ---------------------------------------------------------
    # 38. TEST PARTICIPANT NUMBER GENERATOR
    # ---------------------------------------------------------
    def test_participant_number_generator(self):
        generated = set()
        current_year = date.today().year
        for _ in range(50):
            num = generate_participant_number()
            self.assertRegex(num, rf"^SW-{current_year}-[A-Z0-9]{{8}}$")
            self.assertNotIn(num, generated)
            generated.add(num)

    # ---------------------------------------------------------
    # 39. TEST LOGIN & 40. TEST LOGOUT
    # ---------------------------------------------------------
    def test_login_logout_flow(self):
        # Create a test citizen
        user, _ = register_citizen(
            name="Login Citizen",
            email="test_login_citizen@example.com",
            password="Password123!",
            birth_date=date(1991, 1, 1),
            gender="FEMALE",
            service_class="CLASS_2",
        )

        # Create a test admin
        admin = User(
            name="Admin System",
            email="test_login_admin@example.com",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()

        # Inactive user
        inactive = User(
            name="Inactive User",
            email="test_login_inactive@example.com",
            role="citizen",
            is_active=False,
        )
        inactive.set_password("Password123!")
        db.session.add(inactive)
        db.session.commit()

        # Wrong password
        csrf = self.get_csrf_token("/login")
        res = self.client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "test_login_citizen@example.com",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("Email atau password salah", res.get_data(as_text=True))

        # Unknown email
        csrf = self.get_csrf_token("/login")
        res = self.client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "unknown_email@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(res.status_code, 401)
        self.assertIn("Email atau password salah", res.get_data(as_text=True))

        # Inactive user login
        csrf = self.get_csrf_token("/login")
        res = self.client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "test_login_inactive@example.com",
                "password": "Password123!",
            },
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("Akun Anda dinonaktifkan", res.get_data(as_text=True))

        # Valid citizen login -> redirect /citizen/dashboard
        csrf = self.get_csrf_token("/login")
        res = self.client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "test_login_citizen@example.com",
                "password": "Password123!",
            },
            follow_redirects=False,
        )
        self.assertEqual(res.status_code, 302)
        self.assertIn("/citizen/dashboard", res.headers["Location"])

        # Access citizen dashboard
        res_dash = self.client.get("/citizen/dashboard")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn("Login Citizen", res_dash.get_data(as_text=True))

        # Logout via POST /logout
        csrf_logout = self.get_csrf_token("/citizen/dashboard")
        res_logout = self.client.post("/logout", data={"csrf_token": csrf_logout}, follow_redirects=False)
        self.assertEqual(res_logout.status_code, 302)

        # Ensure protected dashboard redirects to login after logout
        res_after = self.client.get("/citizen/dashboard", follow_redirects=False)
        self.assertEqual(res_after.status_code, 302)
        self.assertIn("/login", res_after.headers["Location"])

        # Valid admin login -> redirect /admin/dashboard
        csrf = self.get_csrf_token("/login")
        res_admin = self.client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "email": "test_login_admin@example.com",
                "password": "AdminPass123!",
            },
            follow_redirects=False,
        )
        self.assertEqual(res_admin.status_code, 302)
        self.assertIn("/admin/dashboard", res_admin.headers["Location"])

    # ---------------------------------------------------------
    # 41. TEST ROLE MATRIX
    # ---------------------------------------------------------
    def test_role_matrix(self):
        # 1. Unauthenticated checks
        res = self.client.get("/citizen/dashboard", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        res = self.client.get("/admin/dashboard", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers["Location"])

        # 2. Citizen user role checks
        citizen_user, _ = register_citizen(
            name="Matrix Citizen",
            email="test_matrix_citizen@example.com",
            password="Password123!",
            birth_date=date(1994, 2, 2),
            gender="MALE",
            service_class="CLASS_1",
        )
        csrf = self.get_csrf_token("/login")
        self.client.post(
            "/login",
            data={"csrf_token": csrf, "email": citizen_user.email, "password": "Password123!"},
        )

        # Citizen can access citizen pages
        self.assertEqual(self.client.get("/citizen/dashboard").status_code, 200)
        self.assertEqual(self.client.get("/citizen/profile").status_code, 200)
        self.assertEqual(self.client.get("/citizen/card").status_code, 200)

        # Citizen CANNOT access admin dashboard -> 403
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 403)

        # Logout citizen
        csrf = self.get_csrf_token("/citizen/dashboard")
        self.client.post("/logout", data={"csrf_token": csrf})

        # 3. Admin user role checks
        admin_user = User(
            name="Matrix Admin",
            email="test_matrix_admin@example.com",
            role="admin",
            is_active=True,
        )
        admin_user.set_password("AdminPass123!")
        db.session.add(admin_user)
        db.session.commit()

        csrf = self.get_csrf_token("/login")
        self.client.post(
            "/login",
            data={"csrf_token": csrf, "email": admin_user.email, "password": "AdminPass123!"},
        )

        # Admin can access admin dashboard
        self.assertEqual(self.client.get("/admin/dashboard").status_code, 200)

        # Admin CANNOT access citizen pages -> 403
        self.assertEqual(self.client.get("/citizen/dashboard").status_code, 403)
        self.assertEqual(self.client.get("/citizen/profile").status_code, 403)
        self.assertEqual(self.client.get("/citizen/card").status_code, 403)

    # ---------------------------------------------------------
    # 42. TEST DATA PRIVACY
    # ---------------------------------------------------------
    def test_data_privacy(self):
        citizen_user, participant = register_citizen(
            name="Privacy Tester",
            email="test_privacy@example.com",
            password="SecurePassword999!",
            birth_date=date(1993, 3, 3),
            gender="FEMALE",
            service_class="CLASS_2",
        )
        csrf = self.get_csrf_token("/login")
        self.client.post(
            "/login",
            data={"csrf_token": csrf, "email": citizen_user.email, "password": "SecurePassword999!"},
        )

        pages = [
            self.client.get("/citizen/dashboard").get_data(as_text=True),
            self.client.get("/citizen/profile").get_data(as_text=True),
            self.client.get("/citizen/card").get_data(as_text=True),
        ]

        for content in pages:
            self.assertNotIn(citizen_user.password_hash, content)
            self.assertNotIn("SecurePassword999!", content)
            self.assertNotIn("DATABASE_URL", content)
            self.assertNotIn("SECRET_KEY", content)
            self.assertNotIn("mysql+pymysql", content)

    # ---------------------------------------------------------
    # 43. DATABASE VERIFICATION (RELATIONSHIPS)
    # ---------------------------------------------------------
    def test_database_relationships(self):
        citizen, participant = register_citizen(
            name="Rel Citizen",
            email="test_rel_citizen@example.com",
            password="Password123!",
            birth_date=date(1990, 1, 1),
            gender="MALE",
            service_class="CLASS_3",
        )
        # 1-to-1 relationship
        self.assertEqual(citizen.participant.id, participant.id)
        self.assertEqual(participant.user.id, citizen.id)

        admin = User(name="Rel Admin", email="test_rel_admin@example.com", role="admin")
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        # Admin has no participant
        self.assertIsNone(admin.participant)

    # ---------------------------------------------------------
    # 45. DATABASE TRANSACTION ROLLBACK
    # ---------------------------------------------------------
    def test_registration_transaction_rollback(self):
        # Trigger an exception by passing an invalid gender to DB
        email = "test_rollback@example.com"
        with self.assertRaises(Exception):
            register_citizen(
                name="Rollback User",
                email=email,
                password="Password123!",
                birth_date=date(1990, 1, 1),
                gender="INVALID_LONG_GENDER_STRING_EXCEEDING_COLUMN_LIMIT",
                service_class="CLASS_1",
            )

        # Verify no orphan User was committed
        user = db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none()
        self.assertIsNone(user)

    # ---------------------------------------------------------
    # CLI TEST
    # ---------------------------------------------------------
    def test_cli_create_admin(self):
        from unittest.mock import patch
        email = "test_cli_admin@example.com"
        with patch("app.cli.getpass.getpass", side_effect=["AdminPassword123!", "AdminPassword123!"]):
            res = self.runner.invoke(
                args=["create-admin"],
                input=f"CLI Admin\n{email}\n",
            )
        self.assertEqual(res.exit_code, 0)
        self.assertIn("berhasil dibuat", res.output)

        admin = db.session.execute(select(User).filter_by(email=email)).scalar_one_or_none()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, "admin")
        self.assertIsNone(admin.participant)
        self.assertTrue(admin.check_password("AdminPassword123!"))


if __name__ == "__main__":
    unittest.main()
