"""Render the existing feature surface with real relationships in isolated fixtures."""
import tests
import unittest
from jinja2 import StrictUndefined
from tests import create_test_app
from app.extensions import db
from app.models import User, HealthFacility, FamilyMember, ServiceRequest, Contribution, Payment, Complaint
from sqlalchemy import select

class RenderRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=create_test_app()
        cls.app.jinja_env.undefined=StrictUndefined
        result=cls.app.test_cli_runner().invoke(args=['seed-demo','--admin-password=AdminDemo123!','--citizen-password=WargaDemo123!'])
        if result.exit_code:raise RuntimeError('Could not seed isolated test data')

    def test_all_public_citizen_admin_pages(self):
        with self.app.app_context():
            citizen=db.session.execute(select(User).filter_by(email='warga.demo@sehatwarga.test')).scalar_one()
            admin=db.session.execute(select(User).filter_by(email='admin.demo@sehatwarga.test')).scalar_one()
            facility=db.session.execute(select(HealthFacility).filter_by(is_active=True)).scalars().first()
            family=citizen.participant.family_members[0]
            service=citizen.participant.service_requests[0]
            family_service=next(s for s in citizen.participant.service_requests if s.family_member_id)
            bill=citizen.participant.contributions[0]
            payment=db.session.execute(select(Payment).join(Payment.contribution).filter(Contribution.participant_id==citizen.participant.id)).scalars().first()
            complaint=citizen.complaints[0]
            routes={None:['/','/health','/login','/register','/facilities',f'/facilities/{facility.id}','/assistant'],citizen.id:['/citizen/dashboard','/citizen/profile','/citizen/card','/citizen/family','/citizen/family/add',f'/citizen/family/{family.id}',f'/citizen/family/{family.id}/edit','/citizen/services','/citizen/services/request',f'/citizen/services/{service.id}',f'/citizen/services/{family_service.id}','/citizen/contributions',f'/citizen/contributions/{bill.id}','/citizen/payments',f'/citizen/payments/{payment.id}','/citizen/complaints','/citizen/complaints/create',f'/citizen/complaints/{complaint.id}'],admin.id:['/admin/dashboard','/admin/facilities','/admin/facilities/create',f'/admin/facilities/{facility.id}/edit','/admin/services',f'/admin/services/{service.id}',f'/admin/services/{family_service.id}','/admin/contributions',f'/admin/contributions/{bill.id}','/admin/payments','/admin/complaints',f'/admin/complaints/{complaint.id}']}
            unpaid=next(b for b in citizen.participant.contributions if b.status in ['UNPAID','OVERDUE'])
            routes[citizen.id].append(f'/citizen/contributions/{unpaid.id}/pay')
        for user_id,paths in routes.items():
            client=self.app.test_client()
            if user_id:
                with client.session_transaction() as session:session['_user_id']=str(user_id);session['_fresh']=True
            for path in paths:
                with self.subTest(path=path):
                    response=client.get(path)
                    self.assertEqual(response.status_code,200)
