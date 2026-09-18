import tests
import re
import unittest
from datetime import date
from sqlalchemy import select
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.complaint import Complaint
from app.services.participant_service import register_citizen
from app.services.complaint_service import (
    STATUS_OPEN,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    STATUS_REJECTED,
    VALID_COMPLAINT_STATUSES,
    COMPLAINT_STATUS_LABELS,
    generate_ticket_number,
    validate_subject,
    validate_message,
    validate_admin_response,
    validate_transition,
    create_complaint,
    start_complaint_processing,
    resolve_complaint,
    reject_complaint,
    transition_complaint,
)


class Stage7TestCase(unittest.TestCase):
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

        # Clean up complaints for test_s7_ users
        test_complaints = db.session.execute(
            select(Complaint)
            .join(Complaint.user)
            .filter(User.email.like("test_s7_%@example.com"))
        ).scalars().all()
        for c in test_complaints:
            db.session.delete(c)

        # Clean up participants and users
        test_users = db.session.execute(
            select(User).filter(User.email.like("test_s7_%@example.com"))
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

    def create_citizen(self, tag):
        user, participant = register_citizen(
            name=f"Citizen S7 {tag}",
            email=f"test_s7_{tag}@example.com",
            password="Password123!",
            birth_date=date(1992, 5, 10),
            gender="FEMALE",
            service_class="CLASS_2",
        )
        return user, participant

    def create_admin(self, tag):
        admin = User(
            name=f"Admin S7 {tag}",
            email=f"test_s7_{tag}@example.com",
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
    # 1. TEST TICKET GENERATOR
    # -------------------------------------------------------------
    def test_01_ticket_generator_format_and_uniqueness(self):
        user, _ = self.create_citizen("ticket")

        ticket_pattern = re.compile(r"^SWT-\d{8}-[A-Z0-9]{8}$")
        tickets = set()

        for _ in range(20):
            ticket = generate_ticket_number()
            self.assertTrue(
                ticket_pattern.match(ticket),
                f"Ticket number '{ticket}' does not match format SWT-YYYYMMDD-XXXXXXXX",
            )
            # Must not contain user id, email, or sensitive data
            # A one-digit id can naturally occur in the date or random suffix.
            # Verify independence from identity via deterministic entropy below.
            self.assertNotIn("test_s7", ticket)
            self.assertNotIn("example", ticket)
            self.assertNotIn(ticket, tickets, "Generated ticket collision occurred")
            tickets.add(ticket)
        from unittest.mock import patch
        with patch("app.services.complaint_service.secrets.choice", return_value="Z"):
            expected = "SWT-20260101-ZZZZZZZZ"
            self.assertEqual(generate_ticket_number(date(2026, 1, 1)), expected)
            user.name = "Different identity"
            self.assertEqual(generate_ticket_number(date(2026, 1, 1)), expected)

    # -------------------------------------------------------------
    # 2. TEST CREATE COMPLAINT & MASS ASSIGNMENT PROTECTION
    # -------------------------------------------------------------
    def test_02_create_complaint_service_and_mass_assignment(self):
        user, _ = self.create_citizen("create_svc")
        admin = self.create_admin("adm_target")

        complaint = create_complaint(
            user_id=user.id,
            subject="  Masalah antrean pendaftaran online  ",
            message="  Layanan pendaftaran faskes mengalami kendala koneksi saat jam kerja pagi hari.  ",
        )

        self.assertIsNotNone(complaint.id)
        self.assertEqual(complaint.user_id, user.id)
        self.assertTrue(complaint.ticket_number.startswith("SWT-"))
        self.assertEqual(complaint.subject, "Masalah antrean pendaftaran online")
        self.assertEqual(
            complaint.message,
            "Layanan pendaftaran faskes mengalami kendala koneksi saat jam kerja pagi hari.",
        )
        self.assertEqual(complaint.status, STATUS_OPEN)
        self.assertIsNone(complaint.admin_response)

    def test_03_create_complaint_route_success_and_mass_assignment(self):
        user, _ = self.create_citizen("create_rt")
        admin = self.create_admin("adm_rt")

        self.login(user.email, "Password123!")

        csrf_token = self.get_csrf_token("/citizen/complaints/create")

        # Client tries to inject ticket_number, user_id, status, and admin_response (Mass Assignment Attempt)
        res = self.client.post(
            "/citizen/complaints/create",
            data={
                "csrf_token": csrf_token,
                "subject": "Keluhan verifikasi berkas keluarga",
                "message": "Data anggota keluarga kami belum terverifikasi setelah lebih dari 3 hari kerja.",
                "ticket_number": "SWT-HACKED-99999999",
                "user_id": admin.id,
                "status": "RESOLVED",
                "admin_response": "Palsu selesai langsung",
            },
            follow_redirects=True,
        )

        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Pengaduan berhasil dikirim.", html)

        # Check in database
        complaint = db.session.execute(
            select(Complaint).filter_by(user_id=user.id)
        ).scalar_one_or_none()

        self.assertIsNotNone(complaint)
        self.assertEqual(complaint.user_id, user.id, "user_id must be current_user.id")
        self.assertNotEqual(complaint.user_id, admin.id)
        self.assertNotEqual(complaint.ticket_number, "SWT-HACKED-99999999")
        self.assertTrue(complaint.ticket_number.startswith("SWT-"))
        self.assertEqual(complaint.status, STATUS_OPEN, "Status must always be OPEN initially")
        self.assertIsNone(complaint.admin_response, "admin_response must be NULL")

    # -------------------------------------------------------------
    # 3. TEST VALIDATION
    # -------------------------------------------------------------
    def test_04_create_validation_subject_and_message(self):
        user, _ = self.create_citizen("validations")
        self.login(user.email, "Password123!")

        url = "/citizen/complaints/create"
        csrf = self.get_csrf_token(url)

        # Subject empty
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "", "message": "Pesan keluhan valid 12345"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Judul pengaduan wajib diisi", res.get_data(as_text=True))

        # Subject < 5 chars
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "Hai", "message": "Pesan keluhan valid 12345"},
        )
        self.assertEqual(res.status_code, 200)

        # Subject whitespace only
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "     ", "message": "Pesan keluhan valid 12345"},
        )
        self.assertEqual(res.status_code, 200)

        # Message empty
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "Judul Pengaduan Valid", "message": ""},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Isi pengaduan wajib diisi", res.get_data(as_text=True))

        # Message < 10 chars
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "Judul Pengaduan Valid", "message": "Pendek"},
        )
        self.assertEqual(res.status_code, 200)

        # Message whitespace only
        res = self.client.post(
            url,
            data={"csrf_token": csrf, "subject": "Judul Pengaduan Valid", "message": "          "},
        )
        self.assertEqual(res.status_code, 200)

        # Service level validation raises ValueError
        with self.assertRaises(ValueError):
            validate_subject("   ")
        with self.assertRaises(ValueError):
            validate_subject("1234")
        with self.assertRaises(ValueError):
            validate_message("   ")
        with self.assertRaises(ValueError):
            validate_message("123456789")

    # -------------------------------------------------------------
    # 4. TEST OWNERSHIP & CITIZEN LIST ISOLATION
    # -------------------------------------------------------------
    def test_05_ownership_and_list_isolation(self):
        user_a, _ = self.create_citizen("user_a")
        user_b, _ = self.create_citizen("user_b")

        comp_a1 = create_complaint(user_a.id, "Pengaduan A1 Warga A", "Uraian lengkap keluhan warga A1.")
        comp_a2 = create_complaint(user_a.id, "Pengaduan A2 Warga A", "Uraian lengkap keluhan warga A2.")
        comp_b1 = create_complaint(user_b.id, "Pengaduan B1 Warga B", "Uraian lengkap keluhan warga B1.")

        # Citizen B tries to access Citizen A's complaint -> MUST return 404
        self.login(user_b.email, "Password123!")
        res = self.client.get(f"/citizen/complaints/{comp_a1.id}")
        self.assertEqual(res.status_code, 404)

        # Citizen B checks list -> Only sees comp_b1
        res = self.client.get("/citizen/complaints")
        self.assertEqual(res.status_code, 200)
        html_b = res.get_data(as_text=True)
        self.assertIn(comp_b1.ticket_number, html_b)
        self.assertNotIn(comp_a1.ticket_number, html_b)
        self.assertNotIn(comp_a2.ticket_number, html_b)

        # Logout & login as Citizen A
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token("/citizen/complaints")})
        self.login(user_a.email, "Password123!")

        res = self.client.get(f"/citizen/complaints/{comp_a1.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(comp_a1.ticket_number, res.get_data(as_text=True))

        res = self.client.get("/citizen/complaints")
        html_a = res.get_data(as_text=True)
        self.assertIn(comp_a1.ticket_number, html_a)
        self.assertIn(comp_a2.ticket_number, html_a)
        self.assertNotIn(comp_b1.ticket_number, html_a)

    # -------------------------------------------------------------
    # 5. TEST ADMIN ACCESS & ROLE PROTECTION
    # -------------------------------------------------------------
    def test_06_admin_list_and_role_protection(self):
        user, _ = self.create_citizen("user_role")
        admin = self.create_admin("admin_role")

        # Unauthenticated access redirects to login
        res = self.client.get("/admin/complaints")
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))

        # Citizen accessing admin complaints -> 403 Forbidden
        self.login(user.email, "Password123!")
        res = self.client.get("/admin/complaints")
        self.assertEqual(res.status_code, 403)

        # Logout citizen, login admin -> 200 OK
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token("/citizen/dashboard")})
        self.login(admin.email, "AdminPass123!")
        res = self.client.get("/admin/complaints")
        self.assertEqual(res.status_code, 200)

    # -------------------------------------------------------------
    # 6. TEST WORKFLOW: OPEN -> IN_PROGRESS
    # -------------------------------------------------------------
    def test_07_workflow_open_to_in_progress(self):
        user, _ = self.create_citizen("flow_start")
        admin = self.create_admin("flow_start_adm")
        comp = create_complaint(user.id, "Pengaduan Proses Uji", "Uraian keluhan warga untuk diuji alur prosesnya.")

        self.assertEqual(comp.status, STATUS_OPEN)

        self.login(admin.email, "AdminPass123!")
        csrf = self.get_csrf_token(f"/admin/complaints/{comp.id}")

        # Admin starts processing
        res = self.client.post(
            f"/admin/complaints/{comp.id}/start",
            data={"csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Pengaduan mulai diproses.", res.get_data(as_text=True))

        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_IN_PROGRESS)

        # Starting again should fail
        csrf2 = self.get_csrf_token(f"/admin/complaints/{comp.id}")
        res2 = self.client.post(
            f"/admin/complaints/{comp.id}/start",
            data={"csrf_token": csrf2},
            follow_redirects=True,
        )
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Tidak dapat memulai proses pengaduan", res2.get_data(as_text=True))
        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_IN_PROGRESS)

    # -------------------------------------------------------------
    # 7. TEST DIRECT OPEN -> RESOLVED IS PROHIBITED
    # -------------------------------------------------------------
    def test_08_direct_open_to_resolved_prohibited(self):
        user, _ = self.create_citizen("direct_res")
        admin = self.create_admin("direct_res_adm")
        comp = create_complaint(user.id, "Pengaduan Direct Test", "Uraian keluhan warga untuk uji direct resolve.")

        self.login(admin.email, "AdminPass123!")
        csrf = self.get_csrf_token(f"/admin/complaints/{comp.id}")

        res = self.client.post(
            f"/admin/complaints/{comp.id}/resolve",
            data={
                "csrf_token": csrf,
                "admin_response": "Tanggapan penyelesaian langsung tanpa proses.",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hanya pengaduan dengan status Sedang Diproses", res.get_data(as_text=True))

        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_OPEN, "Status must remain OPEN")
        self.assertIsNone(comp.admin_response)

    # -------------------------------------------------------------
    # 8. TEST WORKFLOW: IN_PROGRESS -> RESOLVED
    # -------------------------------------------------------------
    def test_09_workflow_in_progress_to_resolved_and_validation(self):
        user, _ = self.create_citizen("flow_res")
        admin = self.create_admin("flow_res_adm")
        comp = create_complaint(user.id, "Pengaduan Resolve Valid", "Keluhan kepesertaan yang akan diselesaikan admin.")
        start_complaint_processing(comp)
        self.assertEqual(comp.status, STATUS_IN_PROGRESS)

        self.login(admin.email, "AdminPass123!")
        url = f"/admin/complaints/{comp.id}/resolve"
        csrf = self.get_csrf_token(f"/admin/complaints/{comp.id}")

        # Invalid: empty response
        res = self.client.post(url, data={"csrf_token": csrf, "admin_response": ""}, follow_redirects=True)
        self.assertIn("Tanggapan admin wajib diisi", res.get_data(as_text=True))
        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_IN_PROGRESS)

        # Invalid: response < 10 chars
        csrf = self.get_csrf_token(f"/admin/complaints/{comp.id}")
        res = self.client.post(url, data={"csrf_token": csrf, "admin_response": "Pendek"}, follow_redirects=True)
        self.assertIn("minimal 10 karakter", res.get_data(as_text=True))
        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_IN_PROGRESS)

        # Valid: resolution response >= 10 chars
        csrf = self.get_csrf_token(f"/admin/complaints/{comp.id}")
        res = self.client.post(
            url,
            data={
                "csrf_token": csrf,
                "admin_response": "Permasalahan verifikasi telah diselesaikan oleh tim teknis SehatWarga.",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Pengaduan berhasil diselesaikan.", res.get_data(as_text=True))

        db.session.refresh(comp)
        self.assertEqual(comp.status, STATUS_RESOLVED)
        self.assertEqual(
            comp.admin_response,
            "Permasalahan verifikasi telah diselesaikan oleh tim teknis SehatWarga.",
        )

    # -------------------------------------------------------------
    # 9. TEST WORKFLOW: OPEN -> REJECTED & IN_PROGRESS -> REJECTED
    # -------------------------------------------------------------
    def test_10_workflow_reject_from_open_and_in_progress(self):
        user, _ = self.create_citizen("flow_rej")
        admin = self.create_admin("flow_rej_adm")

        # 1. Reject from OPEN
        comp1 = create_complaint(user.id, "Pengaduan Reject Open", "Keluhan yang ditolak langsung saat status OPEN.")
        self.login(admin.email, "AdminPass123!")

        csrf = self.get_csrf_token(f"/admin/complaints/{comp1.id}")
        res = self.client.post(
            f"/admin/complaints/{comp1.id}/reject",
            data={
                "csrf_token": csrf,
                "admin_response": "Pengaduan di luar cakupan administratif pelayanan SehatWarga.",
            },
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Pengaduan telah ditolak.", res.get_data(as_text=True))
        db.session.refresh(comp1)
        self.assertEqual(comp1.status, STATUS_REJECTED)
        self.assertIn("di luar cakupan", comp1.admin_response)

        # 2. Reject from IN_PROGRESS
        comp2 = create_complaint(user.id, "Pengaduan Reject Progress", "Keluhan yang ditolak saat status IN_PROGRESS.")
        start_complaint_processing(comp2)
        self.assertEqual(comp2.status, STATUS_IN_PROGRESS)

        csrf2 = self.get_csrf_token(f"/admin/complaints/{comp2.id}")
        res2 = self.client.post(
            f"/admin/complaints/{comp2.id}/reject",
            data={
                "csrf_token": csrf2,
                "admin_response": "Setelah dilakukan pemeriksaan data, pengaduan tidak memenuhi kriteria verifikasi.",
            },
            follow_redirects=True,
        )
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Pengaduan telah ditolak.", res2.get_data(as_text=True))
        db.session.refresh(comp2)
        self.assertEqual(comp2.status, STATUS_REJECTED)

    # -------------------------------------------------------------
    # 10. TEST TERMINAL STATES PROTECTION
    # -------------------------------------------------------------
    def test_11_terminal_states_cannot_be_reprocessed(self):
        user, _ = self.create_citizen("term")
        admin = self.create_admin("term_adm")

        # Create RESOLVED complaint
        comp_res = create_complaint(user.id, "Keluhan Selesai Terminal", "Pengaduan yang telah diselesaikan.")
        start_complaint_processing(comp_res)
        resolve_complaint(comp_res, "Telah selesai ditindaklanjuti secara resmi.")
        self.assertEqual(comp_res.status, STATUS_RESOLVED)

        # Create REJECTED complaint
        comp_rej = create_complaint(user.id, "Keluhan Ditolak Terminal", "Pengaduan yang telah ditolak.")
        reject_complaint(comp_rej, "Telah ditolak karena bukan kewenangan.")
        self.assertEqual(comp_rej.status, STATUS_REJECTED)

        self.login(admin.email, "AdminPass123!")

        # 1. On RESOLVED complaint: start, resolve, reject must fail
        csrf = self.get_csrf_token(f"/admin/complaints/{comp_res.id}")
        res = self.client.post(f"/admin/complaints/{comp_res.id}/start", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertIn("Tidak dapat memulai proses", res.get_data(as_text=True))

        csrf = self.get_csrf_token(f"/admin/complaints/{comp_res.id}")
        res = self.client.post(
            f"/admin/complaints/{comp_res.id}/resolve",
            data={"csrf_token": csrf, "admin_response": "Coba resolve ulang lagi"},
            follow_redirects=True,
        )
        self.assertIn("Hanya pengaduan dengan status Sedang Diproses", res.get_data(as_text=True))

        csrf = self.get_csrf_token(f"/admin/complaints/{comp_res.id}")
        res = self.client.post(
            f"/admin/complaints/{comp_res.id}/reject",
            data={"csrf_token": csrf, "admin_response": "Coba tolak pengaduan yang sudah selesai"},
            follow_redirects=True,
        )
        self.assertIn("tidak dapat ditolak", res.get_data(as_text=True))

        # 2. On REJECTED complaint: start, resolve, reject must fail
        csrf = self.get_csrf_token(f"/admin/complaints/{comp_rej.id}")
        res = self.client.post(f"/admin/complaints/{comp_rej.id}/start", data={"csrf_token": csrf}, follow_redirects=True)
        self.assertIn("Tidak dapat memulai proses", res.get_data(as_text=True))

        csrf = self.get_csrf_token(f"/admin/complaints/{comp_rej.id}")
        res = self.client.post(
            f"/admin/complaints/{comp_rej.id}/resolve",
            data={"csrf_token": csrf, "admin_response": "Coba resolve pengaduan yang ditolak"},
            follow_redirects=True,
        )
        self.assertIn("Hanya pengaduan dengan status Sedang Diproses", res.get_data(as_text=True))

        # Service level transitions also raise ValueError
        with self.assertRaises(ValueError):
            start_complaint_processing(comp_res)
        with self.assertRaises(ValueError):
            resolve_complaint(comp_res, "Valid response string but invalid state")
        with self.assertRaises(ValueError):
            reject_complaint(comp_res, "Valid reason string but invalid state")
        with self.assertRaises(ValueError):
            start_complaint_processing(comp_rej)
        with self.assertRaises(ValueError):
            resolve_complaint(comp_rej, "Valid response string but invalid state")
        with self.assertRaises(ValueError):
            reject_complaint(comp_rej, "Valid reason string but invalid state")

    # -------------------------------------------------------------
    # 11. TEST XSS PROTECTION
    # -------------------------------------------------------------
    def test_12_xss_protection_in_citizen_and_admin_views(self):
        user, _ = self.create_citizen("xss")
        admin = self.create_admin("xss_adm")

        xss_payload = "<script>alert('xss_attack')</script>"
        comp = create_complaint(
            user_id=user.id,
            subject=f"Uji XSS {xss_payload}",
            message=f"Pesan berisi tag berbahaya: {xss_payload} mohon diperiksa.",
        )
        start_complaint_processing(comp)
        resolve_complaint(comp, f"Tanggapan dengan tag XSS {xss_payload} harus diescape.")

        # Citizen view
        self.login(user.email, "Password123!")
        res = self.client.get(f"/citizen/complaints/{comp.id}")
        html = res.get_data(as_text=True)
        self.assertNotIn("<script>alert('xss_attack')</script>", html)
        self.assertIn("&lt;script&gt;alert(&#39;xss_attack&#39;)&lt;/script&gt;", html)

        # Admin view
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token(f"/citizen/complaints/{comp.id}")})
        self.login(admin.email, "AdminPass123!")
        res_adm = self.client.get(f"/admin/complaints/{comp.id}")
        html_adm = res_adm.get_data(as_text=True)
        self.assertNotIn("<script>alert('xss_attack')</script>", html_adm)
        self.assertIn("&lt;script&gt;alert(&#39;xss_attack&#39;)&lt;/script&gt;", html_adm)

    # -------------------------------------------------------------
    # 12. TEST CSRF PROTECTION
    # -------------------------------------------------------------
    def test_13_csrf_protection_on_all_action_routes(self):
        user, _ = self.create_citizen("csrf")
        admin = self.create_admin("csrf_adm")
        comp = create_complaint(user.id, "Pengaduan Uji CSRF", "Pengaduan untuk pengujian proteksi CSRF token.")

        # 1. Citizen create without CSRF
        self.login(user.email, "Password123!")
        res = self.client.post(
            "/citizen/complaints/create",
            data={"subject": "Judul Tanpa CSRF", "message": "Pesan tanpa CSRF token yang valid."},
        )
        self.assertEqual(res.status_code, 400)

        # 2. Admin actions without CSRF
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token("/citizen/dashboard")})
        self.login(admin.email, "AdminPass123!")

        res = self.client.post(f"/admin/complaints/{comp.id}/start", data={})
        self.assertEqual(res.status_code, 400)

        res = self.client.post(f"/admin/complaints/{comp.id}/resolve", data={"admin_response": "Tanggapan valid tapi tanpa csrf"})
        self.assertEqual(res.status_code, 400)

        res = self.client.post(f"/admin/complaints/{comp.id}/reject", data={"admin_response": "Alasan valid tapi tanpa csrf"})
        self.assertEqual(res.status_code, 400)

    # -------------------------------------------------------------
    # 13. TEST PRIVACY OUTPUT
    # -------------------------------------------------------------
    def test_14_privacy_output_and_credential_protection(self):
        user, _ = self.create_citizen("privacy")
        admin = self.create_admin("privacy_adm")
        comp = create_complaint(user.id, "Pengaduan Uji Privasi", "Pengaduan untuk pengujian privasi dan credential leaks.")

        # Citizen view
        self.login(user.email, "Password123!")
        res = self.client.get(f"/citizen/complaints/{comp.id}")
        html_cit = res.get_data(as_text=True)
        self.assertNotIn("password_hash", html_cit)
        self.assertNotIn("pbkdf2:sha256", html_cit)
        self.assertNotIn("SECRET_KEY", html_cit)
        self.assertNotIn("DATABASE_URL", html_cit)
        self.assertNotIn("mysql://", html_cit)

        # Admin view
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token(f"/citizen/complaints/{comp.id}")})
        self.login(admin.email, "AdminPass123!")
        res_adm = self.client.get(f"/admin/complaints/{comp.id}")
        html_adm = res_adm.get_data(as_text=True)
        self.assertNotIn("password_hash", html_adm)
        self.assertNotIn("pbkdf2:sha256", html_adm)
        self.assertNotIn("SECRET_KEY", html_adm)
        self.assertNotIn("DATABASE_URL", html_adm)
        self.assertNotIn("mysql://", html_adm)

    # -------------------------------------------------------------
    # 14. TEST SEARCH, FILTER, AND PAGINATION
    # -------------------------------------------------------------
    def test_15_search_filter_and_pagination(self):
        user, _ = self.create_citizen("search_pg")
        admin = self.create_admin("search_adm")

        complaints = []
        for i in range(12):
            c = create_complaint(
                user_id=user.id,
                subject=f"Pengaduan Subjek Nomor {i:02d}",
                message=f"Pesan komplain terperinci nomor {i:02d} untuk pengujian pagination dan filter.",
            )
            complaints.append(c)

        # Citizen list pagination
        self.login(user.email, "Password123!")

        # Page 1
        res1 = self.client.get("/citizen/complaints?page=1")
        self.assertEqual(res1.status_code, 200)
        html1 = res1.get_data(as_text=True)
        self.assertIn("Pengaduan Subjek Nomor 11", html1)

        # Page 2
        res2 = self.client.get("/citizen/complaints?page=2")
        self.assertEqual(res2.status_code, 200)
        html2 = res2.get_data(as_text=True)
        self.assertIn("Pengaduan Subjek Nomor 01", html2)

        # Search by ticket number
        first_ticket = complaints[0].ticket_number
        res_search = self.client.get(f"/citizen/complaints?q={first_ticket}")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(first_ticket, res_search.get_data(as_text=True))

        # Filter by status
        res_filter = self.client.get("/citizen/complaints?status=OPEN")
        self.assertEqual(res_filter.status_code, 200)
        self.assertIn("Pengaduan Subjek Nomor 11", res_filter.get_data(as_text=True))

        # Invalid search and status inputs must not crash (HTTP 500)
        res_invalid = self.client.get("/citizen/complaints?status=INVALID_STATUS&page=-5&q=%27%20OR%201=1--")
        self.assertEqual(res_invalid.status_code, 200)

        # Admin search and filter
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token("/citizen/complaints")})
        self.login(admin.email, "AdminPass123!")

        # Admin search by citizen name (page 1 will contain the most recent complaints)
        res_adm_q = self.client.get(f"/admin/complaints?q={user.name}")
        self.assertEqual(res_adm_q.status_code, 200)
        self.assertIn(complaints[-1].ticket_number, res_adm_q.get_data(as_text=True))

        # Admin search by specific ticket number
        res_adm_ticket = self.client.get(f"/admin/complaints?q={first_ticket}")
        self.assertEqual(res_adm_ticket.status_code, 200)
        self.assertIn(first_ticket, res_adm_ticket.get_data(as_text=True))

        res_adm_invalid = self.client.get("/admin/complaints?status=NON_EXISTENT&page=999")
        self.assertEqual(res_adm_invalid.status_code, 200)

    # -------------------------------------------------------------
    # 15. TEST DASHBOARDS INTEGRATION
    # -------------------------------------------------------------
    def test_16_dashboards_updated_with_complaint_stats(self):
        user, _ = self.create_citizen("dash")
        admin = self.create_admin("dash_adm")

        # Citizen creates a complaint
        comp = create_complaint(user.id, "Pengaduan Dashboard", "Keluhan untuk memverifikasi counter di dashboard.")

        # Citizen dashboard
        self.login(user.email, "Password123!")
        res_cit = self.client.get("/citizen/dashboard")
        self.assertEqual(res_cit.status_code, 200)
        html_cit = res_cit.get_data(as_text=True)
        self.assertIn("Total Pengaduan", html_cit)
        self.assertIn("Buat Pengaduan", html_cit)
        self.assertIn("Lihat Pengaduan", html_cit)

        # Admin dashboard
        self.client.post("/logout", data={"csrf_token": self.get_csrf_token("/citizen/dashboard")})
        self.login(admin.email, "AdminPass123!")
        res_adm = self.client.get("/admin/dashboard")
        self.assertEqual(res_adm.status_code, 200)
        html_adm = res_adm.get_data(as_text=True)
        self.assertIn("Pengaduan Layanan Masyarakat", html_adm)
        self.assertIn("Kelola Pengaduan", html_adm)
        self.assertIn("5 Pengaduan Layanan Terbaru", html_adm)
        self.assertIn(comp.ticket_number, html_adm)
