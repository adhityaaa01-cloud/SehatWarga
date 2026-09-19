from datetime import date
from flask import Blueprint, render_template, abort, redirect, url_for, flash, request
from flask_login import current_user
from sqlalchemy import select, func, or_
from app.extensions import db
from app.models.family_member import FamilyMember
from app.models.health_facility import HealthFacility
from app.models.service_request import ServiceRequest
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.models.complaint import Complaint
from app.forms.family import FamilyMemberForm
from app.forms.service import ServiceRequestForm
from app.forms.contribution import SimulatedPaymentForm
from app.forms.complaint import ComplaintCreateForm
from app.decorators import role_required
from app.services.family_service import (
    create_family_member,
    update_family_member,
    deactivate_family_member,
)
from app.services.service_request_service import (
    VALID_SERVICE_TYPES,
    VALID_STATUSES,
    create_service_request,
    transition_service_request_status,
)
from app.services.contribution_service import (
    CONTRIBUTION_STATUS_LABELS,
    SIMULATED_RATES,
    RATE_DESCRIPTION,
    get_billing_period_start,
)
from app.services.payment_service import (
    VALID_PAYMENT_METHODS,
    PAYMENT_STATUS_LABELS,
    SIMULATION_NOTICE,
    process_simulated_payment,
)
from app.services.complaint_service import (
    STATUS_OPEN,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    STATUS_REJECTED,
    VALID_COMPLAINT_STATUSES,
    COMPLAINT_STATUS_LABELS,
    COMPLAINT_STATUS_BADGES,
    create_complaint,
)

citizen_bp = Blueprint("citizen", __name__, url_prefix="/citizen")


@citizen_bp.route("/dashboard")
@role_required("citizen")
def dashboard():
    participant = current_user.participant
    if not participant:
        abort(404)

    active_family_count = len([
        m for m in participant.family_members if m.membership_status == "ACTIVE"
    ])

    total_services = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(participant_id=participant.id)
    ).scalar() or 0

    active_services = db.session.execute(
        select(func.count(ServiceRequest.id)).filter(
            ServiceRequest.participant_id == participant.id,
            ServiceRequest.status.in_(["SUBMITTED", "VERIFIED", "SCHEDULED"]),
        )
    ).scalar() or 0

    completed_services = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(
            participant_id=participant.id, status="COMPLETED"
        )
    ).scalar() or 0

    recent_services = db.session.execute(
        select(ServiceRequest)
        .filter_by(participant_id=participant.id)
        .order_by(ServiceRequest.created_at.desc())
        .limit(5)
    ).scalars().all()

    # Contribution stats for citizen dashboard (Stage 6)
    current_period = get_billing_period_start(date.today())
    current_bill = db.session.execute(
        select(Contribution).filter_by(participant_id=participant.id, billing_period=current_period)
    ).scalar_one_or_none()

    unpaid_contributions_count = db.session.execute(
        select(func.count(Contribution.id)).filter(
            Contribution.participant_id == participant.id,
            Contribution.status.in_(["UNPAID", "OVERDUE"]),
        )
    ).scalar() or 0

    total_unpaid_amount = db.session.execute(
        select(func.coalesce(func.sum(Contribution.amount), 0)).filter(
            Contribution.participant_id == participant.id,
            Contribution.status.in_(["UNPAID", "OVERDUE"]),
        )
    ).scalar() or 0

    # Complaint statistics (Stage 7)
    total_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(user_id=current_user.id)
    ).scalar() or 0

    processing_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(
            user_id=current_user.id, status=STATUS_IN_PROGRESS
        )
    ).scalar() or 0

    resolved_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(
            user_id=current_user.id, status=STATUS_RESOLVED
        )
    ).scalar() or 0

    return render_template(
        "citizen/dashboard.html",
        user=current_user,
        participant=participant,
        active_family_count=active_family_count,
        total_services=total_services,
        active_services=active_services,
        completed_services=completed_services,
        recent_services=recent_services,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
        current_bill=current_bill,
        unpaid_contributions_count=unpaid_contributions_count,
        total_unpaid_amount=total_unpaid_amount,
        contribution_status_labels=CONTRIBUTION_STATUS_LABELS,
        total_complaints=total_complaints,
        processing_complaints=processing_complaints,
        resolved_complaints=resolved_complaints,
    )


