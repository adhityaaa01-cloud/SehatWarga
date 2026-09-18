import click
import getpass
from sqlalchemy import select
from app.extensions import db
from app.models.user import User


def register_cli_commands(app):
    @app.cli.command("create-admin")
    def create_admin():
        """Membuat akun administrator SehatWarga secara interaktif dan aman."""
        click.echo("=== Pembuatan Akun Administrator SehatWarga ===")
        name = click.prompt("Nama Lengkap Admin", type=str).strip()
        if not name:
            click.echo("Error: Nama tidak boleh kosong.", err=True)
            return

        email = click.prompt("Email Admin", type=str).strip().lower()
        if not email or "@" not in email:
            click.echo("Error: Format email tidak valid.", err=True)
            return

        # Check unique email
        existing = db.session.execute(
            select(User.id).filter_by(email=email)
        ).scalar_one_or_none()
        if existing:
            click.echo(f"Error: Pengguna dengan email '{email}' sudah terdaftar.", err=True)
            return

        password = getpass.getpass("Kata Sandi (minimal 8 karakter): ")
        if len(password) < 8:
            click.echo("Error: Kata sandi harus minimal 8 karakter.", err=True)
            return

        confirm_password = getpass.getpass("Konfirmasi Kata Sandi: ")
        if password != confirm_password:
            click.echo("Error: Konfirmasi kata sandi tidak cocok.", err=True)
            return

        try:
            admin_user = User(
                name=name,
                email=email,
                role="admin",
                is_active=True,
            )
            admin_user.set_password(password)
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Sukses: Akun admin '{email}' berhasil dibuat.")
        except Exception as e:
            db.session.rollback()
            click.echo(f"Error: Gagal membuat admin: {e}", err=True)

    @app.cli.command("seed-facilities")
    def seed_facilities():
        """Menambahkan data fasilitas kesehatan simulasi SehatWarga secara idempoten."""
        from app.models.health_facility import HealthFacility

        dummy_facilities = [
            {
                "facility_code": "FS-SBY-001",
                "name": "Puskesmas Simulasi SehatWarga Sentral",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Pemuda No. 12, Embong Kaliasin",
                "city": "Surabaya",
                "phone": "031-5312001",
                "latitude": -7.2655000,
                "longitude": 112.7518000,
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-002",
                "name": "Rumah Sakit Umum Simulasi SehatWarga Utama",
                "facility_type": "HOSPITAL",
                "address": "Jl. Dharmahusada No. 45, Gubeng",
                "city": "Surabaya",
                "phone": "031-5034002",
                "latitude": -7.2690000,
                "longitude": 112.7630000,
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-003",
                "name": "Klinik Pratama Simulasi SehatWarga Sejahtera",
                "facility_type": "CLINIC",
                "address": "Jl. Raya Darmo No. 88, Tegalsari",
                "city": "Surabaya",
                "phone": "031-5678003",
                "latitude": -7.2880000,
                "longitude": 112.7380000,
                "is_active": True,
            },
            {
                "facility_code": "FS-SBY-004",
                "name": "Klinik Gigi Simulasi SehatWarga Senyum Indah",
                "facility_type": "DENTAL_CLINIC",
                "address": "Jl. Mayjen Sungkono No. 102, Dukuh Pakis",
                "city": "Surabaya",
                "phone": "031-5621004",
                "latitude": -7.2915000,
                "longitude": 112.7150000,
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-005",
                "name": "Puskesmas Simulasi SehatWarga Waru",
                "facility_type": "PUSKESMAS",
                "address": "Jl. Raya Waru No. 15, Waru",
                "city": "Sidoarjo",
                "phone": "031-8532005",
                "latitude": -7.3550000,
                "longitude": 112.7480000,
                "is_active": True,
            },
            {
                "facility_code": "FS-SDA-006",
                "name": "Rumah Sakit Khusus Simulasi SehatWarga Medika",
                "facility_type": "HOSPITAL",
                "address": "Jl. Pahlawan No. 70, Sidokumpul",
                "city": "Sidoarjo",
                "phone": "031-8945006",
                "latitude": -7.4478000,
                "longitude": 112.7180000,
                "is_active": True,
            },
            {
                "facility_code": "FS-MLG-007",
                "name": "Klinik Pratama Simulasi SehatWarga Brawijaya",
                "facility_type": "CLINIC",
                "address": "Jl. Ijen No. 25, Klojen",
                "city": "Malang",
                "phone": "0341-367007",
                "latitude": -7.9730000,
                "longitude": 112.6240000,
                "is_active": True,
            },
        ]

        added_count = 0
        existing_count = 0

        for item in dummy_facilities:
            facility = db.session.execute(
                select(HealthFacility).filter_by(facility_code=item["facility_code"])
            ).scalar_one_or_none()

            if not facility:
                new_facility = HealthFacility(
                    facility_code=item["facility_code"],
                    name=item["name"],
                    facility_type=item["facility_type"],
                    address=item["address"],
                    city=item["city"],
                    phone=item["phone"],
                    latitude=item["latitude"],
                    longitude=item["longitude"],
                    is_active=item["is_active"],
                )
                db.session.add(new_facility)
                added_count += 1
            else:
                existing_count += 1

        db.session.commit()
        click.echo(
            f"Seed selesai: {added_count} fasilitas kesehatan baru ditambahkan, {existing_count} fasilitas sudah ada."
        )

    @app.cli.command("generate-contributions")
    @click.option("--month", default=None, help="Bulan tagihan format YYYY-MM (contoh: 2026-09). Default: bulan berjalan.")
    def generate_contributions_cmd(month):
        """Membuat tagihan iuran bulanan untuk seluruh peserta aktif secara idempoten."""
        from datetime import date, datetime
        from app.services.contribution_service import generate_contributions_for_active_participants

        target_date = None
        if month:
            try:
                parsed = datetime.strptime(month.strip(), "%Y-%m").date()
                target_date = date(parsed.year, parsed.month, 1)
            except ValueError:
                click.echo("Error: Format bulan tidak valid. Gunakan YYYY-MM (contoh: 2026-09).", err=True)
                return
        else:
            today = date.today()
            target_date = date(today.year, today.month, 1)

        result = generate_contributions_for_active_participants(target_date)
        period_str = result["period"].strftime("%B %Y")
        click.echo(
            f"Tagihan periode {period_str}: "
            f"{result['created']} dibuat, {result['skipped']} dilewati (sudah ada) "
            f"dari total {result['total_active']} peserta aktif."
        )

    @app.cli.command("update-overdue")
    @click.option("--as-of", default=None, help="Tanggal acuan evaluasi jatuh tempo format YYYY-MM-DD. Default: hari ini.")
    def update_overdue_cmd(as_of):
        """Memperbarui status tagihan yang belum dibayar dan melewati jatuh tempo menjadi OVERDUE."""
        from datetime import datetime
        from app.services.contribution_service import mark_overdue_contributions

        ref_date = None
        if as_of:
            try:
                ref_date = datetime.strptime(as_of.strip(), "%Y-%m-%d").date()
            except ValueError:
                click.echo("Error: Format tanggal tidak valid. Gunakan YYYY-MM-DD (contoh: 2026-09-15).", err=True)
                return

        count = mark_overdue_contributions(reference_date=ref_date)
        click.echo(f"Pembaruan status overdue selesai: {count} tagihan diperbarui menjadi OVERDUE.")

    @app.cli.command("seed-demo")
    @click.option("--admin-password", default=None, help="Password akun admin demo (jika belum dibuat).")
    @click.option("--citizen-password", default=None, help="Password akun warga demo (jika belum dibuat).")
    def seed_demo_cmd(admin_password, citizen_password):
        """Membuat dataset demo lengkap (admin, warga, keluarga, faskes, layanan, iuran, pembayaran, pengaduan) secara idempoten."""
        import sys
        from datetime import date, datetime, timedelta, timezone
        from sqlalchemy import func
        from app.models.user import User
        from app.models.participant import Participant
        from app.models.family_member import FamilyMember
        from app.models.health_facility import HealthFacility
        from app.models.service_request import ServiceRequest
        from app.models.contribution import Contribution
        from app.models.payment import Payment
        from app.models.complaint import Complaint
        from app.services.participant_service import register_citizen
        from app.services.family_service import create_family_member
        from app.services.service_request_service import create_service_request, transition_service_request_status
        from app.services.payment_service import generate_payment_number
        from app.services.complaint_service import (
            create_complaint,
            start_complaint_processing,
            resolve_complaint,
        )

        click.echo("============================================================")
        click.echo("SEHATWARGA - GENERATOR DATA DEMO SIMULASI AKADEMIK")
        click.echo("============================================================")

        users_created = 0
        users_skipped = 0
        family_created = 0
        family_skipped = 0
        services_created = 0
        services_skipped = 0
        contributions_created = 0
        contributions_skipped = 0
        payments_created = 0
        payments_skipped = 0
        complaints_created = 0
        complaints_skipped = 0

        # 1. Ensure Facilities exist
        facilities_count = db.session.execute(select(func.count(HealthFacility.id))).scalar() or 0
        if facilities_count == 0:
            click.echo("Data fasilitas kesehatan belum tersedia, menjalankan seed fasilitas...")
            # Trigger seed-facilities
            seed_facilities.callback()
        facilities = db.session.execute(
            select(HealthFacility).filter_by(is_active=True).order_by(HealthFacility.id)
        ).scalars().all()
        if len(facilities) < 2:
            click.echo("Error: Diperlukan minimal 2 fasilitas kesehatan aktif. Jalankan 'flask --app run.py seed-facilities'.", err=True)
            return

        facility_1 = facilities[0]
        facility_2 = facilities[1]

        # 2. Demo Admin Account
        admin_email = "admin.demo@sehatwarga.test"
        admin_user = db.session.execute(select(User).filter_by(email=admin_email)).scalar_one_or_none()
        if not admin_user:
            if not admin_password:
                if sys.stdin.isatty():
                    admin_password = getpass.getpass("Kata Sandi Admin Demo [admin.demo@sehatwarga.test]: ")
                    while len(admin_password) < 8:
                        click.echo("Password minimal 8 karakter.", err=True)
                        admin_password = getpass.getpass("Kata Sandi Admin Demo: ")
                else:
                    admin_password = "AdminDemo123!"

            admin_user = User(
                name="Admin Demo SehatWarga",
                email=admin_email,
                role="admin",
                is_active=True,
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            users_created += 1
        else:
            users_skipped += 1

        # 3. Demo Citizen Account
        citizen_email = "warga.demo@sehatwarga.test"
        citizen_user = db.session.execute(select(User).filter_by(email=citizen_email)).scalar_one_or_none()
        if not citizen_user:
            if not citizen_password:
                if sys.stdin.isatty():
                    citizen_password = getpass.getpass("Kata Sandi Warga Demo [warga.demo@sehatwarga.test]: ")
                    while len(citizen_password) < 8:
                        click.echo("Password minimal 8 karakter.", err=True)
                        citizen_password = getpass.getpass("Kata Sandi Warga Demo: ")
                else:
                    citizen_password = "WargaDemo123!"

            citizen_user, participant = register_citizen(
                name="Warga Demo SehatWarga",
                email=citizen_email,
                password=citizen_password,
                birth_date=date(1990, 8, 17),
                gender="MALE",
                service_class="CLASS_2",
            )
            users_created += 1
        else:
            participant = citizen_user.participant
            users_skipped += 1

        # 4. Demo Family Members
        f1_name = "Anggota Demo Satu (Anak)"
        f1 = db.session.execute(
            select(FamilyMember).filter_by(participant_id=participant.id, full_name=f1_name)
        ).scalar_one_or_none()
        if not f1:
            f1 = create_family_member(
                participant_id=participant.id,
                full_name=f1_name,
                relationship="CHILD",
                birth_date=date(2018, 5, 20),
                gender="FEMALE",
            )
            family_created += 1
        else:
            family_skipped += 1

        f2_name = "Anggota Demo Dua (Pasangan)"
        f2 = db.session.execute(
            select(FamilyMember).filter_by(participant_id=participant.id, full_name=f2_name)
        ).scalar_one_or_none()
        if not f2:
            f2 = create_family_member(
                participant_id=participant.id,
                full_name=f2_name,
                relationship="SPOUSE",
                birth_date=date(1992, 4, 15),
                gender="FEMALE",
            )
            family_created += 1
        else:
            family_skipped += 1

        # 5. Demo Service Requests (Workflow Demonstration)
        demo_services = [
            {
                "beneficiary_type": "SELF",
                "family_member_id": None,
                "facility": facility_1,
                "service_type": "GENERAL",
                "date_offset": 3,
                "summary": "Pemeriksaan kesehatan umum rutin dan konsultasi tensi darah simulasi.",
                "target_status": "SUBMITTED",
            },
            {
                "beneficiary_type": "FAMILY",
                "family_member_id": f1.id,
                "facility": facility_1,
                "service_type": "MATERNAL",
                "date_offset": 5,
                "summary": "Pemeriksaan kesehatan anak berkala dan pemantauan tumbuh kembang simulasi.",
                "target_status": "VERIFIED",
                "verify_note": "Berkas identitas tanggungan keluarga telah diverifikasi lengkap.",
            },
            {
                "beneficiary_type": "SELF",
                "family_member_id": None,
                "facility": facility_1,
                "service_type": "DENTAL",
                "date_offset": 7,
                "summary": "Pemeriksaan dan pembersihan karang gigi simulasi berkala.",
                "target_status": "SCHEDULED",
                "verify_note": "Berkas administrasi kepesertaan disetujui.",
                "schedule_note": "Jadwal poli gigi ditetapkan pukul 09.00 WIB.",
            },
            {
                "beneficiary_type": "SELF",
                "family_member_id": None,
                "facility": facility_2,
                "service_type": "SPECIALIST",
                "date_offset": -2,
                "summary": "Pemeriksaan spesialis penyakit dalam simulasi lanjutan.",
                "target_status": "COMPLETED",
                "verify_note": "Rujukan poli spesialis telah diverifikasi.",
                "schedule_note": "Jadwal konsultasi spesialis telah ditetapkan.",
                "complete_note": "Pelayanan medis simulasi telah tuntas dilaksanakan.",
            },
            {
                "beneficiary_type": "FAMILY",
                "family_member_id": f2.id,
                "facility": facility_2,
                "service_type": "OTHER",
                "date_offset": 4,
                "summary": "Permohonan layanan konsultasi di faskes yang sedang dalam perbaikan sarana.",
                "target_status": "REJECTED",
                "reject_note": "Fasilitas kesehatan rujukan sedang dalam masa renovasi, silakan pilih faskes lain.",
            },
        ]

        for s in demo_services:
            existing_sr = db.session.execute(
                select(ServiceRequest).filter_by(
                    participant_id=participant.id,
                    complaint_summary=s["summary"],
                )
            ).scalar_one_or_none()

            if not existing_sr:
                req_date = date.today() + timedelta(days=s["date_offset"])
                # For past completed requests, ensure service_request allows it or create with today and shift
                target_date = req_date if req_date >= date.today() else date.today()
                sr = create_service_request(
                    participant=participant,
                    health_facility_id=s["facility"].id,
                    service_type=s["service_type"],
                    scheduled_date=target_date,
                    complaint_summary=s["summary"],
                    beneficiary_type=s["beneficiary_type"],
                    family_member_id=s["family_member_id"],
                    user_id=citizen_user.id,
                )

                if s["target_status"] == "VERIFIED":
                    transition_service_request_status(sr, "VERIFIED", user_id=admin_user.id, note=s.get("verify_note", "Diverifikasi."))
                elif s["target_status"] == "SCHEDULED":
                    transition_service_request_status(sr, "VERIFIED", user_id=admin_user.id, note=s.get("verify_note", "Diverifikasi."))
                    transition_service_request_status(sr, "SCHEDULED", user_id=admin_user.id, note=s.get("schedule_note", "Jadwal ditetapkan."), new_scheduled_date=sr.scheduled_date)
                elif s["target_status"] == "COMPLETED":
                    transition_service_request_status(sr, "VERIFIED", user_id=admin_user.id, note=s.get("verify_note", "Diverifikasi."))
                    transition_service_request_status(sr, "SCHEDULED", user_id=admin_user.id, note=s.get("schedule_note", "Jadwal ditetapkan."), new_scheduled_date=sr.scheduled_date)
                    transition_service_request_status(sr, "COMPLETED", user_id=admin_user.id, note=s.get("complete_note", "Selesai."))
                elif s["target_status"] == "REJECTED":
                    transition_service_request_status(sr, "REJECTED", user_id=admin_user.id, note=s.get("reject_note", "Ditolak."))

                services_created += 1
            else:
                services_skipped += 1

        # 6. Demo Contributions & Simulated Payments
        today = date.today()

        # A. Next Month: UNPAID (Due next month, remains UNPAID and ready for citizen payment demo)
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        unpaid_period = date(next_year, next_month, 1)

        # B. Previous Month: PAID + Simulated Payment
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        paid_period = date(prev_year, prev_month, 1)

        # C. Two Months Ago: OVERDUE
        two_months_ago = prev_month - 1 if prev_month > 1 else 12
        two_months_year = prev_year if prev_month > 1 else prev_year - 1
        overdue_period = date(two_months_year, two_months_ago, 1)

        rate_amount = 100000.00  # CLASS_2 rate

        # A. Next Month: UNPAID
        c_unpaid = db.session.execute(
            select(Contribution).filter_by(participant_id=participant.id, billing_period=unpaid_period)
        ).scalar_one_or_none()
        if not c_unpaid:
            c_unpaid = Contribution(
                participant_id=participant.id,
                billing_period=unpaid_period,
                amount=rate_amount,
                due_date=date(unpaid_period.year, unpaid_period.month, 10),
                status="UNPAID",
            )
            db.session.add(c_unpaid)
            db.session.commit()
            contributions_created += 1
        else:
            if c_unpaid.status != "UNPAID":
                c_unpaid.status = "UNPAID"
                db.session.commit()
            contributions_skipped += 1

        # B. Previous Month: PAID + Simulated Payment
        c_paid = db.session.execute(
            select(Contribution).filter_by(participant_id=participant.id, billing_period=paid_period)
        ).scalar_one_or_none()
        if not c_paid:
            c_paid = Contribution(
                participant_id=participant.id,
                billing_period=paid_period,
                amount=rate_amount,
                due_date=date(paid_period.year, paid_period.month, 10),
                status="PAID",
            )
            db.session.add(c_paid)
            db.session.flush()

            pay_num = generate_payment_number(paid_period)
            payment = Payment(
                payment_number=pay_num,
                contribution_id=c_paid.id,
                amount=rate_amount,
                payment_method="SIMULATION_TRANSFER",
                status="SUCCESS",
                paid_at=datetime(paid_period.year, paid_period.month, 5, 10, 30, 0, tzinfo=timezone.utc),
            )
            db.session.add(payment)
            db.session.commit()
            contributions_created += 1
            payments_created += 1
        else:
            if c_paid.status != "PAID":
                c_paid.status = "PAID"
                db.session.commit()
            contributions_skipped += 1
            # Check payment
            if c_paid.payments:
                payments_skipped += 1

        # C. Two Months Ago: OVERDUE
        c_overdue = db.session.execute(
            select(Contribution).filter_by(participant_id=participant.id, billing_period=overdue_period)
        ).scalar_one_or_none()
        if not c_overdue:
            c_overdue = Contribution(
                participant_id=participant.id,
                billing_period=overdue_period,
                amount=rate_amount,
                due_date=date(overdue_period.year, overdue_period.month, 10),
                status="OVERDUE",
            )
            db.session.add(c_overdue)
            db.session.commit()
            contributions_created += 1
        else:
            if c_overdue.status != "OVERDUE":
                c_overdue.status = "OVERDUE"
                db.session.commit()
            contributions_skipped += 1

        # 7. Demo Complaints
        demo_complaints = [
            {
                "subject": "Kendala akses kartu digital pada koneksi seluler",
                "message": "Aplikasi sempat memerlukan waktu muat lebih lama saat menampilkan barcode kartu kepesertaan digital di area faskes.",
                "target_status": "OPEN",
            },
            {
                "subject": "Pertanyaan prosedur pemindahan fasilitas rujukan keluarga",
                "message": "Bagaimana alur administratif untuk memperbarui fasilitas kesehatan rujukan keluarga kami ke puskesmas yang lebih dekat dari domisili?",
                "target_status": "IN_PROGRESS",
            },
            {
                "subject": "Klarifikasi pencatatan pembayaran simulasi iuran bulanan",
                "message": "Mohon konfirmasi status iuran periode bulan lalu yang telah dibayarkan melalui transfer simulasi SehatWarga.",
                "target_status": "RESOLVED",
                "admin_response": "Pembayaran iuran simulasi Anda telah berhasil diverifikasi lunas dalam sistem SehatWarga. Terima kasih atas konfirmasinya.",
            },
        ]

        for cmp in demo_complaints:
            existing_cmp = db.session.execute(
                select(Complaint).filter_by(user_id=citizen_user.id, subject=cmp["subject"])
            ).scalar_one_or_none()

            if not existing_cmp:
                c_obj = create_complaint(
                    user_id=citizen_user.id,
                    subject=cmp["subject"],
                    message=cmp["message"],
                )
                if cmp["target_status"] == "IN_PROGRESS":
                    start_complaint_processing(c_obj)
                elif cmp["target_status"] == "RESOLVED":
                    start_complaint_processing(c_obj)
                    resolve_complaint(c_obj, admin_response=cmp["admin_response"])

                complaints_created += 1
            else:
                complaints_skipped += 1

        click.echo("------------------------------------------------------------")
        click.echo("HASIL SEED DEMO:")
        click.echo(f"  Akun Pengguna        : {users_created} dibuat, {users_skipped} dilewati")
        click.echo(f"  Anggota Keluarga     : {family_created} dibuat, {family_skipped} dilewati")
        click.echo(f"  Fasilitas Kesehatan  : {len(facilities)} tersedia (aktif)")
        click.echo(f"  Pengajuan Layanan    : {services_created} dibuat, {services_skipped} dilewati")
        click.echo(f"  Tagihan Iuran        : {contributions_created} dibuat, {contributions_skipped} dilewati")
        click.echo(f"  Pembayaran Simulasi  : {payments_created} dibuat, {payments_skipped} dilewati")
        click.echo(f"  Pengaduan Layanan    : {complaints_created} dibuat, {complaints_skipped} dilewati")
        click.echo("------------------------------------------------------------")
        click.echo("Akun Demo:")
        click.echo(f"  Administrator : {admin_email}")
        click.echo(f"  Warga/Peserta : {citizen_email}")
        click.echo("Status: SUKSES (Idempoten).")
        click.echo("============================================================")

