import unittest
from sqlalchemy import select, func
from tests import create_test_app
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.family_member import FamilyMember
from app.models.health_facility import HealthFacility
from app.models.service_request import ServiceRequest
from app.models.service_history import ServiceHistory
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.models.complaint import Complaint


class DemoSeederTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.app.config["TESTING"] = True

    def setUp(self):
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_seed_demo_full_execution_and_idempotency(self):
        runner = self.app.test_cli_runner()

        # Run 1: Execution on test db
        res1 = runner.invoke(args=["seed-demo-full", "--admin-password=Demo123!", "--citizen-password=Demo123!"])
        self.assertEqual(res1.exit_code, 0, f"Run 1 failed: {res1.output}")
        self.assertIn("SEHATWARGA - FULL DEMO DATA SEEDER", res1.output)
        self.assertIn("Status: SUKSES (Idempoten & Terhubung Sempurna).", res1.output)

        # Record counts after Run 1
        count_users_1 = db.session.execute(select(func.count(User.id))).scalar()
        count_parts_1 = db.session.execute(select(func.count(Participant.id))).scalar()
        count_fams_1 = db.session.execute(select(func.count(FamilyMember.id))).scalar()
        count_facs_1 = db.session.execute(select(func.count(HealthFacility.id))).scalar()
        count_srvs_1 = db.session.execute(select(func.count(ServiceRequest.id))).scalar()
        count_hist_1 = db.session.execute(select(func.count(ServiceHistory.id))).scalar()
        count_cont_1 = db.session.execute(select(func.count(Contribution.id))).scalar()
        count_pmts_1 = db.session.execute(select(func.count(Payment.id))).scalar()
        count_cmps_1 = db.session.execute(select(func.count(Complaint.id))).scalar()

        self.assertGreaterEqual(count_users_1, 20)
        self.assertGreaterEqual(count_parts_1, 19)
        self.assertGreaterEqual(count_fams_1, 25)
        self.assertGreaterEqual(count_facs_1, 20)
        self.assertGreaterEqual(count_srvs_1, 30)
        self.assertGreaterEqual(count_cont_1, 60)
        self.assertGreaterEqual(count_pmts_1, 50)
        self.assertGreaterEqual(count_cmps_1, 15)

        # Run 2: Idempotent run
        res2 = runner.invoke(args=["seed-demo-full", "--admin-password=Demo123!", "--citizen-password=Demo123!"])
        self.assertEqual(res2.exit_code, 0, f"Run 2 failed: {res2.output}")
        self.assertIn("0 dibuat", res2.output)

        # Record counts after Run 2 MUST be identical
        count_users_2 = db.session.execute(select(func.count(User.id))).scalar()
        count_parts_2 = db.session.execute(select(func.count(Participant.id))).scalar()
        count_fams_2 = db.session.execute(select(func.count(FamilyMember.id))).scalar()
        count_facs_2 = db.session.execute(select(func.count(HealthFacility.id))).scalar()
        count_srvs_2 = db.session.execute(select(func.count(ServiceRequest.id))).scalar()
        count_hist_2 = db.session.execute(select(func.count(ServiceHistory.id))).scalar()
        count_cont_2 = db.session.execute(select(func.count(Contribution.id))).scalar()
        count_pmts_2 = db.session.execute(select(func.count(Payment.id))).scalar()
        count_cmps_2 = db.session.execute(select(func.count(Complaint.id))).scalar()

        self.assertEqual(count_users_1, count_users_2)
        self.assertEqual(count_parts_1, count_parts_2)
        self.assertEqual(count_fams_1, count_fams_2)
        self.assertEqual(count_facs_1, count_facs_2)
        self.assertEqual(count_srvs_1, count_srvs_2)
        self.assertEqual(count_hist_1, count_hist_2)
        self.assertEqual(count_cont_1, count_cont_2)
        self.assertEqual(count_pmts_1, count_pmts_2)
        self.assertEqual(count_cmps_1, count_cmps_2)

    def test_seeded_data_integrity_and_relationships(self):
        # 1. Admin login verification
        admin = db.session.execute(select(User).filter_by(email="admin.demo@sehatwarga.test")).scalar_one_or_none()
        self.assertIsNotNone(admin)
        self.assertEqual(admin.role, "admin")
        self.assertTrue(admin.check_password("Demo123!"))

        # 2. Main citizen login verification
        citizen = db.session.execute(select(User).filter_by(email="warga.demo@sehatwarga.test")).scalar_one_or_none()
        self.assertIsNotNone(citizen)
        self.assertEqual(citizen.role, "citizen")
        self.assertTrue(citizen.check_password("Demo123!"))
        self.assertIsNotNone(citizen.participant)

        # 3. Orphan verification: No family member without existing participant
        orphans_fm = db.session.execute(
            select(FamilyMember).outerjoin(Participant, FamilyMember.participant_id == Participant.id).filter(Participant.id.is_(None))
        ).scalars().all()
        self.assertEqual(len(orphans_fm), 0, "Found orphan family members!")

        # 4. Orphan verification: No service request without existing participant or facility
        orphans_sr_p = db.session.execute(
            select(ServiceRequest).outerjoin(Participant, ServiceRequest.participant_id == Participant.id).filter(Participant.id.is_(None))
        ).scalars().all()
        self.assertEqual(len(orphans_sr_p), 0, "Found service requests with invalid participant!")

        orphans_sr_f = db.session.execute(
            select(ServiceRequest).outerjoin(HealthFacility, ServiceRequest.health_facility_id == HealthFacility.id).filter(HealthFacility.id.is_(None))
        ).scalars().all()
        self.assertEqual(len(orphans_sr_f), 0, "Found service requests with invalid facility!")

        # 5. Orphan verification: No payment without existing contribution
        orphans_pmt = db.session.execute(
            select(Payment).outerjoin(Contribution, Payment.contribution_id == Contribution.id).filter(Contribution.id.is_(None))
        ).scalars().all()
        self.assertEqual(len(orphans_pmt), 0, "Found orphan payments!")

        # 6. Payment amount consistency with contribution amount
        payments = db.session.execute(select(Payment)).scalars().all()
        for p in payments:
            self.assertEqual(p.amount, p.contribution.amount)
            self.assertEqual(p.status, "SUCCESS")
            self.assertEqual(p.contribution.status, "PAID")

        # 7. Orphan verification: No complaint without existing user
        orphans_cmp = db.session.execute(
            select(Complaint).outerjoin(User, Complaint.user_id == User.id).filter(User.id.is_(None))
        ).scalars().all()
        self.assertEqual(len(orphans_cmp), 0, "Found orphan complaints!")

        # 8. Service Request status history completeness
        service_requests = db.session.execute(select(ServiceRequest)).scalars().all()
        for sr in service_requests:
            hist_statuses = [h.status for h in sr.histories]
            self.assertIn("SUBMITTED", hist_statuses, f"ServiceRequest {sr.request_number} missing initial SUBMITTED history")
            self.assertIn(sr.status, hist_statuses, f"ServiceRequest {sr.request_number} current status not in histories")

        # 9. Health facility coordinate bounds
        facilities = db.session.execute(select(HealthFacility)).scalars().all()
        for f in facilities:
            self.assertIsNotNone(f.latitude)
            self.assertIsNotNone(f.longitude)
            lat = float(f.latitude)
            lng = float(f.longitude)
            self.assertTrue(-10.0 <= lat <= -5.0, f"Facility {f.facility_code} latitude {lat} out of East Java range")
            self.assertTrue(110.0 <= lng <= 116.0, f"Facility {f.facility_code} longitude {lng} out of East Java range")


if __name__ == "__main__":
    unittest.main()
