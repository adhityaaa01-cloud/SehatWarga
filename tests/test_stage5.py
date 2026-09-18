import tests
import re
import unittest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.family_member import FamilyMember
from app.models.health_facility import HealthFacility
from app.models.service_request import ServiceRequest
from app.models.service_history import ServiceHistory
from app.services.participant_service import register_citizen
from app.services.family_service import create_family_member
from app.services.service_request_service import (
    generate_request_number,
    create_service_request,
    transition_service_request_status,
)


class Stage5TestCase(unittest.TestCase):
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

        # Clean up test service histories and requests
        test_requests = db.session.execute(
            select(ServiceRequest).join(ServiceRequest.participant).join(Participant.user).filter(
                User.email.like("test_s5_%@example.com")
            )
        ).scalars().all()
        for r in test_requests:
            for h in r.histories:
                db.session.delete(h)
            db.session.delete(r)

        # Clean up test users and their participants + family members
        test_users = db.session.execute(
            select(User).filter(User.email.like("test_s5_%@example.com"))
        ).scalars().all()
        for u in test_users:
            if u.participant:
                for fm in u.participant.family_members:
                    db.session.delete(fm)
                db.session.delete(u.participant)
            db.session.delete(u)

        # Clean up test facilities
        test_facilities = db.session.execute(
            select(HealthFacility).filter(HealthFacility.facility_code.like("TEST-FAC-S5-%"))
        ).scalars().all()
        for f in test_facilities:
            db.session.delete(f)

        db.session.commit()
        self.ctx.pop()

    def get_csrf_token(self, url):
        res = self.client.get(url)
        html = res.get_data(as_text=True)
        match = re.search(r'name="csrf_token"[^>]*?value="([^"]+)"', html)
        self.assertTrue(match, f"CSRF token not found in {url}")
        return match.group(1)

    def create_citizen(self, tag, is_active_membership=True):
        user, participant = register_citizen(
            name=f"Citizen S5 {tag}",
            email=f"test_s5_{tag}@example.com",
            password="Password123!",
            birth_date=date(1990, 1, 1),
            gender="MALE",
            service_class="CLASS_1",
        )
        if not is_active_membership:
            participant.membership_status = "INACTIVE"
            db.session.commit()
        return user, participant

    def create_admin(self, tag):
        admin = User(
            name=f"Admin S5 {tag}",
            email=f"test_s5_{tag}@example.com",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        return admin

    def create_facility(self, tag, is_active=True):
        facility = HealthFacility(
            facility_code=f"TEST-FAC-S5-{tag.upper()}",
            name=f"Fasilitas Uji S5 {tag}",
            facility_type="PUSKESMAS",
            address="Jl. Sehat No. 123",
            city="Jakarta",
            phone="021-555000",
            latitude=Decimal("-6.2088000"),
            longitude=Decimal("106.8456000"),
            is_active=is_active,
        )
        db.session.add(facility)
        db.session.commit()
        return facility

    def login_user(self, email, password):
        csrf = self.get_csrf_token("/login")
        return self.client.post("/login", data={"csrf_token": csrf, "email": email, "password": password})

    def logout_user(self):
        csrf = self.get_csrf_token("/citizen/dashboard")
        return self.client.post("/logout", data={"csrf_token": csrf})

    # ---------------------------------------------------------
    # 1. REQUEST NUMBER GENERATOR FORMAT
    # ---------------------------------------------------------
    def test_request_number_format(self):
        req_num = generate_request_number()
        pattern = r"^SWR-\d{8}-[A-Z0-9]{8}$"
        self.assertTrue(re.match(pattern, req_num), f"Request number '{req_num}' did not match pattern '{pattern}'")

    # ---------------------------------------------------------
    # 2. CREATE SERVICE REQUEST FOR SELF (SERVICE LAYER)
    # ---------------------------------------------------------
    def test_create_service_request_self(self):
        user, participant = self.create_citizen("srv_self")
        facility = self.create_facility("self1")
        visit_date = date.today() + timedelta(days=2)

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=visit_date,
            complaint_summary="Pemeriksaan kesehatan rutin tekanan darah",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.assertIsNotNone(req.id)
        self.assertTrue(req.request_number.startswith("SWR-"))
        self.assertEqual(req.participant_id, participant.id)
        self.assertIsNone(req.family_member_id)
        self.assertEqual(req.status, "SUBMITTED")
        self.assertEqual(len(req.histories), 1)
        self.assertEqual(req.histories[0].status, "SUBMITTED")
        self.assertEqual(req.histories[0].changed_by, user.id)

    # ---------------------------------------------------------
    # 3. CREATE SERVICE REQUEST FOR ACTIVE FAMILY MEMBER
    # ---------------------------------------------------------
    def test_create_service_request_family(self):
        user, participant = self.create_citizen("srv_fam")
        facility = self.create_facility("fam1")
        member = create_family_member(
            participant_id=participant.id,
            full_name="Anak Kandung S5",
            relationship="CHILD",
            birth_date=date(2015, 5, 20),
            gender="FEMALE",
        )
        visit_date = date.today() + timedelta(days=3)

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="DENTAL",
            scheduled_date=visit_date,
            complaint_summary="Pemeriksaan gigi berlubang",
            beneficiary_type="FAMILY",
            family_member_id=member.id,
            user_id=user.id,
        )

        self.assertIsNotNone(req.id)
        self.assertEqual(req.family_member_id, member.id)
        self.assertEqual(req.family_member.full_name, "Anak Kandung S5")
        self.assertEqual(req.status, "SUBMITTED")

    # ---------------------------------------------------------
    # 4. REJECT CREATION FOR INACTIVE FAMILY MEMBER
    # ---------------------------------------------------------
    def test_reject_request_for_inactive_family_member(self):
        user, participant = self.create_citizen("srv_inact_fam")
        facility = self.create_facility("inact_fam")
        member = create_family_member(
            participant_id=participant.id,
            full_name="Anggota Nonaktif",
            relationship="SPOUSE",
            birth_date=date(1992, 4, 10),
            gender="FEMALE",
        )
        member.membership_status = "INACTIVE"
        db.session.commit()

        with self.assertRaises(ValueError) as ctx:
            create_service_request(
                participant=participant,
                health_facility_id=facility.id,
                service_type="GENERAL",
                scheduled_date=date.today() + timedelta(days=1),
                complaint_summary="Pemeriksaan umum",
                beneficiary_type="FAMILY",
                family_member_id=member.id,
                user_id=user.id,
            )
        self.assertIn("tidak aktif", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # 5. REJECT CREATION FOR ANOTHER CITIZEN'S FAMILY MEMBER
    # ---------------------------------------------------------
    def test_reject_request_for_foreign_family_member(self):
        user1, participant1 = self.create_citizen("cit1")
        user2, participant2 = self.create_citizen("cit2")
        facility = self.create_facility("foreign_fam")
        member_other = create_family_member(
            participant_id=participant2.id,
            full_name="Keluarga Orang Lain",
            relationship="CHILD",
            birth_date=date(2018, 1, 1),
            gender="MALE",
        )

        with self.assertRaises(ValueError) as ctx:
            create_service_request(
                participant=participant1,
                health_facility_id=facility.id,
                service_type="GENERAL",
                scheduled_date=date.today() + timedelta(days=1),
                complaint_summary="Pemeriksaan kesehatan",
                beneficiary_type="FAMILY",
                family_member_id=member_other.id,
                user_id=user1.id,
            )
        self.assertIn("tidak ditemukan atau bukan bagian", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # 6. REJECT CREATION FOR INACTIVE PARTICIPANT
    # ---------------------------------------------------------
    def test_reject_request_for_inactive_participant(self):
        user, participant = self.create_citizen("srv_inact_part", is_active_membership=False)
        facility = self.create_facility("inact_part")

        with self.assertRaises(ValueError) as ctx:
            create_service_request(
                participant=participant,
                health_facility_id=facility.id,
                service_type="GENERAL",
                scheduled_date=date.today() + timedelta(days=1),
                complaint_summary="Pemeriksaan umum",
                beneficiary_type="SELF",
                user_id=user.id,
            )
        self.assertIn("status kepesertaan tidak aktif", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # 7. REJECT CREATION FOR PAST SCHEDULED DATE
    # ---------------------------------------------------------
    def test_reject_request_for_past_date(self):
        user, participant = self.create_citizen("srv_past_date")
        facility = self.create_facility("past_date")

        with self.assertRaises(ValueError) as ctx:
            create_service_request(
                participant=participant,
                health_facility_id=facility.id,
                service_type="GENERAL",
                scheduled_date=date.today() - timedelta(days=1),
                complaint_summary="Pemeriksaan umum",
                beneficiary_type="SELF",
                user_id=user.id,
            )
        self.assertIn("masa lalu", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # 8. REJECT CREATION FOR INACTIVE HEALTH FACILITY
    # ---------------------------------------------------------
    def test_reject_request_for_inactive_facility(self):
        user, participant = self.create_citizen("srv_inact_fac")
        facility = self.create_facility("inact_fac", is_active=False)

        with self.assertRaises(ValueError) as ctx:
            create_service_request(
                participant=participant,
                health_facility_id=facility.id,
                service_type="GENERAL",
                scheduled_date=date.today() + timedelta(days=2),
                complaint_summary="Pemeriksaan umum",
                beneficiary_type="SELF",
                user_id=user.id,
            )
        self.assertIn("tidak aktif", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # 9. WORKFLOW STATUS STATE MACHINE (HAPPY PATH & TRANSITIONS)
    # SUBMITTED -> VERIFIED -> SCHEDULED -> COMPLETED
    # ---------------------------------------------------------
    def test_status_workflow_complete_lifecycle(self):
        user, participant = self.create_citizen("wf_user")
        admin = self.create_admin("wf_admin")
        facility = self.create_facility("wf_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="SPECIALIST",
            scheduled_date=date.today() + timedelta(days=5),
            complaint_summary="Konsultasi dokter spesialis penyakit dalam",
            beneficiary_type="SELF",
            user_id=user.id,
        )
        self.assertEqual(req.status, "SUBMITTED")

        # 1. SUBMITTED -> VERIFIED
        transition_service_request_status(
            service_request=req,
            target_status="VERIFIED",
            user_id=admin.id,
            note="Berkas peserta valid dan lengkap.",
        )
        self.assertEqual(req.status, "VERIFIED")
        self.assertEqual(len(req.histories), 2)
        self.assertEqual(req.histories[-1].status, "VERIFIED")

        # 2. VERIFIED -> SCHEDULED
        new_date = date.today() + timedelta(days=7)
        transition_service_request_status(
            service_request=req,
            target_status="SCHEDULED",
            user_id=admin.id,
            note="Jadwal ditetapkan di Poli Spesialis Lt. 3",
            new_scheduled_date=new_date,
        )
        self.assertEqual(req.status, "SCHEDULED")
        self.assertEqual(req.scheduled_date, new_date)
        self.assertEqual(len(req.histories), 3)
        self.assertEqual(req.histories[-1].status, "SCHEDULED")

        # 3. SCHEDULED -> COMPLETED
        transition_service_request_status(
            service_request=req,
            target_status="COMPLETED",
            user_id=admin.id,
            note="Pemeriksaan spesialis selesai dilaksanakan.",
        )
        self.assertEqual(req.status, "COMPLETED")
        self.assertEqual(len(req.histories), 4)
        self.assertEqual(req.histories[-1].status, "COMPLETED")

    # ---------------------------------------------------------
    # 10. WORKFLOW REJECTION (SUBMITTED -> REJECTED) WITH REASON
    # ---------------------------------------------------------
    def test_status_workflow_rejection_requires_reason(self):
        user, participant = self.create_citizen("wf_rej")
        admin = self.create_admin("wf_rej_adm")
        facility = self.create_facility("wf_rej_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="MATERNAL",
            scheduled_date=date.today() + timedelta(days=4),
            complaint_summary="Pemeriksaan kehamilan",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        # Rejection with empty reason must fail
        with self.assertRaises(ValueError) as ctx:
            transition_service_request_status(
                service_request=req,
                target_status="REJECTED",
                user_id=admin.id,
                note="   ",
            )
        self.assertIn("alasan penolakan", str(ctx.exception).lower())

        # Rejection with short reason must fail
        with self.assertRaises(ValueError) as ctx:
            transition_service_request_status(
                service_request=req,
                target_status="REJECTED",
                user_id=admin.id,
                note="bad",
            )
        self.assertIn("minimal 5 karakter", str(ctx.exception).lower())

        # Rejection with valid reason must succeed
        transition_service_request_status(
            service_request=req,
            target_status="REJECTED",
            user_id=admin.id,
            note="Persyaratan rujukan faskes tingkat 1 belum terpenuhi.",
        )
        self.assertEqual(req.status, "REJECTED")

    # ---------------------------------------------------------
    # 11. WORKFLOW DISALLOWED TRANSITIONS
    # ---------------------------------------------------------
    def test_workflow_disallowed_transitions(self):
        user, participant = self.create_citizen("wf_dis")
        admin = self.create_admin("wf_dis_adm")
        facility = self.create_facility("wf_dis_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan kesehatan",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        # SUBMITTED -> COMPLETED is illegal
        with self.assertRaises(ValueError):
            transition_service_request_status(
                service_request=req,
                target_status="COMPLETED",
                user_id=admin.id,
                note="Langsung selesai",
            )

        # Cancel request
        transition_service_request_status(
            service_request=req,
            target_status="CANCELLED",
            user_id=user.id,
            note="Dibatalkan sendiri oleh peserta",
        )
        self.assertEqual(req.status, "CANCELLED")

        # CANCELLED -> VERIFIED is illegal (terminal state)
        with self.assertRaises(ValueError):
            transition_service_request_status(
                service_request=req,
                target_status="VERIFIED",
                user_id=admin.id,
                note="Mencoba verifikasi pembatalan",
            )

    # ---------------------------------------------------------
    # 12. CITIZEN HTTP SUBMISSION (WEB FLOW)
    # ---------------------------------------------------------
    def test_citizen_web_submit_request(self):
        user, participant = self.create_citizen("web_submit")
        facility = self.create_facility("web_sub_fac")
        self.login_user(user.email, "Password123!")

        csrf = self.get_csrf_token("/citizen/services/request")
        visit_date = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

        post_data = {
            "csrf_token": csrf,
            "beneficiary_type": "SELF",
            "health_facility_id": str(facility.id),
            "service_type": "GENERAL",
            "scheduled_date": visit_date,
            "complaint_summary": "Pemeriksaan gula darah puasa",
        }

        res = self.client.post("/citizen/services/request", data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("berhasil dikirim", html.lower())
        self.assertIn("SWR-", html)

    # ---------------------------------------------------------
    # 13. CITIZEN WEB DETAIL & PRIVACY ISOLATION
    # ---------------------------------------------------------
    def test_citizen_privacy_isolation(self):
        user1, part1 = self.create_citizen("priv1")
        user2, part2 = self.create_citizen("priv2")
        facility = self.create_facility("priv_fac")

        req1 = create_service_request(
            participant=part1,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan user 1",
            beneficiary_type="SELF",
            user_id=user1.id,
        )

        # Login as User 2 and try to view User 1's request
        self.login_user(user2.email, "Password123!")
        res = self.client.get(f"/citizen/services/{req1.id}")
        self.assertEqual(res.status_code, 404)

        # Logout User 2
        self.logout_user()

        # Login as User 1 and view own request
        self.login_user(user1.email, "Password123!")
        res = self.client.get(f"/citizen/services/{req1.id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(req1.request_number, res.get_data(as_text=True))

    # ---------------------------------------------------------
    # 14. CITIZEN CANCELLATION (SUBMITTED -> CANCELLED)
    # ---------------------------------------------------------
    def test_citizen_cancel_submitted_request(self):
        user, participant = self.create_citizen("web_cancel")
        facility = self.create_facility("web_can_fac")
        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan batal",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.login_user(user.email, "Password123!")
        csrf = self.get_csrf_token(f"/citizen/services/{req.id}")

        res = self.client.post(
            f"/citizen/services/{req.id}/cancel",
            data={"csrf_token": csrf, "cancel_reason": "Berhalangan hadir karena urusan keluarga."},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("berhasil dibatalkan", res.get_data(as_text=True).lower())

        db.session.refresh(req)
        self.assertEqual(req.status, "CANCELLED")

    # ---------------------------------------------------------
    # 15. CITIZEN CANNOT CANCEL SCHEDULED REQUEST
    # ---------------------------------------------------------
    def test_citizen_cannot_cancel_scheduled_request(self):
        user, participant = self.create_citizen("no_can_sched")
        admin = self.create_admin("no_can_adm")
        facility = self.create_facility("no_can_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan dijadwalkan",
            beneficiary_type="SELF",
            user_id=user.id,
        )
        transition_service_request_status(req, "VERIFIED", admin.id, "Verifikasi berkas")
        transition_service_request_status(req, "SCHEDULED", admin.id, "Jadwal ditetapkan", date.today() + timedelta(days=3))

        self.login_user(user.email, "Password123!")
        csrf = self.get_csrf_token(f"/citizen/services/{req.id}")

        res = self.client.post(
            f"/citizen/services/{req.id}/cancel",
            data={"csrf_token": csrf, "cancel_reason": "Ingin batalkan"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("tidak dapat dibatalkan", res.get_data(as_text=True).lower())

        db.session.refresh(req)
        self.assertEqual(req.status, "SCHEDULED")

    # ---------------------------------------------------------
    # 16. ADMIN MANAGEMENT WEB FLOW (VERIFY, SCHEDULE, COMPLETE)
    # ---------------------------------------------------------
    def test_admin_service_actions_web_flow(self):
        user, participant = self.create_citizen("adm_flow_user")
        admin = self.create_admin("adm_flow_adm")
        facility = self.create_facility("adm_flow_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan alur admin",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.login_user(admin.email, "AdminPass123!")

        # 1. Admin checks service list
        res_list = self.client.get("/admin/services")
        self.assertEqual(res_list.status_code, 200)
        self.assertIn(req.request_number, res_list.get_data(as_text=True))

        # 2. Admin verifies request
        csrf_detail = self.get_csrf_token(f"/admin/services/{req.id}")
        res_ver = self.client.post(
            f"/admin/services/{req.id}/verify",
            data={"csrf_token": csrf_detail, "note": "Dokumen verifikasi oke"},
            follow_redirects=True,
        )
        self.assertEqual(res_ver.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "VERIFIED")

        # 3. Admin schedules request
        sched_date = (date.today() + timedelta(days=4)).strftime("%Y-%m-%d")
        csrf_detail = self.get_csrf_token(f"/admin/services/{req.id}")
        res_sched = self.client.post(
            f"/admin/services/{req.id}/schedule",
            data={"csrf_token": csrf_detail, "scheduled_date": sched_date, "note": "Poli Umum Jam 09.00"},
            follow_redirects=True,
        )
        self.assertEqual(res_sched.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "SCHEDULED")

        # 4. Admin completes request
        csrf_detail = self.get_csrf_token(f"/admin/services/{req.id}")
        res_comp = self.client.post(
            f"/admin/services/{req.id}/complete",
            data={"csrf_token": csrf_detail, "note": "Pelayanan poli tuntas"},
            follow_redirects=True,
        )
        self.assertEqual(res_comp.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "COMPLETED")

    # ---------------------------------------------------------
    # 17. ADMIN REJECT ACTION WEB FLOW
    # ---------------------------------------------------------
    def test_admin_reject_action_web_flow(self):
        user, participant = self.create_citizen("adm_rej_user")
        admin = self.create_admin("adm_rej_adm")
        facility = self.create_facility("adm_rej_fac")

        req = create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="OTHER",
            scheduled_date=date.today() + timedelta(days=2),
            complaint_summary="Pemeriksaan lain",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.login_user(admin.email, "AdminPass123!")
        csrf_detail = self.get_csrf_token(f"/admin/services/{req.id}")

        res_rej = self.client.post(
            f"/admin/services/{req.id}/reject",
            data={"csrf_token": csrf_detail, "reason": "Fasilitas tidak menyediakan layanan yang diminta."},
            follow_redirects=True,
        )
        self.assertEqual(res_rej.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "REJECTED")

    # ---------------------------------------------------------
    # 18. CITIZEN DASHBOARD SHOWS SERVICE STATS
    # ---------------------------------------------------------
    def test_citizen_dashboard_service_stats(self):
        user, participant = self.create_citizen("dash_cit")
        facility = self.create_facility("dash_cit_fac")

        create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=1),
            complaint_summary="Pemeriksaan 1",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.login_user(user.email, "Password123!")
        res = self.client.get("/citizen/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Layanan Aktif / Berjalan", html)
        self.assertIn("Total Layanan Diajukan", html)
        self.assertIn("Ajukan Layanan", html)

    # ---------------------------------------------------------
    # 19. ADMIN DASHBOARD SHOWS SERVICE STATS
    # ---------------------------------------------------------
    def test_admin_dashboard_service_stats(self):
        user, participant = self.create_citizen("dash_adm_user")
        admin = self.create_admin("dash_adm_adm")
        facility = self.create_facility("dash_adm_fac")

        create_service_request(
            participant=participant,
            health_facility_id=facility.id,
            service_type="GENERAL",
            scheduled_date=date.today() + timedelta(days=1),
            complaint_summary="Pemeriksaan admin dash",
            beneficiary_type="SELF",
            user_id=user.id,
        )

        self.login_user(admin.email, "AdminPass123!")
        res = self.client.get("/admin/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Operasional Pengajuan Layanan", html)
        self.assertIn("Menunggu Verifikasi", html)
        self.assertIn("Kelola Pengajuan Layanan", html)


if __name__ == "__main__":
    unittest.main()