@citizen_bp.route("/profile")
@role_required("citizen")
def profile():
    participant = current_user.participant
    if not participant:
        abort(404)

    return render_template("citizen/profile.html", user=current_user, participant=participant)


@citizen_bp.route("/card")
@role_required("citizen")
def card():
    participant = current_user.participant
    if not participant:
        abort(404)

    return render_template("citizen/card.html", user=current_user, participant=participant)


@citizen_bp.route("/family")
@role_required("citizen")
def family_list():
    participant = current_user.participant
    if not participant:
        abort(404)

    members = db.session.execute(
        select(FamilyMember)
        .filter_by(participant_id=participant.id)
        .order_by(FamilyMember.created_at.desc())
    ).scalars().all()

    return render_template("citizen/family/list.html", user=current_user, participant=participant, members=members)


@citizen_bp.route("/family/add", methods=["GET", "POST"])
@role_required("citizen")
def family_add():
    participant = current_user.participant
    if not participant:
        abort(404)

    form = FamilyMemberForm()
    if form.validate_on_submit():
        try:
            create_family_member(
                participant_id=participant.id,
                full_name=form.full_name.data,
                relationship=form.relationship.data,
                birth_date=form.birth_date.data,
                gender=form.gender.data,
            )
            flash("Anggota keluarga berhasil didaftarkan.", "success")
            return redirect(url_for("citizen.family_list"))
        except Exception:
            flash("Terjadi kesalahan saat menambahkan anggota keluarga.", "danger")

    return render_template("citizen/family/add.html", form=form, participant=participant)


