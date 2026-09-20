"""
Full Demo Data Seeder for SehatWarga (TCC 2026).
Ensures safe, idempotent, realistic, and fully interconnected simulation data.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import click
from sqlalchemy import select
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
from app.services.contribution_service import SIMULATED_RATES


def run_seed_demo_full(admin_password: str = None, citizen_password: str = None) -> dict:
    """
    Executes the full demo seed process idempotently within a safe database transaction.
    """
    default_password = "Demo123!"
    effective_admin_pwd = admin_password or default_password
    effective_citizen_pwd = citizen_password or default_password

    stats = {
        "admin": {"created": 0, "existing": 0},
        "citizens": {"created": 0, "existing": 0},
        "family_members": {"created": 0, "existing": 0},
        "facilities": {"created": 0, "existing": 0},
        "service_requests": {"created": 0, "existing": 0},
        "service_histories": {"created": 0, "existing": 0},
        "contributions": {"created": 0, "existing": 0},
        "payments": {"created": 0, "existing": 0},
        "complaints": {"created": 0, "existing": 0},
    }

    try:
        # =====================================================================
        # 1. FACILITIES (25 facilities total: 7 existing + 18 new East Java)
        # =====================================================================
        facilities_data = [
            # Existing core set
            {
                "facility_code": "FS-SBY-001",
                "name": "Puskesmas Simulasi SehatWarga Sentral",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Pemuda No. 12, Embong Kaliasin",
                "city": "Surabaya",
                "phone": "031-5312001",
                "latitude": Decimal("-7.2655000"),
                "longitude": Decimal("112.7518000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-002",
                "name": "Rumah Sakit Umum Simulasi SehatWarga Utama",
                "facility_type": "HOSPITAL",
                "address": "Jl. Dharmahusada No. 45, Gubeng",
                "city": "Surabaya",
                "phone": "031-5034002",
                "latitude": Decimal("-7.2690000"),
                "longitude": Decimal("112.7630000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-003",
                "name": "Klinik Pratama Simulasi SehatWarga Sejahtera",
                "facility_type": "CLINIC",
                "address": "Jl. Raya Darmo No. 88, Tegalsari",
                "city": "Surabaya",
                "phone": "031-5678003",
                "latitude": Decimal("-7.2880000"),
                "longitude": Decimal("112.7380000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-004",
                "name": "Klinik Gigi Simulasi SehatWarga Senyum Indah",
                "facility_type": "DENTAL_CLINIC",
                "address": "Jl. Mayjen Sungkono No. 102, Dukuh Pakis",
                "city": "Surabaya",
                "phone": "031-5621004",
                "latitude": Decimal("-7.2915000"),
                "longitude": Decimal("112.7150000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-005",
                "name": "Puskesmas Simulasi SehatWarga Waru",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Raya Waru No. 15, Waru",
                "city": "Sidoarjo",
                "phone": "031-8532005",
                "latitude": Decimal("-7.3550000"),
                "longitude": Decimal("112.7480000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-006",
                "name": "Rumah Sakit Khusus Simulasi SehatWarga Medika",
                "facility_type": "HOSPITAL",
                "address": "Jl. Pahlawan No. 70, Sidokumpul",
                "city": "Sidoarjo",
                "phone": "031-8945006",
                "latitude": Decimal("-7.4478000"),
                "longitude": Decimal("112.7180000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MLG-007",
                "name": "Klinik Pratama Simulasi SehatWarga Brawijaya",
                "facility_type": "CLINIC",
                "address": "Jl. Ijen No. 25, Klojen",
                "city": "Malang",
                "phone": "0341-367007",
                "latitude": Decimal("-7.9730000"),
                "longitude": Decimal("112.6240000"),
                "is_active": True,
            },
            # Expanded facilities across East Java
            {
                "facility_code": "FS-SBY-008",
                "name": "Puskesmas Simulasi Rungkut",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Rungkut Asri No. 18, Rungkut",
                "city": "Surabaya",
                "phone": "031-8712340",
                "latitude": Decimal("-7.3180000"),
                "longitude": Decimal("112.7750000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-009",
                "name": "RS Umum Simulasi Surabaya Timur",
                "facility_type": "HOSPITAL",
                "address": "Jl. Kenjeran No. 240, Kenjeran",
                "city": "Surabaya",
                "phone": "031-3814520",
                "latitude": Decimal("-7.2450000"),
                "longitude": Decimal("112.7850000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-010",
                "name": "Klinik Pratama Simulasi Medika Tandes",
                "facility_type": "CLINIC",
                "address": "Jl. Balongsari Tama No. 4, Tandes",
                "city": "Surabaya",
                "phone": "031-7401123",
                "latitude": Decimal("-7.2620000"),
                "longitude": Decimal("112.6840000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-011",
                "name": "Klinik Gigi Simulasi Sidoarjo Sehat",
                "facility_type": "DENTAL_CLINIC",
                "address": "Jl. Gajah Mada No. 82, Sidokumpul",
                "city": "Sidoarjo",
                "phone": "031-8962211",
                "latitude": Decimal("-7.4520000"),
                "longitude": Decimal("112.7150000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-012",
                "name": "Puskesmas Simulasi Krian",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Kyai Mojo No. 5, Krian",
                "city": "Sidoarjo",
                "phone": "031-8971040",
                "latitude": Decimal("-7.4060000"),
                "longitude": Decimal("112.5930000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-GRS-013",
                "name": "Puskesmas Simulasi Kebomas",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Sunan Giri No. 33, Kebomas",
                "city": "Gresik",
                "phone": "031-3982001",
                "latitude": Decimal("-7.1650000"),
                "longitude": Decimal("112.6350000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-GRS-014",
                "name": "RS Umum Simulasi Gresik Sejahtera",
                "facility_type": "HOSPITAL",
                "address": "Jl. Dr. Wahidin Sudirohusodo No. 120",
                "city": "Gresik",
                "phone": "031-3951122",
                "latitude": Decimal("-7.1580000"),
                "longitude": Decimal("112.6500000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-GRS-015",
                "name": "Klinik Pratama Simulasi Manyar Husada",
                "facility_type": "CLINIC",
                "address": "Jl. Raya Manyar No. 45, Manyar",
                "city": "Gresik",
                "phone": "031-3957800",
                "latitude": Decimal("-7.1230000"),
                "longitude": Decimal("112.6020000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-LMG-016",
                "name": "Puskesmas Simulasi Lamongan Kota",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Veteran No. 14, Lamongan",
                "city": "Lamongan",
                "phone": "0322-321450",
                "latitude": Decimal("-7.1180000"),
                "longitude": Decimal("112.4150000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-LMG-017",
                "name": "RS Umum Simulasi Lamongan Sehat",
                "facility_type": "HOSPITAL",
                "address": "Jl. Kusuma Bangsa No. 7, Lamongan",
                "city": "Lamongan",
                "phone": "0322-322100",
                "latitude": Decimal("-7.1250000"),
                "longitude": Decimal("112.4080000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MJK-018",
                "name": "Puskesmas Simulasi Magersari",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Pahlawan No. 22, Magersari",
                "city": "Mojokerto",
                "phone": "0321-324001",
                "latitude": Decimal("-7.4720000"),
                "longitude": Decimal("112.4380000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MJK-019",
                "name": "RS Simulasi Mojokerto Husada",
                "facility_type": "HOSPITAL",
                "address": "Jl. Gajah Mada No. 100, Mojokerto",
                "city": "Mojokerto",
                "phone": "0321-328900",
                "latitude": Decimal("-7.4650000"),
                "longitude": Decimal("112.4450000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MJK-020",
                "name": "Klinik Pratama Simulasi Mojosari",
                "facility_type": "CLINIC",
                "address": "Jl. Niaga No. 15, Mojosari",
                "city": "Mojokerto",
                "phone": "0321-591230",
                "latitude": Decimal("-7.5120000"),
                "longitude": Decimal("112.5500000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-JBG-021",
                "name": "Puskesmas Simulasi Jombang Kota",
                "facility_type": "PUSKESMAS",
                "address": "Jl. KH. Wahid Hasyim No. 50, Jombang",
                "city": "Jombang",
                "phone": "0321-861234",
                "latitude": Decimal("-7.5450000"),
                "longitude": Decimal("112.2330000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-JBG-022",
                "name": "RS Umum Simulasi Jombang Sehat",
                "facility_type": "HOSPITAL",
                "address": "Jl. Dr. Soetomo No. 18, Jombang",
                "city": "Jombang",
                "phone": "0321-862500",
                "latitude": Decimal("-7.5520000"),
                "longitude": Decimal("112.2280000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MLG-023",
                "name": "RS Umum Simulasi Saiful Sehat Malang",
                "facility_type": "HOSPITAL",
                "address": "Jl. Jaksa Agung Suprapto No. 2, Klojen",
                "city": "Malang",
                "phone": "0341-362101",
                "latitude": Decimal("-7.9780000"),
                "longitude": Decimal("112.6310000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-MLG-024",
                "name": "Puskesmas Simulasi Dinoyo",
                "facility_type": "PUSKESMAS",
                "address": "Jl. MT. Haryono No. 110, Lowokwaru",
                "city": "Malang",
                "phone": "0341-551200",
                "latitude": Decimal("-7.9480000"),
                "longitude": Decimal("112.6070000"),
                "is_active": True,
            },
            {
                "facility_code": "FS-PAS-025",
                "name": "Puskesmas Simulasi Purworejo",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Panglima Sudirman No. 30, Purworejo",
                "city": "Pasuruan",
                "phone": "0343-421300",
                "latitude": Decimal("-7.6450000"),
                "longitude": Decimal("112.9050000"),
                "is_active": True,
            },
        ]

        facility_map = {}
        for fd in facilities_data:
            fac = db.session.execute(
                select(HealthFacility).filter_by(facility_code=fd["facility_code"])
            ).scalar_one_or_none()

            if not fac:
                fac = HealthFacility(
                    facility_code=fd["facility_code"],
                    name=fd["name"],
                    facility_type=fd["facility_type"],
                    address=fd["address"],
                    city=fd["city"],
                    phone=fd["phone"],
                    latitude=fd["latitude"],
                    longitude=fd["longitude"],
                    is_active=fd["is_active"],
                )
                db.session.add(fac)
                db.session.flush()
                stats["facilities"]["created"] += 1
            else:
                # Update non-destructive fields if needed to ensure valid coords
                if fac.latitude is None or fac.longitude is None:
                    fac.latitude = fd["latitude"]
                    fac.longitude = fd["longitude"]
                stats["facilities"]["existing"] += 1

            facility_map[fd["facility_code"]] = fac

        # =====================================================================
        # 2. ADMIN USER
        # =====================================================================
        admin_email = "admin.demo@sehatwarga.test"
        admin_user = db.session.execute(
            select(User).filter_by(email=admin_email)
        ).scalar_one_or_none()

        if not admin_user:
            admin_user = User(
                name="Admin Demo SehatWarga",
                email=admin_email,
                role="admin",
                is_active=True,
            )
            admin_user.set_password(effective_admin_pwd)
            db.session.add(admin_user)
            db.session.flush()
            stats["admin"]["created"] += 1
        else:
            # Guarantee password matches required demo credentials
            admin_user.set_password(effective_admin_pwd)
            admin_user.is_active = True
            stats["admin"]["existing"] += 1

        # =====================================================================
        # 3. CITIZEN USERS & PARTICIPANTS (20 demo citizens)
        # =====================================================================
        citizens_data = [
            {
                "email": "warga.demo@sehatwarga.test",
                "name": "Warga Demo SehatWarga",
                "participant_number": "SW-2026-DEMO0001",
                "birth_date": date(1990, 8, 17),
                "gender": "MALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "budi.santoso@sehatwarga.test",
                "name": "Budi Santoso",
                "participant_number": "SW-2026-DEMO0002",
                "birth_date": date(1985, 4, 12),
                "gender": "MALE",
                "service_class": "CLASS_1",
                "membership_status": "ACTIVE",
            },
            {
                "email": "siti.aminah@sehatwarga.test",
                "name": "Siti Aminah",
                "participant_number": "SW-2026-DEMO0003",
                "birth_date": date(1988, 11, 23),
                "gender": "FEMALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "ahmad.dahlan@sehatwarga.test",
                "name": "Ahmad Dahlan",
                "participant_number": "SW-2026-DEMO0004",
                "birth_date": date(1979, 2, 15),
                "gender": "MALE",
                "service_class": "CLASS_1",
                "membership_status": "ACTIVE",
            },
            {
                "email": "dewi.lestari@sehatwarga.test",
                "name": "Dewi Lestari",
                "participant_number": "SW-2026-DEMO0005",
                "birth_date": date(1993, 7, 8),
                "gender": "FEMALE",
                "service_class": "CLASS_3",
                "membership_status": "ACTIVE",
            },
            {
                "email": "hendra.wijaya@sehatwarga.test",
                "name": "Hendra Wijaya",
                "participant_number": "SW-2026-DEMO0006",
                "birth_date": date(1982, 9, 30),
                "gender": "MALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "rina.kartika@sehatwarga.test",
                "name": "Rina Kartika Sari",
                "participant_number": "SW-2026-DEMO0007",
                "birth_date": date(1995, 3, 14),
                "gender": "FEMALE",
                "service_class": "CLASS_3",
                "membership_status": "ACTIVE",
            },
            {
                "email": "agus.setiawan@sehatwarga.test",
                "name": "Agus Setiawan",
                "participant_number": "SW-2026-DEMO0008",
                "birth_date": date(1975, 12, 5),
                "gender": "MALE",
                "service_class": "CLASS_1",
                "membership_status": "ACTIVE",
            },
            {
                "email": "maya.safitri@sehatwarga.test",
                "name": "Maya Safitri",
                "participant_number": "SW-2026-DEMO0009",
                "birth_date": date(1991, 6, 19),
                "gender": "FEMALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "fajar.nugroho@sehatwarga.test",
                "name": "Fajar Nugroho",
                "participant_number": "SW-2026-DEMO0010",
                "birth_date": date(1987, 10, 25),
                "gender": "MALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "dian.kusuma@sehatwarga.test",
                "name": "Dian Kusuma Wardani",
                "participant_number": "SW-2026-DEMO0011",
                "birth_date": date(1994, 1, 18),
                "gender": "FEMALE",
                "service_class": "CLASS_3",
                "membership_status": "ACTIVE",
            },
            {
                "email": "joko.prasetyo@sehatwarga.test",
                "name": "Joko Prasetyo",
                "participant_number": "SW-2026-DEMO0012",
                "birth_date": date(1980, 5, 22),
                "gender": "MALE",
                "service_class": "CLASS_1",
                "membership_status": "ACTIVE",
            },
            {
                "email": "nurul.hidayati@sehatwarga.test",
                "name": "Nurul Hidayati",
                "participant_number": "SW-2026-DEMO0013",
                "birth_date": date(1989, 8, 9),
                "gender": "FEMALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "eka.putra@sehatwarga.test",
                "name": "Eka Pratama Putra",
                "participant_number": "SW-2026-DEMO0014",
                "birth_date": date(1996, 12, 3),
                "gender": "MALE",
                "service_class": "CLASS_3",
                "membership_status": "ACTIVE",
            },
            {
                "email": "gita.pertiwi@sehatwarga.test",
                "name": "Gita Ayu Pertiwi",
                "participant_number": "SW-2026-DEMO0015",
                "birth_date": date(1992, 4, 27),
                "gender": "FEMALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "hadi.firmansyah@sehatwarga.test",
                "name": "Hadi Firmansyah",
                "participant_number": "SW-2026-DEMO0016",
                "birth_date": date(1984, 7, 16),
                "gender": "MALE",
                "service_class": "CLASS_1",
                "membership_status": "ACTIVE",
            },
            {
                "email": "kartika.wulandari@sehatwarga.test",
                "name": "Kartika Wulandari",
                "participant_number": "SW-2026-DEMO0017",
                "birth_date": date(1997, 9, 11),
                "gender": "FEMALE",
                "service_class": "CLASS_3",
                "membership_status": "ACTIVE",
            },
            {
                "email": "lukman.hakim@sehatwarga.test",
                "name": "Lukman Hakim",
                "participant_number": "SW-2026-DEMO0018",
                "birth_date": date(1981, 3, 5),
                "gender": "MALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "tri.wahyuni@sehatwarga.test",
                "name": "Tri Wahyuni",
                "participant_number": "SW-2026-DEMO0019",
                "birth_date": date(1990, 11, 14),
                "gender": "FEMALE",
                "service_class": "CLASS_2",
                "membership_status": "ACTIVE",
            },
            {
                "email": "bambang.sutrisno@sehatwarga.test",
                "name": "Bambang Sutrisno",
                "participant_number": "SW-2026-DEMO0020",
                "birth_date": date(1968, 8, 20),
                "gender": "MALE",
                "service_class": "CLASS_3",
                "membership_status": "INACTIVE",
            },
        ]

        user_map = {}
        participant_map = {}

        for cd in citizens_data:
            user = db.session.execute(
                select(User).filter_by(email=cd["email"])
            ).scalar_one_or_none()

            if not user:
                user = User(
                    name=cd["name"],
                    email=cd["email"],
                    role="citizen",
                    is_active=True,
                )
                user.set_password(effective_citizen_pwd)
                db.session.add(user)
                db.session.flush()

                part = Participant(
                    user_id=user.id,
                    participant_number=cd["participant_number"],
                    full_name=cd["name"],
                    birth_date=cd["birth_date"],
                    gender=cd["gender"],
                    membership_status=cd["membership_status"],
                    service_class=cd["service_class"],
                    registered_at=datetime(2025, 10, 15, 8, 0, 0),
                )
                db.session.add(part)
                db.session.flush()
                stats["citizens"]["created"] += 1
            else:
                user.set_password(effective_citizen_pwd)
                part = user.participant
                if not part:
                    part = Participant(
                        user_id=user.id,
                        participant_number=cd["participant_number"],
                        full_name=cd["name"],
                        birth_date=cd["birth_date"],
                        gender=cd["gender"],
                        membership_status=cd["membership_status"],
                        service_class=cd["service_class"],
                        registered_at=datetime(2025, 10, 15, 8, 0, 0),
                    )
                    db.session.add(part)
                    db.session.flush()
                    stats["citizens"]["created"] += 1
                else:
                    stats["citizens"]["existing"] += 1

            user_map[cd["email"]] = user
            participant_map[cd["email"]] = part

        # =====================================================================
        # 4. FAMILY MEMBERS (28+ members across participants)
        # =====================================================================
        family_data = [
            # Warga Demo (citizen 1)
            {
                "citizen_email": "warga.demo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0001",
                "full_name": "Anggota Demo Satu (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2018, 5, 20),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "warga.demo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0002",
                "full_name": "Anggota Demo Dua (Pasangan)",
                "relationship": "SPOUSE",
                "birth_date": date(1992, 4, 15),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "warga.demo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0003",
                "full_name": "Hj. Sulastri (Ibu)",
                "relationship": "PARENT",
                "birth_date": date(1962, 5, 10),
                "gender": "FEMALE",
            },
            # Budi Santoso (citizen 2)
            {
                "citizen_email": "budi.santoso@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0004",
                "full_name": "Ratna Indah (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1987, 3, 15),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "budi.santoso@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0005",
                "full_name": "Dimas Bagus Pratama (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2012, 7, 20),
                "gender": "MALE",
            },
            {
                "citizen_email": "budi.santoso@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0006",
                "full_name": "Anisa Citra Lestari (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2016, 11, 4),
                "gender": "FEMALE",
            },
            # Siti Aminah (citizen 3)
            {
                "citizen_email": "siti.aminah@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0007",
                "full_name": "Arif Rahman (Suami)",
                "relationship": "SPOUSE",
                "birth_date": date(1985, 9, 12),
                "gender": "MALE",
            },
            {
                "citizen_email": "siti.aminah@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0008",
                "full_name": "Rizky Fauzan (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2015, 2, 18),
                "gender": "MALE",
            },
            # Ahmad Dahlan (citizen 4)
            {
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0009",
                "full_name": "Fatimah Zahra (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1982, 1, 25),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0010",
                "full_name": "Bilal Ahmad (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2010, 6, 30),
                "gender": "MALE",
            },
            {
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0011",
                "full_name": "Maryam Ahmad (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2014, 8, 14),
                "gender": "FEMALE",
            },
            # Dewi Lestari (citizen 5)
            {
                "citizen_email": "dewi.lestari@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0012",
                "full_name": "Soeprapto (Ayah)",
                "relationship": "PARENT",
                "birth_date": date(1960, 4, 10),
                "gender": "MALE",
            },
            # Hendra Wijaya (citizen 6)
            {
                "citizen_email": "hendra.wijaya@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0013",
                "full_name": "Linda Novita (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1985, 12, 1),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "hendra.wijaya@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0014",
                "full_name": "Kevin Wijaya (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2013, 5, 17),
                "gender": "MALE",
            },
            # Rina Kartika (citizen 7)
            {
                "citizen_email": "rina.kartika@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0015",
                "full_name": "Endang Sunarni (Ibu)",
                "relationship": "PARENT",
                "birth_date": date(1965, 10, 18),
                "gender": "FEMALE",
            },
            # Agus Setiawan (citizen 8)
            {
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0016",
                "full_name": "Sri Wahyuni (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1978, 8, 8),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0017",
                "full_name": "Bayu Setiawan (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2008, 3, 22),
                "gender": "MALE",
            },
            {
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0018",
                "full_name": "Tiara Setiawan (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2011, 9, 15),
                "gender": "FEMALE",
            },
            # Maya Safitri (citizen 9)
            {
                "citizen_email": "maya.safitri@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0019",
                "full_name": "Danang Prakoso (Suami)",
                "relationship": "SPOUSE",
                "birth_date": date(1989, 2, 28),
                "gender": "MALE",
            },
            {
                "citizen_email": "maya.safitri@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0020",
                "full_name": "Alika Putri (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2019, 10, 12),
                "gender": "FEMALE",
            },
            # Fajar Nugroho (citizen 10)
            {
                "citizen_email": "fajar.nugroho@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0021",
                "full_name": "Wulan Anggraeni (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1989, 7, 4),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "fajar.nugroho@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0022",
                "full_name": "Raffa Nugroho (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2018, 1, 20),
                "gender": "MALE",
            },
            # Dian Kusuma (citizen 11)
            {
                "citizen_email": "dian.kusuma@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0023",
                "full_name": "Suwandi (Ayah)",
                "relationship": "PARENT",
                "birth_date": date(1963, 12, 7),
                "gender": "MALE",
            },
            # Joko Prasetyo (citizen 12)
            {
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0024",
                "full_name": "Retno Palupi (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1983, 4, 19),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0025",
                "full_name": "Aditya Prasetyo (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2011, 8, 26),
                "gender": "MALE",
            },
            {
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0026",
                "full_name": "Nayla Prasetyo (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2017, 3, 9),
                "gender": "FEMALE",
            },
            # Nurul Hidayati (citizen 13)
            {
                "citizen_email": "nurul.hidayati@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0027",
                "full_name": "Syamsul Ma'arif (Suami)",
                "relationship": "SPOUSE",
                "birth_date": date(1986, 11, 15),
                "gender": "MALE",
            },
            {
                "citizen_email": "nurul.hidayati@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0028",
                "full_name": "Farhan Ma'arif (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2016, 6, 21),
                "gender": "MALE",
            },
            # Eka Putra (citizen 14)
            {
                "citizen_email": "eka.putra@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0029",
                "full_name": "Sunarti (Ibu)",
                "relationship": "PARENT",
                "birth_date": date(1969, 2, 14),
                "gender": "FEMALE",
            },
            # Gita Pertiwi (citizen 15)
            {
                "citizen_email": "gita.pertiwi@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0030",
                "full_name": "Reza Pratama (Suami)",
                "relationship": "SPOUSE",
                "birth_date": date(1990, 10, 2),
                "gender": "MALE",
            },
            # Hadi Firmansyah (citizen 16)
            {
                "citizen_email": "hadi.firmansyah@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0031",
                "full_name": "Novita Dewi (Istri)",
                "relationship": "SPOUSE",
                "birth_date": date(1986, 6, 18),
                "gender": "FEMALE",
            },
            {
                "citizen_email": "hadi.firmansyah@sehatwarga.test",
                "member_number": "SWF-2026-DEMO0032",
                "full_name": "Kenzo Firmansyah (Anak)",
                "relationship": "CHILD",
                "birth_date": date(2017, 12, 5),
                "gender": "MALE",
            },
        ]

        family_map = {}
        for fmd in family_data:
            part = participant_map.get(fmd["citizen_email"])
            if not part:
                continue

            # Identify existing by member_number or (participant_id, full_name)
            existing_fm = db.session.execute(
                select(FamilyMember).filter(
                    (FamilyMember.member_number == fmd["member_number"])
                    | (
                        (FamilyMember.participant_id == part.id)
                        & (FamilyMember.full_name == fmd["full_name"])
                    )
                )
            ).scalar_one_or_none()

            if not existing_fm:
                existing_fm = FamilyMember(
                    participant_id=part.id,
                    member_number=fmd["member_number"],
                    full_name=fmd["full_name"],
                    relationship=fmd["relationship"],
                    birth_date=fmd["birth_date"],
                    gender=fmd["gender"],
                    membership_status="ACTIVE",
                )
                db.session.add(existing_fm)
                db.session.flush()
                stats["family_members"]["created"] += 1
            else:
                stats["family_members"]["existing"] += 1

            family_map[fmd["member_number"]] = existing_fm

        # =====================================================================
        # 5. SERVICE REQUESTS & SERVICE HISTORIES (~40 total across citizens)
        # =====================================================================
        services_definitions = [
            # Budi Santoso (citizen 2)
            {
                "request_number": "SWR-20260901-DEMO0001",
                "citizen_email": "budi.santoso@sehatwarga.test",
                "facility_code": "FS-SBY-001",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 20),
                "complaint_summary": "Pemeriksaan kesehatan umum rutin dan evaluasi tensi darah kerja berkala.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 15, 9, 30, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0002",
                "citizen_email": "budi.santoso@sehatwarga.test",
                "facility_code": "FS-SBY-004",
                "service_type": "DENTAL",
                "family_member_number": "SWF-2026-DEMO0005",
                "scheduled_date": date(2026, 9, 25),
                "complaint_summary": "Pemeriksaan kesehatan gigi anak dan penambalan gigi berlubang ringan.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 15, 10, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0003",
                "citizen_email": "budi.santoso@sehatwarga.test",
                "facility_code": "FS-SBY-002",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 28),
                "complaint_summary": "Konsultasi rujukan lanjutan poli spesialis mata untuk pemeriksaan berkala.",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 18, 11, 20, 0),
            },
            # Siti Aminah (citizen 3)
            {
                "request_number": "SWR-20260901-DEMO0004",
                "citizen_email": "siti.aminah@sehatwarga.test",
                "facility_code": "FS-SBY-001",
                "service_type": "MATERNAL",
                "family_member_number": "SWF-2026-DEMO0008",
                "scheduled_date": date(2026, 8, 25),
                "complaint_summary": "Pemeriksaan tumbuh kembang anak dan imunisasi booster balita.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 20, 8, 15, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0005",
                "citizen_email": "siti.aminah@sehatwarga.test",
                "facility_code": "FS-SBY-003",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 24),
                "complaint_summary": "Konsultasi keluhan migrain berulang dan pemeriksaan asam urat.",
                "status": "VERIFIED",
                "created_at": datetime(2026, 9, 16, 14, 0, 0),
            },
            # Ahmad Dahlan (citizen 4)
            {
                "request_number": "SWR-20260901-DEMO0006",
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "facility_code": "FS-SBY-002",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 10),
                "complaint_summary": "Pemeriksaan kardiologi berkala dan evaluasi hasil rekam jantung EKG.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 5, 8, 30, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0007",
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "facility_code": "FS-SBY-001",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0010",
                "scheduled_date": date(2026, 9, 26),
                "complaint_summary": "Pemeriksaan demam dan batuk pilek pada anak remaja.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 14, 11, 45, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0008",
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "facility_code": "FS-SBY-004",
                "service_type": "DENTAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 29),
                "complaint_summary": "Pembersihan karang gigi scaling dan konsultasi gusi berdarah.",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 19, 9, 0, 0),
            },
            # Dewi Lestari (citizen 5)
            {
                "request_number": "SWR-20260901-DEMO0009",
                "citizen_email": "dewi.lestari@sehatwarga.test",
                "facility_code": "FS-SDA-005",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0012",
                "scheduled_date": date(2026, 8, 18),
                "complaint_summary": "Pemeriksaan kesehatan lansia berkala untuk ayah dan cek gula darah.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 12, 10, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0010",
                "citizen_email": "dewi.lestari@sehatwarga.test",
                "facility_code": "FS-SDA-005",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 25),
                "complaint_summary": "Pemeriksaan alergi kulit dan gatal-gatal pada lengan.",
                "status": "VERIFIED",
                "created_at": datetime(2026, 9, 17, 13, 30, 0),
            },
            # Hendra Wijaya (citizen 6)
            {
                "request_number": "SWR-20260901-DEMO0011",
                "citizen_email": "hendra.wijaya@sehatwarga.test",
                "facility_code": "FS-SDA-006",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 28),
                "complaint_summary": "Pemeriksaan ortopedi untuk keluhan nyeri lutut setelah berolahraga.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 22, 15, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0012",
                "citizen_email": "hendra.wijaya@sehatwarga.test",
                "facility_code": "FS-SDA-011",
                "service_type": "DENTAL",
                "family_member_number": "SWF-2026-DEMO0014",
                "scheduled_date": date(2026, 9, 23),
                "complaint_summary": "Pencabutan gigi susu anak yang sudah goyang.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 12, 10, 15, 0),
            },
            # Rina Kartika (citizen 7)
            {
                "request_number": "SWR-20260901-DEMO0013",
                "citizen_email": "rina.kartika@sehatwarga.test",
                "facility_code": "FS-SBY-008",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0015",
                "scheduled_date": date(2026, 8, 14),
                "complaint_summary": "Pemeriksaan tekanan darah dan resep obat hipertensi rutin ibu.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 9, 8, 45, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0014",
                "citizen_email": "rina.kartika@sehatwarga.test",
                "facility_code": "FS-SBY-008",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 27),
                "complaint_summary": "Pemeriksaan kelelahan kronis dan tes darah anemia.",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 19, 14, 20, 0),
            },
            # Agus Setiawan (citizen 8)
            {
                "request_number": "SWR-20260901-DEMO0015",
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "facility_code": "FS-SBY-002",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 8),
                "complaint_summary": "Pemeriksaan gastroenterologi untuk gangguan pencernaan menahun.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 2, 9, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0016",
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "facility_code": "FS-SBY-003",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0017",
                "scheduled_date": date(2026, 9, 25),
                "complaint_summary": "Pemeriksaan kesehatan remaja dan surat keterangan sehat sekolah.",
                "status": "VERIFIED",
                "created_at": datetime(2026, 9, 15, 8, 30, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0017",
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "facility_code": "FS-SBY-004",
                "service_type": "DENTAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 20),
                "complaint_summary": "Permohonan pemasangan kawat gigi estetik bukan indikasi medis.",
                "status": "REJECTED",
                "created_at": datetime(2026, 9, 10, 11, 0, 0),
            },
            # Maya Safitri (citizen 9)
            {
                "request_number": "SWR-20260901-DEMO0018",
                "citizen_email": "maya.safitri@sehatwarga.test",
                "facility_code": "FS-SBY-009",
                "service_type": "MATERNAL",
                "family_member_number": "SWF-2026-DEMO0020",
                "scheduled_date": date(2026, 8, 29),
                "complaint_summary": "Pemeriksaan alergi pernapasan pada balita di poli anak.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 24, 10, 30, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0019",
                "citizen_email": "maya.safitri@sehatwarga.test",
                "facility_code": "FS-SBY-001",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 24),
                "complaint_summary": "Pemeriksaan radang tenggorokan dan batuk kering.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 13, 14, 0, 0),
            },
            # Fajar Nugroho (citizen 10)
            {
                "request_number": "SWR-20260901-DEMO0020",
                "citizen_email": "fajar.nugroho@sehatwarga.test",
                "facility_code": "FS-SDA-005",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 22),
                "complaint_summary": "Pemeriksaan influenza dan pemulihan stamina pasca sakit.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 17, 9, 15, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0021",
                "citizen_email": "fajar.nugroho@sehatwarga.test",
                "facility_code": "FS-SDA-006",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 21),
                "complaint_summary": "Permohonan jadwal ulang di luar kota sehingga permohonan dibatalkan peserta.",
                "status": "CANCELLED",
                "created_at": datetime(2026, 9, 11, 16, 0, 0),
            },
            # Dian Kusuma (citizen 11)
            {
                "request_number": "SWR-20260901-DEMO0022",
                "citizen_email": "dian.kusuma@sehatwarga.test",
                "facility_code": "FS-GRS-013",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0023",
                "scheduled_date": date(2026, 9, 26),
                "complaint_summary": "Pemeriksaan keluhan rematik sendi pada ayah.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 14, 9, 0, 0),
            },
            # Joko Prasetyo (citizen 12)
            {
                "request_number": "SWR-20260901-DEMO0023",
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "facility_code": "FS-GRS-014",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 16),
                "complaint_summary": "Pemeriksaan neurologi untuk keluhan pusing vertigo berkepanjangan.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 10, 10, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0024",
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "facility_code": "FS-GRS-015",
                "service_type": "CLINIC" if "CLINIC" in [f.facility_type for f in facility_map.values()] else "GENERAL",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0025",
                "scheduled_date": date(2026, 9, 28),
                "complaint_summary": "Pemeriksaan demam dan batuk anak di klinik terdekat.",
                "status": "VERIFIED",
                "created_at": datetime(2026, 9, 18, 15, 30, 0),
            },
            # Nurul Hidayati (citizen 13)
            {
                "request_number": "SWR-20260901-DEMO0025",
                "citizen_email": "nurul.hidayati@sehatwarga.test",
                "facility_code": "FS-LMG-016",
                "service_type": "MATERNAL",
                "family_member_number": "SWF-2026-DEMO0028",
                "scheduled_date": date(2026, 8, 30),
                "complaint_summary": "Pemeriksaan gizi anak dan penimbangan berat badan berkala.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 25, 8, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0026",
                "citizen_email": "nurul.hidayati@sehatwarga.test",
                "facility_code": "FS-LMG-016",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 27),
                "complaint_summary": "Pemeriksaan mata kabur dan rujukan kacamata.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 15, 11, 15, 0),
            },
            # Eka Putra (citizen 14)
            {
                "request_number": "SWR-20260901-DEMO0027",
                "citizen_email": "eka.putra@sehatwarga.test",
                "facility_code": "FS-MJK-018",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0029",
                "scheduled_date": date(2026, 9, 30),
                "complaint_summary": "Pemeriksaan kolesterol dan tekanan darah ibu.",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 20, 8, 20, 0),
            },
            # Gita Pertiwi (citizen 15)
            {
                "request_number": "SWR-20260901-DEMO0028",
                "citizen_email": "gita.pertiwi@sehatwarga.test",
                "facility_code": "FS-MJK-019",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 26),
                "complaint_summary": "Pemeriksaan dermatologi untuk infeksi kulit dermatitis.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 21, 13, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0029",
                "citizen_email": "gita.pertiwi@sehatwarga.test",
                "facility_code": "FS-MJK-020",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 26),
                "complaint_summary": "Konsultasi keluhan lambung dispepsia dan maag akut.",
                "status": "VERIFIED",
                "created_at": datetime(2026, 9, 16, 9, 45, 0),
            },
            # Hadi Firmansyah (citizen 16)
            {
                "request_number": "SWR-20260901-DEMO0030",
                "citizen_email": "hadi.firmansyah@sehatwarga.test",
                "facility_code": "FS-JBG-021",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 19),
                "complaint_summary": "Pemeriksaan fisik dan tensi darah berkala.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 14, 10, 0, 0),
            },
            {
                "request_number": "SWR-20260901-DEMO0031",
                "citizen_email": "hadi.firmansyah@sehatwarga.test",
                "facility_code": "FS-JBG-022",
                "service_type": "SPECIALIST",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 15),
                "complaint_summary": "Permohonan layanan rujukan spesialis tanpa surat rujukan primer FKTP.",
                "status": "REJECTED",
                "created_at": datetime(2026, 9, 10, 8, 30, 0),
            },
            # Kartika Wulandari (citizen 17)
            {
                "request_number": "SWR-20260901-DEMO0032",
                "citizen_email": "kartika.wulandari@sehatwarga.test",
                "facility_code": "FS-MLG-007",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 29),
                "complaint_summary": "Pemeriksaan flu dan sakit kepala musiman.",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 19, 16, 0, 0),
            },
            # Lukman Hakim (citizen 18)
            {
                "request_number": "SWR-20260901-DEMO0033",
                "citizen_email": "lukman.hakim@sehatwarga.test",
                "facility_code": "FS-MLG-024",
                "service_type": "DENTAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 9, 24),
                "complaint_summary": "Pembersihan karang gigi dan penanganan ngilu saat minum dingin.",
                "status": "SCHEDULED",
                "created_at": datetime(2026, 9, 14, 14, 10, 0),
            },
            # Tri Wahyuni (citizen 19)
            {
                "request_number": "SWR-20260901-DEMO0034",
                "citizen_email": "tri.wahyuni@sehatwarga.test",
                "facility_code": "FS-PAS-025",
                "service_type": "GENERAL",
                "family_member_number": None,
                "scheduled_date": date(2026, 8, 27),
                "complaint_summary": "Pemeriksaan kesehatan berkala dan cek asam urat.",
                "status": "COMPLETED",
                "created_at": datetime(2026, 8, 22, 11, 0, 0),
            },
            # Additional SUBMITTED request for Warga Demo
            {
                "request_number": "SWR-20260901-DEMO0035",
                "citizen_email": "warga.demo@sehatwarga.test",
                "facility_code": "FS-SBY-001",
                "service_type": "GENERAL",
                "family_member_number": "SWF-2026-DEMO0003",
                "scheduled_date": date(2026, 9, 30),
                "complaint_summary": "Pemeriksaan kesehatan rutin untuk ibu tercinta (Hj. Sulastri).",
                "status": "SUBMITTED",
                "created_at": datetime(2026, 9, 20, 7, 0, 0),
            },
        ]

        for sd in services_definitions:
            part = participant_map.get(sd["citizen_email"])
            fac = facility_map.get(sd["facility_code"])
            if not part or not fac:
                continue

            fm = family_map.get(sd["family_member_number"]) if sd["family_member_number"] else None

            sr = db.session.execute(
                select(ServiceRequest).filter_by(request_number=sd["request_number"])
            ).scalar_one_or_none()

            if not sr:
                sr = ServiceRequest(
                    request_number=sd["request_number"],
                    participant_id=part.id,
                    family_member_id=fm.id if fm else None,
                    health_facility_id=fac.id,
                    service_type=sd["service_type"],
                    scheduled_date=sd["scheduled_date"],
                    complaint_summary=sd["complaint_summary"],
                    status=sd["status"],
                    created_at=sd["created_at"],
                    updated_at=sd["created_at"],
                )
                db.session.add(sr)
                db.session.flush()
                stats["service_requests"]["created"] += 1

                # Generate matching chronological history log
                hist_entries = []
                # Always starts with SUBMITTED
                hist_entries.append({
                    "status": "SUBMITTED",
                    "note": "Pengajuan layanan dibuat oleh peserta.",
                    "changed_by": part.user_id,
                    "created_at": sd["created_at"],
                })

                if sd["status"] == "VERIFIED":
                    hist_entries.append({
                        "status": "VERIFIED",
                        "note": "Berkas identitas dan kepesertaan diverifikasi lengkap oleh petugas.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=2),
                    })
                elif sd["status"] == "SCHEDULED":
                    hist_entries.append({
                        "status": "VERIFIED",
                        "note": "Berkas kepesertaan diverifikasi lengkap.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=2),
                    })
                    hist_entries.append({
                        "status": "SCHEDULED",
                        "note": f"Jadwal layanan ditetapkan pada {sd['scheduled_date'].strftime('%d/%m/%Y')}.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=5),
                    })
                elif sd["status"] == "COMPLETED":
                    hist_entries.append({
                        "status": "VERIFIED",
                        "note": "Berkas kepesertaan diverifikasi lengkap.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=2),
                    })
                    hist_entries.append({
                        "status": "SCHEDULED",
                        "note": f"Jadwal layanan ditetapkan pada {sd['scheduled_date'].strftime('%d/%m/%Y')}.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=5),
                    })
                    hist_entries.append({
                        "status": "COMPLETED",
                        "note": "Pelayanan kesehatan simulasi telah tuntas dilaksanakan dengan baik.",
                        "changed_by": admin_user.id,
                        "created_at": datetime.combine(sd["scheduled_date"], datetime.min.time()) + timedelta(hours=11),
                    })
                elif sd["status"] == "REJECTED":
                    hist_entries.append({
                        "status": "REJECTED",
                        "note": "Pengajuan ditolak karena persyaratan administratif medis belum terpenuhi.",
                        "changed_by": admin_user.id,
                        "created_at": sd["created_at"] + timedelta(hours=4),
                    })
                elif sd["status"] == "CANCELLED":
                    hist_entries.append({
                        "status": "CANCELLED",
                        "note": "Pengajuan dibatalkan atas permohonan pemohon layanan.",
                        "changed_by": part.user_id,
                        "created_at": sd["created_at"] + timedelta(hours=3),
                    })

                for he in hist_entries:
                    sh = ServiceHistory(
                        service_request_id=sr.id,
                        status=he["status"],
                        note=he["note"],
                        changed_by=he["changed_by"],
                        created_at=he["created_at"],
                    )
                    db.session.add(sh)
                    stats["service_histories"]["created"] += 1
            else:
                stats["service_requests"]["existing"] += 1

        # =====================================================================
        # 6. CONTRIBUTIONS & PAYMENTS (6 months for active participants)
        # =====================================================================
        # Periods: 2026-04-01 to 2026-09-01
        billing_months = [
            date(2026, 4, 1),
            date(2026, 5, 1),
            date(2026, 6, 1),
            date(2026, 7, 1),
            date(2026, 8, 1),
            date(2026, 9, 1),
        ]

        payment_methods_cycle = [
            "SIMULATION_TRANSFER",
            "SIMULATION_VIRTUAL_ACCOUNT",
            "SIMULATION_CASH",
        ]

        # Process each active participant
        active_participants = [
            (email, part) for email, part in participant_map.items()
            if part.membership_status == "ACTIVE"
        ]

        payment_seq = 100
        for p_idx, (email, part) in enumerate(active_participants):
            amount = SIMULATED_RATES.get(part.service_class, Decimal("100000.00"))

            for m_idx, b_period in enumerate(billing_months):
                due_date = date(b_period.year, b_period.month, 10)

                # Determine status:
                # Months 0-3 (Apr-Jul): ALL PAID
                # Month 4 (Aug): participants with p_idx % 6 == 0 are OVERDUE, others PAID
                # Month 5 (Sep, current): participants with p_idx % 2 == 0 are UNPAID, others PAID
                if m_idx < 4:
                    target_status = "PAID"
                elif m_idx == 4:  # Aug
                    target_status = "OVERDUE" if (p_idx % 6 == 0) else "PAID"
                else:  # Sep
                    target_status = "UNPAID" if (p_idx % 2 == 0) else "PAID"

                # Check existing contribution
                contrib = db.session.execute(
                    select(Contribution).filter_by(
                        participant_id=part.id, billing_period=b_period
                    )
                ).scalar_one_or_none()

                if not contrib:
                    contrib = Contribution(
                        participant_id=part.id,
                        billing_period=b_period,
                        amount=amount,
                        status=target_status,
                        due_date=due_date,
                        created_at=datetime(b_period.year, b_period.month, 1, 6, 0, 0),
                        updated_at=datetime(b_period.year, b_period.month, 1, 6, 0, 0),
                    )
                    db.session.add(contrib)
                    db.session.flush()
                    stats["contributions"]["created"] += 1
                else:
                    stats["contributions"]["existing"] += 1

                # If status is PAID, ensure a matching successful payment exists
                if contrib.status == "PAID":
                    has_success_payment = any(
                        p.status == "SUCCESS" for p in contrib.payments
                    )
                    if not has_success_payment:
                        payment_seq += 1
                        pay_num = f"SWP-{b_period.strftime('%Y%m')}-DEMO{payment_seq:04d}"
                        method = payment_methods_cycle[(p_idx + m_idx) % len(payment_methods_cycle)]
                        paid_dt = datetime(
                            b_period.year, b_period.month, 5, 9, (p_idx * 3) % 60, 0
                        )

                        pmt = Payment(
                            contribution_id=contrib.id,
                            payment_number=pay_num,
                            amount=contrib.amount,
                            payment_method=method,
                            status="SUCCESS",
                            paid_at=paid_dt,
                            created_at=paid_dt,
                        )
                        db.session.add(pmt)
                        db.session.flush()
                        stats["payments"]["created"] += 1
                    else:
                        stats["payments"]["existing"] += 1

        # =====================================================================
        # 7. COMPLAINTS (16 varied realistic complaints)
        # =====================================================================
        complaints_data = [
            {
                "ticket_number": "SWT-202609-DEMO0001",
                "citizen_email": "budi.santoso@sehatwarga.test",
                "subject": "Perubahan fasilitas rujukan tingkat pertama setelah pindah domisili",
                "message": "Selamat pagi tim admin SehatWarga. Saya baru saja pindah domisili ke wilayah Rungkut Surabaya. Apakah alur perubahan faskes primer keluarga dapat dilakukan sepenuhnya melalui portal digital?",
                "status": "RESOLVED",
                "admin_response": "Selamat pagi Bapak Budi. Perubahan fasilitas rujukan tingkat pertama dapat diajukan langsung melalui profil peserta atau pengajuan layanan dengan memilih fasilitas baru di wilayah Rungkut. Data telah kami perbarui.",
                "created_at": datetime(2026, 9, 2, 9, 15, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0002",
                "citizen_email": "siti.aminah@sehatwarga.test",
                "subject": "Sinkronisasi data kepesertaan tanggungan anak yang baru lahir",
                "message": "Halo admin, saya ingin mendaftarkan anak kedua kami ke dalam data tanggungan keluarga. Dokumen akta dan KK simulasi sudah kami siapkan. Mohon petunjuk proses verifikasinya.",
                "status": "RESOLVED",
                "admin_response": "Halo Ibu Siti Aminah. Pendaftaran anggota keluarga baru telah berhasil diverifikasi oleh sistem. Nomor kepesertaan keluarga telah aktif dan dapat digunakan untuk pengajuan layanan.",
                "created_at": datetime(2026, 9, 3, 10, 30, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0003",
                "citizen_email": "ahmad.dahlan@sehatwarga.test",
                "subject": "Jadwal poli spesialis penyakit dalam di RS rujukan",
                "message": "Mohon informasi jam praktik dokter spesialis kardiologi di RS Umum Simulasi SehatWarga Utama pada hari Sabtu apakah tetap membuka pelayanan poli rawat jalan?",
                "status": "IN_PROGRESS",
                "admin_response": None,
                "created_at": datetime(2026, 9, 16, 11, 0, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0004",
                "citizen_email": "dewi.lestari@sehatwarga.test",
                "subject": "Pertanyaan mengenai cetak kartu fisik vs kartu digital SehatWarga",
                "message": "Apakah kartu digital ber-barcode yang tertera di menu Kartu Peserta sudah cukup sah untuk proses verifikasi di puskesmas tanpa harus mencetak kartu fisik?",
                "status": "RESOLVED",
                "admin_response": "Benar Ibu Dewi. Kartu kepesertaan digital SehatWarga dilengkapi barcode resmi dan diakui secara penuh di seluruh fasilitas kesehatan mitra simulasi tanpa perlu mencetak fisik.",
                "created_at": datetime(2026, 9, 5, 14, 20, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0005",
                "citizen_email": "hendra.wijaya@sehatwarga.test",
                "subject": "Kendala konfirmasi pembayaran simulasi via virtual account",
                "message": "Saya sudah melakukan transaksi pembayaran simulasi tagihan bulan Agustus melalui Virtual Account, namun status sempat tertunda beberapa menit. Mohon konfirmasi kelunasannya.",
                "status": "RESOLVED",
                "admin_response": "Terima kasih atas konfirmasinya Bapak Hendra. Pembayaran simulasi Anda telah terverifikasi lunas di sistem kami dengan nomor bukti transaksi valid.",
                "created_at": datetime(2026, 9, 6, 16, 45, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0006",
                "citizen_email": "rina.kartika@sehatwarga.test",
                "subject": "Permohonan penambahan anggota keluarga orang tua lansia",
                "message": "Apakah orang tua yang tinggal satu domisili dapat ditambahkan ke dalam daftar tanggungan keluarga peserta mandiri kelas 3?",
                "status": "IN_PROGRESS",
                "admin_response": None,
                "created_at": datetime(2026, 9, 17, 8, 30, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0007",
                "citizen_email": "agus.setiawan@sehatwarga.test",
                "subject": "Informasi jam operasional poli gigi di Puskesmas Kebomas",
                "message": "Apakah pendaftaran poli gigi di Puskesmas Kebomas Gresik melayani antrean daring pada pagi hari mulai jam 07.30?",
                "status": "RESOLVED",
                "admin_response": "Poli gigi Puskesmas Kebomas beroperasi mulai pukul 08.00 - 14.00 WIB setiap hari kerja. Pengajuan antrean dapat dilakukan H-1 melalui portal SehatWarga.",
                "created_at": datetime(2026, 9, 7, 9, 50, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0008",
                "citizen_email": "maya.safitri@sehatwarga.test",
                "subject": "Antrean layanan rujukan rawat jalan yang cukup padat",
                "message": "Saat berkunjung ke RS Simulasi Surabaya Timur, antrean poli anak cukup padat pada pagi hari. Mohon peningkatan kuota antrean digital per sesi agar lebih merata.",
                "status": "OPEN",
                "admin_response": None,
                "created_at": datetime(2026, 9, 19, 10, 15, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0009",
                "citizen_email": "fajar.nugroho@sehatwarga.test",
                "subject": "Permintaan perbaikan penulisan nama peserta pada kartu digital",
                "message": "Terdapat kesalahan satu huruf pada penulisan nama tengah saya di kartu peserta. Mohon bantuan petugas admin untuk melakukan koreksi ejaan.",
                "status": "IN_PROGRESS",
                "admin_response": None,
                "created_at": datetime(2026, 9, 18, 13, 0, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0010",
                "citizen_email": "dian.kusuma@sehatwarga.test",
                "subject": "Klarifikasi status tagihan bulan Agustus yang sempat tercatat terlambat",
                "message": "Tagihan bulan Agustus tercatat terlambat padahal pembayaran sudah dilakukan sebelum batas tanggal 10. Mohon pengecekan mutasi simulasi sistem.",
                "status": "RESOLVED",
                "admin_response": "Klarifikasi status telah dilakukan. Riwayat transaksi berhasil disinkronkan dan status tagihan telah diperbarui menjadi lunas.",
                "created_at": datetime(2026, 9, 9, 15, 20, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0011",
                "citizen_email": "joko.prasetyo@sehatwarga.test",
                "subject": "Pertanyaan ketersediaan dokter spesialis anak di RS Medika Sidoarjo",
                "message": "Mohon info apakah RS Medika Sidoarjo memiliki poliklinik tumbuh kembang anak khusus untuk konsultasi wicara balita?",
                "status": "RESOLVED",
                "admin_response": "RS Khusus Simulasi SehatWarga Medika Sidoarjo melayani klinik tumbuh kembang anak pada hari Selasa dan Kamis dengan perjanjian awal melalui portal SehatWarga.",
                "created_at": datetime(2026, 9, 10, 11, 40, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0012",
                "citizen_email": "nurul.hidayati@sehatwarga.test",
                "subject": "Kendala akses riwayat pelayanan kesehatan pada perangkat seluler",
                "message": "Halaman riwayat pengajuan sempat lambat dimuat saat menggunakan jaringan seluler di area Lamongan. Mohon optimasi performa muat halaman.",
                "status": "OPEN",
                "admin_response": None,
                "created_at": datetime(2026, 9, 20, 8, 45, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0013",
                "citizen_email": "gita.pertiwi@sehatwarga.test",
                "subject": "Prosedur pengalihan kelas layanan kepesertaan mandiri",
                "message": "Bagaimana ketentuan untuk melakukan peningkatan kelas kepesertaan dari Kelas 2 ke Kelas 1 bagi peserta mandiri aktif?",
                "status": "IN_PROGRESS",
                "admin_response": None,
                "created_at": datetime(2026, 9, 18, 16, 10, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0014",
                "citizen_email": "hadi.firmansyah@sehatwarga.test",
                "subject": "Pengajuan penggantian fasilitas kesehatan ditolak tanpa penjelasan",
                "message": "Pengajuan layanan rujukan spesialis saya kemarin mendapat status penolakan. Mohon penjelasan lebih rinci mengenai alasan penolakannya.",
                "status": "RESOLVED",
                "admin_response": "Penolakan terjadi karena rujukan spesialis memerlukan surat rujukan aktif dari faskes tingkat pertama (FKTP) Anda terlebih dahulu. Silakan kunjungi FKTP terlebih dahulu.",
                "created_at": datetime(2026, 9, 12, 14, 0, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0015",
                "citizen_email": "lukman.hakim@sehatwarga.test",
                "subject": "Apresiasi respon cepat Asisten SehatWarga pada rekomendasi faskes",
                "message": "Fitur Asisten AI SehatWarga sangat membantu saya menemukan faskes terdekat di wilayah Malang secara akurat. Terima kasih atas inovasinya.",
                "status": "OPEN",
                "admin_response": None,
                "created_at": datetime(2026, 9, 19, 17, 30, 0),
            },
            {
                "ticket_number": "SWT-202609-DEMO0016",
                "citizen_email": "eka.putra@sehatwarga.test",
                "subject": "Permintaan pembatalan pengajuan ganda layanan poli umum",
                "message": "Saya tidak sengaja menekan tombol kirim dua kali saat mengajukan layanan umum. Mohon dibatalkan salah satunya.",
                "status": "REJECTED",
                "admin_response": "Pengaduan penutupan manual tidak dapat diproses via tiket karena peserta dapat langsung menggunakan tombol 'Batalkan Pengajuan' mandiri pada halaman detail pengajuan.",
                "created_at": datetime(2026, 9, 14, 10, 20, 0),
            },
        ]

        for cd in complaints_data:
            user = user_map.get(cd["citizen_email"])
            if not user:
                continue

            cmp_obj = db.session.execute(
                select(Complaint).filter_by(ticket_number=cd["ticket_number"])
            ).scalar_one_or_none()

            if not cmp_obj:
                cmp_obj = Complaint(
                    ticket_number=cd["ticket_number"],
                    user_id=user.id,
                    subject=cd["subject"],
                    message=cd["message"],
                    status=cd["status"],
                    admin_response=cd["admin_response"],
                    created_at=cd["created_at"],
                    updated_at=cd["created_at"],
                )
                db.session.add(cmp_obj)
                db.session.flush()
                stats["complaints"]["created"] += 1
            else:
                stats["complaints"]["existing"] += 1

        # =====================================================================
        # Commit entire transaction atomically
        # =====================================================================
        db.session.commit()

        click.echo("============================================================")
        click.echo("SEHATWARGA - FULL DEMO DATA SEEDER (TCC 2026)")
        click.echo("============================================================")
        click.echo(f"Admin Users       : {stats['admin']['created']} dibuat, {stats['admin']['existing']} sudah ada")
        click.echo(f"Citizens/Peserta  : {stats['citizens']['created']} dibuat, {stats['citizens']['existing']} sudah ada")
        click.echo(f"Anggota Keluarga  : {stats['family_members']['created']} dibuat, {stats['family_members']['existing']} sudah ada")
        click.echo(f"Fasilitas Faskes  : {stats['facilities']['created']} dibuat, {stats['facilities']['existing']} sudah ada")
        click.echo(f"Pengajuan Layanan : {stats['service_requests']['created']} dibuat, {stats['service_requests']['existing']} sudah ada")
        click.echo(f"Riwayat Layanan   : {stats['service_histories']['created']} dibuat, {stats['service_histories']['existing']} sudah ada")
        click.echo(f"Tagihan Iuran     : {stats['contributions']['created']} dibuat, {stats['contributions']['existing']} sudah ada")
        click.echo(f"Pembayaran Sukses : {stats['payments']['created']} dibuat, {stats['payments']['existing']} sudah ada")
        click.echo(f"Pengaduan Tiket   : {stats['complaints']['created']} dibuat, {stats['complaints']['existing']} sudah ada")
        click.echo("------------------------------------------------------------")
        click.echo("Akun Demo Siap Presentasi:")
        click.echo(f"  ADMINISTRATOR : {admin_email}")
        click.echo(f"  CITIZEN UTAMA : warga.demo@sehatwarga.test")
        click.echo("  Password demo : gunakan password yang diberikan melalui opsi CLI atau default Demo123!")
        click.echo("Status: SUKSES (Idempoten & Terhubung Sempurna).")
        click.echo("============================================================")

        return stats

    except Exception as e:
        db.session.rollback()
        click.echo(f"Error pada proses seed demo full: {e}", err=True)
        raise
