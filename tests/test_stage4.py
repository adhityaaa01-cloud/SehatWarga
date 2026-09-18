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
from app.services.participant_service import register_citizen
from app.services.family_service import generate_family_member_number, create_family_member


class Stage4TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True
        cls.app.config["WTF_CSRF_ENABLED"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.runner = self.app.test_cli_runner()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        db.session.rollback()
        # Clean up test users and their participants + family members
        test_users = db.session.execute(
            select(User).filter(User.email.like("test_s4_%@example.com"))
        ).scalars().all()
        for u in test_users:
            if u.participant:
                for fm in u.participant.family_members:
                    db.session.delete(fm)
                db.session.delete(u.participant)
            db.session.delete(u)

        # Clean up test facilities
        test_facilities = db.session.execute(
            select(HealthFacility).filter(HealthFacility.facility_code.like("TEST-FAC-%"))
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

    def create_citizen(self, tag):
        user, participant = register_citizen(
            name=f"Citizen {tag}",
            email=f"test_s4_{tag}@example.com",
            password="Password123!",
            birth_date=date(1990, 1, 1),
            gender="MALE",
            service_class="CLASS_1",
        )
        return user, participant

    def create_admin(self, tag):
        admin = User(
            name=f"Admin {tag}",
            email=f"test_s4_{tag}@example.com",
            role="admin",
            is_active=True,
        )
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        return admin

    def login_user(self, email, password):
        csrf = self.get_csrf_token("/login")
        return self.client.post("/login", data={"csrf_token": csrf, "email": email, "password": password})

    def logout_user(self):
        csrf = self.get_csrf_token("/citizen/dashboard")
        return self.client.post("/logout", data={"csrf_token": csrf})

    # ---------------------------------------------------------
    # 42. TEST FAMILY CREATE & 46. TEST MEMBER NUMBER
    # ---------------------------------------------------------
    def test_family_create_and_member_number(self):
        user, participant = self.create_citizen("fam1")
        self.login_user(user.email, "Password123!")

        csrf = self.get_csrf_token("/citizen/family/add")
        post_data = {
            "csrf_token": csrf,
            "full_name": "Siti Rahmawati",
            "relationship": "SPOUSE",
            "birth_date": "1992-04-10",
            "gender": "FEMALE",
        }
        res = self.client.post("/citizen/family/add", data=post_data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        member = db.session.execute(
            select(FamilyMember).filter_by(participant_id=participant.id, full_name="Siti Rahmawati")
        ).scalar_one_or_none()
        self.assertIsNotNone(member)
        self.assertEqual(member.relationship, "SPOUSE")
        self.assertEqual(member.gender, "FEMALE")
        self.assertEqual(member.membership_status, "ACTIVE")

        # Check format: SWF-YYYY-XXXXXXXX
        current_year = date.today().year
        self.assertRegex(member.member_number, rf"^SWF-{current_year}-[A-Z0-9]{{8}}$")

    # ---------------------------------------------------------
    # 43. TEST FAMILY MASS ASSIGNMENT
    # ---------------------------------------------------------
    def test_family_mass_assignment(self):
        user, participant = self.create_citizen("mass")
        self.login_user(user.email, "Password123!")

        csrf = self.get_csrf_token("/citizen/family/add")
        hack_data = {
            "csrf_token": csrf,
            "full_name": "Injected Family",
            "relationship": "CHILD",
            "birth_date": "2015-06-01",
            "gender": "MALE",
            "participant_id": 9999,
            "member_number": "HACK-SWF-0000",
            "membership_status": "INACTIVE",
        }
        res = self.client.post("/citizen/family/add", data=hack_data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)

        member = db.session.execute(
            select(FamilyMember).filter_by(full_name="Injected Family")
        ).scalar_one_or_none()
        self.assertIsNotNone(member)
        self.assertEqual(member.participant_id, participant.id)
        self.assertNotEqual(member.member_number, "HACK-SWF-0000")
        self.assertTrue(member.member_number.startswith("SWF-"))
        self.assertEqual(member.membership_status, "ACTIVE")

    # ---------------------------------------------------------
    # 44. TEST FAMILY OWNERSHIP
    # ---------------------------------------------------------
    def test_family_ownership_isolation(self):
        user_a, part_a = self.create_citizen("user_a")
        member_a = create_family_member(
            participant_id=part_a.id,
            full_name="Anak User A",
            relationship="CHILD",
            birth_date=date(2018, 1, 1),
            gender="MALE",
        )

        user_b, _ = self.create_citizen("user_b")

        # Login as User B
        self.login_user(user_b.email, "Password123!")

        # User B attempts to GET Member A detail -> 404
        res_detail = self.client.get(f"/citizen/family/{member_a.id}")
        self.assertEqual(res_detail.status_code, 404)

        # User B attempts to GET Member A edit form -> 404
        res_edit_get = self.client.get(f"/citizen/family/{member_a.id}/edit")
        self.assertEqual(res_edit_get.status_code, 404)

        # User B attempts to POST Member A edit -> 404
        csrf = self.get_csrf_token("/citizen/family")
        res_edit_post = self.client.post(
            f"/citizen/family/{member_a.id}/edit",
            data={
                "csrf_token": csrf,
                "full_name": "Hacked Name",
                "relationship": "CHILD",
                "birth_date": "2018-01-01",
                "gender": "MALE",
            },
        )
        self.assertEqual(res_edit_post.status_code, 404)

        # User B attempts to POST Member A remove -> 404
        res_remove = self.client.post(
            f"/citizen/family/{member_a.id}/remove",
            data={"csrf_token": csrf},
        )
        self.assertEqual(res_remove.status_code, 404)

        # Member A data remains untouched
        db.session.refresh(member_a)
        self.assertEqual(member_a.full_name, "Anak User A")
        self.assertEqual(member_a.membership_status, "ACTIVE")

    # ---------------------------------------------------------
    # 45. TEST FAMILY VALIDATION
    # ---------------------------------------------------------
    def test_family_validation(self):
        user, _ = self.create_citizen("val")
        self.login_user(user.email, "Password123!")

        # Empty name
        csrf = self.get_csrf_token("/citizen/family/add")
        res = self.client.post(
            "/citizen/family/add",
            data={
                "csrf_token": csrf,
                "full_name": "   ",
                "relationship": "SPOUSE",
                "birth_date": "1995-01-01",
                "gender": "FEMALE",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Nama tidak boleh hanya berupa spasi", res.get_data(as_text=True))

        # Invalid relationship
        csrf = self.get_csrf_token("/citizen/family/add")
        res = self.client.post(
            "/citizen/family/add",
            data={
                "csrf_token": csrf,
                "full_name": "Valid Name",
                "relationship": "INVALID_REL",
                "birth_date": "1995-01-01",
                "gender": "FEMALE",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Not a valid choice", res.get_data(as_text=True))

        # Future birth date
        future_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        csrf = self.get_csrf_token("/citizen/family/add")
        res = self.client.post(
            "/citizen/family/add",
            data={
                "csrf_token": csrf,
                "full_name": "Future Baby",
                "relationship": "CHILD",
                "birth_date": future_date,
                "gender": "MALE",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Tanggal lahir tidak boleh di masa depan", res.get_data(as_text=True))

    # ---------------------------------------------------------
    # 47. TEST FACILITY PUBLIC LIST & 48. FILTERS
    # ---------------------------------------------------------
    def test_facility_public_list_and_filters(self):
        # Create 1 active facility and 1 inactive facility
        f_active = HealthFacility(
            facility_code="TEST-FAC-ACT1",
            name="Klinik Uji Aktif",
            facility_type="CLINIC",
            city="Surabaya",
            address="Jl. Uji Coba 1",
            latitude=Decimal("-7.2600"),
            longitude=Decimal("112.7500"),
            is_active=True,
        )
        f_inactive = HealthFacility(
            facility_code="TEST-FAC-INACT1",
            name="Klinik Uji Nonaktif",
            facility_type="CLINIC",
            city="Surabaya",
            address="Jl. Uji Coba 2",
            is_active=False,
        )
        db.session.add_all([f_active, f_inactive])
        db.session.commit()

        # Public list
        res = self.client.get("/facilities")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Klinik Uji Aktif", html)
        self.assertNotIn("Klinik Uji Nonaktif", html)

        # Filter by search
        res_search = self.client.get("/facilities?search=TEST-FAC-ACT1")
        self.assertEqual(res_search.status_code, 200)
        self.assertIn("Klinik Uji Aktif", res_search.get_data(as_text=True))

        # Filter by invalid type should not produce 500
        res_inv = self.client.get("/facilities?facility_type=INVALID_TYPE")
        self.assertEqual(res_inv.status_code, 200)

    # ---------------------------------------------------------
    # 49. TEST FACILITY DETAIL
    # ---------------------------------------------------------
    def test_facility_detail(self):
        f_active = HealthFacility(
            facility_code="TEST-FAC-DET1",
            name="RS Detail Aktif",
            facility_type="HOSPITAL",
            city="Surabaya",
            is_active=True,
        )
        f_inactive = HealthFacility(
            facility_code="TEST-FAC-DET2",
            name="RS Detail Inaktif",
            facility_type="HOSPITAL",
            city="Surabaya",
            is_active=False,
        )
        db.session.add_all([f_active, f_inactive])
        db.session.commit()

        # Active facility: 200
        res_act = self.client.get(f"/facilities/{f_active.id}")
        self.assertEqual(res_act.status_code, 200)
        self.assertIn("RS Detail Aktif", res_act.get_data(as_text=True))

        # Inactive facility via public: 404
        res_inact = self.client.get(f"/facilities/{f_inactive.id}")
        self.assertEqual(res_inact.status_code, 404)

        # Nonexistent facility: 404
        res_non = self.client.get("/facilities/999999")
        self.assertEqual(res_non.status_code, 404)

    # ---------------------------------------------------------
    # 50. TEST ADMIN FACILITY PROTECTION
    # ---------------------------------------------------------
    def test_admin_facility_protection(self):
        # Unauthenticated redirects to login
        res_unauth = self.client.get("/admin/facilities", follow_redirects=False)
        self.assertEqual(res_unauth.status_code, 302)
        self.assertIn("/login", res_unauth.headers["Location"])

        # Citizen gets 403
        user, _ = self.create_citizen("protect")
        self.login_user(user.email, "Password123!")

        res_cit = self.client.get("/admin/facilities")
        self.assertEqual(res_cit.status_code, 403)

        res_cit_create = self.client.get("/admin/facilities/create")
        self.assertEqual(res_cit_create.status_code, 403)

        self.logout_user()

        # Admin gets 200
        admin = self.create_admin("protect_admin")
        self.login_user(admin.email, "AdminPass123!")

        res_adm = self.client.get("/admin/facilities")
        self.assertEqual(res_adm.status_code, 200)

    # ---------------------------------------------------------
    # 51. TEST FACILITY CREATE & 52. DEACTIVATION
    # ---------------------------------------------------------
    def test_admin_facility_create_and_deactivation(self):
        admin = self.create_admin("mgr_admin")
        self.login_user(admin.email, "AdminPass123!")

        csrf = self.get_csrf_token("/admin/facilities/create")
        post_data = {
            "csrf_token": csrf,
            "facility_code": "TEST-FAC-NEW1",
            "name": "Puskesmas Admin Baru",
            "facility_type": "PUSKESMAS",
            "address": "Jl. Merdeka No. 1",
            "city": "Surabaya",
            "phone": "031-112233",
            "latitude": "-7.2500000",
            "longitude": "112.7500000",
            "is_active": "y",
        }
        res_create = self.client.post("/admin/facilities/create", data=post_data, follow_redirects=False)
        self.assertEqual(res_create.status_code, 302)

        facility = db.session.execute(
            select(HealthFacility).filter_by(facility_code="TEST-FAC-NEW1")
        ).scalar_one_or_none()
        self.assertIsNotNone(facility)
        self.assertTrue(facility.is_active)

        # Duplicate facility_code should fail
        csrf2 = self.get_csrf_token("/admin/facilities/create")
        post_data["csrf_token"] = csrf2
        res_dup = self.client.post("/admin/facilities/create", data=post_data)
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn("sudah digunakan", res_dup.get_data(as_text=True))

        # Admin toggle-status to deactivate
        csrf_toggle = self.get_csrf_token("/admin/facilities")
        res_toggle = self.client.post(
            f"/admin/facilities/{facility.id}/toggle-status",
            data={"csrf_token": csrf_toggle},
            follow_redirects=False,
        )
        self.assertEqual(res_toggle.status_code, 302)

        db.session.refresh(facility)
        self.assertFalse(facility.is_active)

        # Check public list does NOT show it
        res_pub = self.client.get("/facilities")
        self.assertNotIn("TEST-FAC-NEW1", res_pub.get_data(as_text=True))
        self.assertNotIn('<h3 class="facility-name">Puskesmas Admin Baru</h3>', res_pub.get_data(as_text=True))

        # Check admin list STILL shows it
        res_adm_list = self.client.get("/admin/facilities")
        self.assertIn("Puskesmas Admin Baru", res_adm_list.get_data(as_text=True))
        self.assertIn("NONAKTIF", res_adm_list.get_data(as_text=True))

    # ---------------------------------------------------------
    # 53. TEST SEED IDEMPOTENCY
    # ---------------------------------------------------------
    def test_seed_facilities_cli(self):
        res1 = self.runner.invoke(args=["seed-facilities"])
        self.assertEqual(res1.exit_code, 0)

        res2 = self.runner.invoke(args=["seed-facilities"])
        self.assertEqual(res2.exit_code, 0)
        self.assertIn("0 fasilitas kesehatan baru ditambahkan", res2.output)


if __name__ == "__main__":
    unittest.main()