@citizen_bp.route("/family/<int:member_id>")
@role_required("citizen")
def family_detail(member_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    member = db.session.execute(
        select(FamilyMember).filter_by(id=member_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not member:
        abort(404)

    return render_template("citizen/family/detail.html", member=member, participant=participant)


@citizen_bp.route("/family/<int:member_id>/edit", methods=["GET", "POST"])
@role_required("citizen")
def family_edit(member_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    member = db.session.execute(
        select(FamilyMember).filter_by(id=member_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not member:
        abort(404)

    form = FamilyMemberForm(obj=member)
    if form.validate_on_submit():
        try:
            update_family_member(
                member=member,
                full_name=form.full_name.data,
                relationship=form.relationship.data,
                birth_date=form.birth_date.data,
                gender=form.gender.data,
            )
            flash("Data anggota keluarga berhasil diperbarui.", "success")
            return redirect(url_for("citizen.family_detail", member_id=member.id))
        except Exception:
            flash("Terjadi kesalahan saat memperbarui data anggota keluarga.", "danger")

    return render_template("citizen/family/edit.html", form=form, member=member, participant=participant)


@citizen_bp.route("/family/<int:member_id>/remove", methods=["POST"])
@role_required("citizen")
def family_remove(member_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    member = db.session.execute(
        select(FamilyMember).filter_by(id=member_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not member:
        abort(404)

    try:
        deactivate_family_member(member)
        flash("Anggota keluarga berhasil dinonaktifkan.", "info")
    except Exception:
        flash("Terjadi kesalahan saat menonaktifkan anggota keluarga.", "danger")

    return redirect(url_for("citizen.family_list"))


# ============================================================
# SERVICE REQUESTS (STAGE 5)
# ============================================================

@citizen_bp.route("/services")
@role_required("citizen")
def service_requests_list():
    participant = current_user.participant
    if not participant:
        abort(404)

    selected_status = request.args.get("status", "").strip()
    selected_service_type = request.args.get("service_type", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = select(ServiceRequest).filter_by(participant_id=participant.id)

    if selected_status in VALID_STATUSES:
        query = query.filter(ServiceRequest.status == selected_status)

    if selected_service_type in VALID_SERVICE_TYPES:
        query = query.filter(ServiceRequest.service_type == selected_service_type)

    query = query.order_by(ServiceRequest.created_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    service_requests = pagination.items

    return render_template(
        "citizen/services/list.html",
        participant=participant,
        service_requests=service_requests,
        pagination=pagination,
        selected_status=selected_status,
        selected_service_type=selected_service_type,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
    )


@citizen_bp.route("/services/request", methods=["GET", "POST"])
@role_required("citizen")
def service_request_create():
    participant = current_user.participant
    if not participant:
        abort(404)

    if participant.membership_status != "ACTIVE":
        flash("Status kepesertaan Anda tidak aktif, sehingga tidak dapat mengajukan layanan kesehatan.", "danger")
        return redirect(url_for("citizen.dashboard"))

    # Active facilities for selection
    facilities = db.session.execute(
        select(HealthFacility).filter_by(is_active=True).order_by(HealthFacility.name.asc())
    ).scalars().all()

    # Active family members for selection
    family_members = db.session.execute(
        select(FamilyMember)
        .filter_by(participant_id=participant.id, membership_status="ACTIVE")
        .order_by(FamilyMember.full_name.asc())
    ).scalars().all()

    form = ServiceRequestForm()
    form.health_facility_id.choices = [("", "-- Pilih Fasilitas Kesehatan --")] + [
        (str(f.id), f"{f.name} ({f.facility_code}) - {f.city or 'Umum'}") for f in facilities
    ]
    form.family_member_id.choices = [("", "-- Pilih Anggota Keluarga --")] + [
        (str(m.id), f"{m.full_name} ({m.member_number}) - {m.relationship}") for m in family_members
    ]

    # Prefill aman dari rekomendasi AI Health Navigator.
    # Nilai asing yang tidak tersedia di database akan diabaikan.
    if request.method == "GET":
        suggested_facility_id = request.args.get(
            "health_facility_id", ""
        ).strip()
        suggested_service_type = request.args.get(
            "service_type", ""
        ).strip().upper()

        active_facility_ids = {
            str(facility.id)
            for facility in facilities
        }

        if suggested_facility_id in active_facility_ids:
            form.health_facility_id.data = suggested_facility_id

        if suggested_service_type in VALID_SERVICE_TYPES:
            form.service_type.data = suggested_service_type

    if form.validate_on_submit():
        target_family_id = None
        if form.beneficiary_type.data == "FAMILY":
            if not form.family_member_id.data:
                flash("Silakan pilih anggota keluarga yang akan menerima layanan kesehatan.", "danger")
                return render_template(
                    "citizen/services/request.html",
                    form=form,
                    participant=participant,
                    has_family_members=len(family_members) > 0,
                )
            try:
                target_family_id = int(form.family_member_id.data)
            except (ValueError, TypeError):
                flash("Pilihan anggota keluarga tidak valid.", "danger")
                return render_template(
                    "citizen/services/request.html",
                    form=form,
                    participant=participant,
                    has_family_members=len(family_members) > 0,
                )

        try:
            facility_id = int(form.health_facility_id.data)
            service_req = create_service_request(
                participant=participant,
                health_facility_id=facility_id,
                service_type=form.service_type.data,
                scheduled_date=form.scheduled_date.data,
                complaint_summary=form.complaint_summary.data,
                beneficiary_type=form.beneficiary_type.data,
                family_member_id=target_family_id,
                user_id=current_user.id,
            )
            flash(f"Pengajuan layanan berhasil dikirim dengan nomor {service_req.request_number}.", "success")
            return redirect(url_for("citizen.service_request_detail", request_id=service_req.id))
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat memproses pengajuan layanan.", "danger")

    return render_template(
        "citizen/services/request.html",
        form=form,
        participant=participant,
        has_family_members=len(family_members) > 0,
    )


@citizen_bp.route("/services/<int:request_id>")
@role_required("citizen")
def service_request_detail(request_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    return render_template(
        "citizen/services/detail.html",
        participant=participant,
        req=service_req,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
    )


@citizen_bp.route("/services/<int:request_id>/cancel", methods=["POST"])
@role_required("citizen")
def service_request_cancel(request_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    if service_req.status not in ["SUBMITTED", "VERIFIED"]:
        flash(
            f"Pengajuan dengan status '{VALID_STATUSES.get(service_req.status, service_req.status)}' tidak dapat dibatalkan.",
            "warning",
        )
        return redirect(url_for("citizen.service_request_detail", request_id=service_req.id))

    cancel_reason = request.form.get("cancel_reason", "").strip() or "Dibatalkan oleh pemohon layanan (peserta)."

    try:
        transition_service_request_status(
            service_request=service_req,
            target_status="CANCELLED",
            user_id=current_user.id,
            note=cancel_reason,
        )
        flash(f"Pengajuan layanan {service_req.request_number} berhasil dibatalkan.", "info")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception:
        flash("Terjadi kesalahan sistem saat membatalkan pengajuan.", "danger")

    return redirect(url_for("citizen.service_request_detail", request_id=service_req.id))


# ============================================================
# CONTRIBUTIONS & PAYMENTS (STAGE 6)
# ============================================================

@citizen_bp.route("/contributions")
@role_required("citizen")
def contributions_list():
    participant = current_user.participant
    if not participant:
        abort(404)

    selected_status = request.args.get("status", "").strip()
    selected_year = request.args.get("year", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 12

    query = select(Contribution).filter_by(participant_id=participant.id)

    if selected_status in CONTRIBUTION_STATUS_LABELS:
        query = query.filter(Contribution.status == selected_status)

    if selected_year:
        query = query.filter(db.extract("year", Contribution.billing_period) == selected_year)

    query = query.order_by(Contribution.billing_period.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    contributions = pagination.items

    years = db.session.execute(
        select(func.distinct(db.extract("year", Contribution.billing_period)))
        .filter_by(participant_id=participant.id)
        .order_by(db.extract("year", Contribution.billing_period).desc())
    ).scalars().all()

    return render_template(
        "citizen/contributions/list.html",
        participant=participant,
        contributions=contributions,
        pagination=pagination,
        selected_status=selected_status,
        selected_year=selected_year,
        years=years,
        status_labels=CONTRIBUTION_STATUS_LABELS,
        rate_desc=RATE_DESCRIPTION,
    )


@citizen_bp.route("/contributions/<int:contribution_id>")
@role_required("citizen")
def contribution_detail(contribution_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    contribution = db.session.execute(
        select(Contribution).filter_by(id=contribution_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not contribution:
        abort(404)

    return render_template(
        "citizen/contributions/detail.html",
        participant=participant,
        contribution=contribution,
        status_labels=CONTRIBUTION_STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
        payment_methods=VALID_PAYMENT_METHODS,
        rate_desc=RATE_DESCRIPTION,
    )


@citizen_bp.route("/contributions/<int:contribution_id>/pay", methods=["GET", "POST"])
@role_required("citizen")
def contribution_pay(contribution_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    contribution = db.session.execute(
        select(Contribution).filter_by(id=contribution_id, participant_id=participant.id)
    ).scalar_one_or_none()

    if not contribution:
        abort(404)

    if contribution.status == "PAID":
        flash("Tagihan iuran untuk periode ini sudah lunas.", "info")
        return redirect(url_for("citizen.contribution_detail", contribution_id=contribution.id))

    form = SimulatedPaymentForm()

    if form.validate_on_submit():
        try:
            payment = process_simulated_payment(
                contribution=contribution,
                payment_method=form.payment_method.data,
            )
            flash(
                f"Pembayaran simulasi berhasil diproses dengan nomor bukti {payment.payment_number}.",
                "success",
            )
            return redirect(url_for("citizen.payment_detail", payment_id=payment.id))
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat memproses simulasi pembayaran.", "danger")

    return render_template(
        "citizen/contributions/pay.html",
        participant=participant,
        contribution=contribution,
        form=form,
        simulation_notice=SIMULATION_NOTICE,
        rate_desc=RATE_DESCRIPTION,
        status_labels=CONTRIBUTION_STATUS_LABELS,
    )


@citizen_bp.route("/payments")
@role_required("citizen")
def payments_list():
    participant = current_user.participant
    if not participant:
        abort(404)

    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = (
        select(Payment)
        .join(Payment.contribution)
        .filter(Contribution.participant_id == participant.id)
        .order_by(Payment.created_at.desc())
    )

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    return render_template(
        "citizen/payments/list.html",
        participant=participant,
        payments=payments,
        pagination=pagination,
        status_labels=PAYMENT_STATUS_LABELS,
        method_labels=VALID_PAYMENT_METHODS,
        simulation_notice=SIMULATION_NOTICE,
    )


@citizen_bp.route("/payments/<int:payment_id>")
@role_required("citizen")
def payment_detail(payment_id):
    participant = current_user.participant
    if not participant:
        abort(404)

    payment = db.session.execute(
        select(Payment)
        .join(Payment.contribution)
        .filter(Payment.id == payment_id, Contribution.participant_id == participant.id)
    ).scalar_one_or_none()

    if not payment:
        abort(404)

    return render_template(
        "citizen/payments/detail.html",
        participant=participant,
        payment=payment,
        status_labels=PAYMENT_STATUS_LABELS,
        method_labels=VALID_PAYMENT_METHODS,
        simulation_notice=SIMULATION_NOTICE,
    )


# ============================================================
# COMPLAINTS (STAGE 7)
# ============================================================

@citizen_bp.route("/complaints")
@role_required("citizen")
def complaints_list():
    status_filter = request.args.get("status", "").strip().upper()
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = 10

    stmt = select(Complaint).filter(Complaint.user_id == current_user.id)

    if status_filter in VALID_COMPLAINT_STATUSES:
        stmt = stmt.filter(Complaint.status == status_filter)
    else:
        status_filter = ""

    if search_query:
        stmt = stmt.filter(
            or_(
                Complaint.ticket_number.ilike(f"%{search_query}%"),
                Complaint.subject.ilike(f"%{search_query}%"),
            )
        )

    stmt = stmt.order_by(Complaint.created_at.desc(), Complaint.id.desc())
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    complaints = pagination.items

    return render_template(
        "citizen/complaints/list.html",
        complaints=complaints,
        pagination=pagination,
        status_filter=status_filter,
        search_query=search_query,
        status_labels=COMPLAINT_STATUS_LABELS,
        status_badges=COMPLAINT_STATUS_BADGES,
        valid_statuses=VALID_COMPLAINT_STATUSES,
    )


@citizen_bp.route("/complaints/create", methods=["GET", "POST"])
@role_required("citizen")
def complaint_create():
    form = ComplaintCreateForm()
    if form.validate_on_submit():
        try:
            # Mass-assignment protection: explicitly take only subject and message
            complaint = create_complaint(
                user_id=current_user.id,
                subject=form.subject.data,
                message=form.message.data,
            )
            flash("Pengaduan berhasil dikirim.", "success")
            return redirect(url_for("citizen.complaint_detail", complaint_id=complaint.id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat mengirim pengaduan. Silakan coba lagi.", "danger")

    return render_template("citizen/complaints/create.html", form=form)


@citizen_bp.route("/complaints/<int:complaint_id>")
@role_required("citizen")
def complaint_detail(complaint_id):
    # Strict ownership check: return 404 if not found or not owned
    complaint = db.session.execute(
        select(Complaint).filter_by(id=complaint_id, user_id=current_user.id)
    ).scalar_one_or_none()

    if not complaint:
        abort(404)

    return render_template(
        "citizen/complaints/detail.html",
        complaint=complaint,
        status_labels=COMPLAINT_STATUS_LABELS,
        status_badges=COMPLAINT_STATUS_BADGES,
    )

