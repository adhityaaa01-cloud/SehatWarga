from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user
from sqlalchemy import select, func, or_
from app.extensions import db
from app.models.user import User
from app.models.participant import Participant
from app.models.health_facility import HealthFacility
from app.models.service_request import ServiceRequest
from app.models.contribution import Contribution
from app.models.payment import Payment
from app.models.complaint import Complaint
from app.forms.facility import HealthFacilityForm, HealthFacilityEditForm
from app.forms.service import ScheduleServiceRequestForm, RejectServiceRequestForm
from app.forms.contribution import AdminGenerateContributionForm
from app.forms.complaint import AdminResolveComplaintForm, AdminRejectComplaintForm
from app.decorators import role_required
from app.services.service_request_service import (
    VALID_SERVICE_TYPES,
    VALID_STATUSES,
    transition_service_request_status,
)
from app.services.contribution_service import (
    CONTRIBUTION_STATUS_LABELS,
    SIMULATED_RATES,
    RATE_DESCRIPTION,
    get_billing_period_start,
    generate_contributions_for_active_participants,
)
from app.services.payment_service import (
    VALID_PAYMENT_METHODS,
    PAYMENT_STATUS_LABELS,
    SIMULATION_NOTICE,
)
from app.services.complaint_service import (
    STATUS_OPEN,
    STATUS_IN_PROGRESS,
    STATUS_RESOLVED,
    STATUS_REJECTED,
    VALID_COMPLAINT_STATUSES,
    COMPLAINT_STATUS_LABELS,
    COMPLAINT_STATUS_BADGES,
    start_complaint_processing,
    resolve_complaint,
    reject_complaint,
    transition_complaint,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

FACILITY_TYPE_LABELS = {
    "PUSKESMAS": "Puskesmas",
    "CLINIC": "Klinik",
    "HOSPITAL": "Rumah Sakit",
    "DENTAL_CLINIC": "Klinik Gigi",
    "OTHER": "Lainnya",
}


@admin_bp.route("/dashboard")
@role_required("admin")
def dashboard():
    total_users = db.session.execute(select(func.count(User.id))).scalar() or 0
    total_citizens = db.session.execute(
        select(func.count(User.id)).filter_by(role="citizen")
    ).scalar() or 0
    total_active_participants = db.session.execute(
        select(func.count(Participant.id)).filter_by(membership_status="ACTIVE")
    ).scalar() or 0
    total_inactive_participants = db.session.execute(
        select(func.count(Participant.id)).filter_by(membership_status="INACTIVE")
    ).scalar() or 0

    # Facility statistics
    total_facilities = db.session.execute(select(func.count(HealthFacility.id))).scalar() or 0
    active_facilities = db.session.execute(
        select(func.count(HealthFacility.id)).filter_by(is_active=True)
    ).scalar() or 0
    inactive_facilities = db.session.execute(
        select(func.count(HealthFacility.id)).filter_by(is_active=False)
    ).scalar() or 0

    # Service Request statistics (Stage 5)
    total_service_requests = db.session.execute(select(func.count(ServiceRequest.id))).scalar() or 0
    pending_service_requests = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(status="SUBMITTED")
    ).scalar() or 0
    verified_service_requests = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(status="VERIFIED")
    ).scalar() or 0
    scheduled_service_requests = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(status="SCHEDULED")
    ).scalar() or 0
    completed_service_requests = db.session.execute(
        select(func.count(ServiceRequest.id)).filter_by(status="COMPLETED")
    ).scalar() or 0

    # Contribution statistics (Stage 6)
    current_period = get_billing_period_start(date.today())
    total_month_bills = db.session.execute(
        select(func.count(Contribution.id)).filter_by(billing_period=current_period)
    ).scalar() or 0
    unpaid_month_bills = db.session.execute(
        select(func.count(Contribution.id)).filter_by(billing_period=current_period, status="UNPAID")
    ).scalar() or 0
    overdue_bills = db.session.execute(
        select(func.count(Contribution.id)).filter_by(status="OVERDUE")
    ).scalar() or 0
    paid_month_bills = db.session.execute(
        select(func.count(Contribution.id)).filter_by(billing_period=current_period, status="PAID")
    ).scalar() or 0
    total_simulated_paid = db.session.execute(
        select(func.coalesce(func.sum(Payment.amount), 0)).filter(
            func.date(Payment.paid_at) >= current_period, Payment.status == "SUCCESS"
        )
    ).scalar() or 0

    recent_participants = db.session.execute(
        select(Participant).order_by(Participant.created_at.desc()).limit(5)
    ).scalars().all()

    recent_service_requests = db.session.execute(
        select(ServiceRequest).order_by(ServiceRequest.created_at.desc()).limit(5)
    ).scalars().all()

    recent_contributions = db.session.execute(
        select(Contribution).order_by(Contribution.created_at.desc()).limit(5)
    ).scalars().all()

    # Complaint statistics (Stage 7)
    total_complaints = db.session.execute(select(func.count(Complaint.id))).scalar() or 0
    open_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(status=STATUS_OPEN)
    ).scalar() or 0
    in_progress_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(status=STATUS_IN_PROGRESS)
    ).scalar() or 0
    resolved_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(status=STATUS_RESOLVED)
    ).scalar() or 0
    rejected_complaints = db.session.execute(
        select(func.count(Complaint.id)).filter_by(status=STATUS_REJECTED)
    ).scalar() or 0

    recent_complaints = db.session.execute(
        select(Complaint).order_by(Complaint.created_at.desc(), Complaint.id.desc()).limit(5)
    ).scalars().all()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_citizens=total_citizens,
        total_active_participants=total_active_participants,
        total_inactive_participants=total_inactive_participants,
        total_facilities=total_facilities,
        active_facilities=active_facilities,
        inactive_facilities=inactive_facilities,
        total_service_requests=total_service_requests,
        pending_service_requests=pending_service_requests,
        verified_service_requests=verified_service_requests,
        scheduled_service_requests=scheduled_service_requests,
        completed_service_requests=completed_service_requests,
        total_month_bills=total_month_bills,
        unpaid_month_bills=unpaid_month_bills,
        overdue_bills=overdue_bills,
        paid_month_bills=paid_month_bills,
        total_simulated_paid=total_simulated_paid,
        current_period=current_period,
        recent_participants=recent_participants,
        recent_service_requests=recent_service_requests,
        recent_contributions=recent_contributions,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
        contribution_status_labels=CONTRIBUTION_STATUS_LABELS,
        total_complaints=total_complaints,
        open_complaints=open_complaints,
        in_progress_complaints=in_progress_complaints,
        resolved_complaints=resolved_complaints,
        rejected_complaints=rejected_complaints,
        recent_complaints=recent_complaints,
        complaint_status_labels=COMPLAINT_STATUS_LABELS,
        complaint_status_badges=COMPLAINT_STATUS_BADGES,
    )


@admin_bp.route("/facilities")
@role_required("admin")
def facilities_list():
    search_query = request.args.get("search", "").strip()
    selected_type = request.args.get("facility_type", "").strip()
    selected_status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = select(HealthFacility)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                HealthFacility.name.ilike(pattern),
                HealthFacility.facility_code.ilike(pattern),
                HealthFacility.city.ilike(pattern),
            )
        )

    if selected_type in FACILITY_TYPE_LABELS:
        query = query.filter(HealthFacility.facility_type == selected_type)

    if selected_status == "active":
        query = query.filter(HealthFacility.is_active.is_(True))
    elif selected_status == "inactive":
        query = query.filter(HealthFacility.is_active.is_(False))

    query = query.order_by(HealthFacility.created_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    facilities = pagination.items

    return render_template(
        "admin/facilities/list.html",
        facilities=facilities,
        pagination=pagination,
        search_query=search_query,
        selected_type=selected_type,
        selected_status=selected_status,
        facility_types=FACILITY_TYPE_LABELS,
    )


@admin_bp.route("/facilities/create", methods=["GET", "POST"])
@role_required("admin")
def facility_create():
    form = HealthFacilityForm()
    if form.validate_on_submit():
        code = form.facility_code.data.strip().upper()
        # Check uniqueness of facility_code
        existing = db.session.execute(
            select(HealthFacility.id).filter_by(facility_code=code)
        ).scalar_one_or_none()

        if existing:
            flash(f"Kode fasilitas '{code}' sudah digunakan oleh fasilitas lain.", "danger")
            return render_template("admin/facilities/create.html", form=form), 400

        try:
            facility = HealthFacility(
                facility_code=code,
                name=form.name.data.strip(),
                facility_type=form.facility_type.data,
                address=form.address.data.strip() if form.address.data else None,
                city=form.city.data.strip() if form.city.data else None,
                phone=form.phone.data.strip() if form.phone.data else None,
                latitude=form.latitude.data,
                longitude=form.longitude.data,
                is_active=form.is_active.data,
            )
            db.session.add(facility)
            db.session.commit()
            flash(f"Fasilitas kesehatan '{facility.name}' berhasil ditambahkan.", "success")
            return redirect(url_for("admin.facilities_list"))
        except Exception:
            db.session.rollback()
            flash("Terjadi kesalahan saat menambahkan fasilitas kesehatan.", "danger")

    return render_template("admin/facilities/create.html", form=form)


@admin_bp.route("/facilities/<int:facility_id>/edit", methods=["GET", "POST"])
@role_required("admin")
def facility_edit(facility_id):
    facility = db.session.execute(
        select(HealthFacility).filter_by(id=facility_id)
    ).scalar_one_or_none()

    if not facility:
        abort(404)

    form = HealthFacilityEditForm(obj=facility)
    if form.validate_on_submit():
        try:
            facility.name = form.name.data.strip()
            facility.facility_type = form.facility_type.data
            facility.address = form.address.data.strip() if form.address.data else None
            facility.city = form.city.data.strip() if form.city.data else None
            facility.phone = form.phone.data.strip() if form.phone.data else None
            facility.latitude = form.latitude.data
            facility.longitude = form.longitude.data
            facility.is_active = form.is_active.data

            db.session.commit()
            flash(f"Data fasilitas kesehatan '{facility.name}' berhasil diperbarui.", "success")
            return redirect(url_for("admin.facilities_list"))
        except Exception:
            db.session.rollback()
            flash("Terjadi kesalahan saat memperbarui fasilitas kesehatan.", "danger")

    return render_template("admin/facilities/edit.html", form=form, facility=facility)


@admin_bp.route("/facilities/<int:facility_id>/toggle-status", methods=["POST"])
@role_required("admin")
def facility_toggle_status(facility_id):
    facility = db.session.execute(
        select(HealthFacility).filter_by(id=facility_id)
    ).scalar_one_or_none()

    if not facility:
        abort(404)

    try:
        facility.is_active = not facility.is_active
        db.session.commit()
        status_text = "diaktifkan" if facility.is_active else "dinonaktifkan"
        flash(f"Fasilitas kesehatan '{facility.name}' berhasil {status_text}.", "info")
    except Exception:
        db.session.rollback()
        flash("Terjadi kesalahan saat mengubah status fasilitas.", "danger")

    return redirect(url_for("admin.facilities_list"))


# ============================================================
# SERVICE MANAGEMENT (STAGE 5)
# ============================================================

@admin_bp.route("/services")
@role_required("admin")
def services_list():
    search_query = request.args.get("search", "").strip()
    selected_status = request.args.get("status", "").strip()
    selected_service_type = request.args.get("service_type", "").strip()
    selected_facility_id = request.args.get("facility_id", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 10

    query = select(ServiceRequest).join(ServiceRequest.participant)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                ServiceRequest.request_number.ilike(pattern),
                Participant.participant_number.ilike(pattern),
                Participant.full_name.ilike(pattern),
            )
        )

    if selected_status in VALID_STATUSES:
        query = query.filter(ServiceRequest.status == selected_status)

    if selected_service_type in VALID_SERVICE_TYPES:
        query = query.filter(ServiceRequest.service_type == selected_service_type)

    if selected_facility_id:
        query = query.filter(ServiceRequest.health_facility_id == selected_facility_id)

    query = query.order_by(ServiceRequest.created_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    service_requests = pagination.items

    facilities = db.session.execute(
        select(HealthFacility).order_by(HealthFacility.name.asc())
    ).scalars().all()

    return render_template(
        "admin/services/list.html",
        service_requests=service_requests,
        pagination=pagination,
        search_query=search_query,
        selected_status=selected_status,
        selected_service_type=selected_service_type,
        selected_facility_id=selected_facility_id,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
        facilities=facilities,
    )


@admin_bp.route("/services/<int:request_id>")
@role_required("admin")
def service_detail(request_id):
    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    schedule_form = ScheduleServiceRequestForm(scheduled_date=service_req.scheduled_date)
    reject_form = RejectServiceRequestForm()

    return render_template(
        "admin/services/detail.html",
        req=service_req,
        schedule_form=schedule_form,
        reject_form=reject_form,
        valid_statuses=VALID_STATUSES,
        valid_service_types=VALID_SERVICE_TYPES,
    )


@admin_bp.route("/services/<int:request_id>/verify", methods=["POST"])
@role_required("admin")
def service_verify(request_id):
    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    note = request.form.get("note", "").strip() or "Pengajuan layanan diverifikasi oleh petugas administrator."

    try:
        transition_service_request_status(
            service_request=service_req,
            target_status="VERIFIED",
            user_id=current_user.id,
            note=note,
        )
        flash(f"Pengajuan {service_req.request_number} berhasil diverifikasi.", "success")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception:
        flash("Terjadi kesalahan sistem saat memverifikasi pengajuan.", "danger")

    return redirect(url_for("admin.service_detail", request_id=service_req.id))


@admin_bp.route("/services/<int:request_id>/schedule", methods=["POST"])
@role_required("admin")
def service_schedule(request_id):
    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    form = ScheduleServiceRequestForm()
    if form.validate_on_submit():
        note = form.note.data.strip() if form.note.data else "Jadwal layanan kesehatan telah ditetapkan."
        try:
            transition_service_request_status(
                service_request=service_req,
                target_status="SCHEDULED",
                user_id=current_user.id,
                note=note,
                new_scheduled_date=form.scheduled_date.data,
            )
            flash(
                f"Pengajuan {service_req.request_number} berhasil dijadwalkan pada {form.scheduled_date.data.strftime('%d/%m/%Y')}.",
                "success",
            )
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat menetapkan jadwal.", "danger")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Jadwal: {err}", "danger")

    return redirect(url_for("admin.service_detail", request_id=service_req.id))


@admin_bp.route("/services/<int:request_id>/reject", methods=["POST"])
@role_required("admin")
def service_reject(request_id):
    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    form = RejectServiceRequestForm()
    if form.validate_on_submit():
        try:
            transition_service_request_status(
                service_request=service_req,
                target_status="REJECTED",
                user_id=current_user.id,
                note=form.reason.data.strip(),
            )
            flash(f"Pengajuan {service_req.request_number} telah ditolak.", "info")
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat menolak pengajuan.", "danger")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Penolakan: {err}", "danger")

    return redirect(url_for("admin.service_detail", request_id=service_req.id))


@admin_bp.route("/services/<int:request_id>/complete", methods=["POST"])
@role_required("admin")
def service_complete(request_id):
    service_req = db.session.execute(
        select(ServiceRequest).filter_by(id=request_id)
    ).scalar_one_or_none()

    if not service_req:
        abort(404)

    note = request.form.get("note", "").strip() or "Pelayanan kesehatan telah selesai dilaksanakan."

    try:
        transition_service_request_status(
            service_request=service_req,
            target_status="COMPLETED",
            user_id=current_user.id,
            note=note,
        )
        flash(f"Pengajuan layanan {service_req.request_number} berhasil diselesaikan.", "success")
    except ValueError as ve:
        flash(str(ve), "danger")
    except Exception:
        flash("Terjadi kesalahan sistem saat menyelesaikan pengajuan.", "danger")

    return redirect(url_for("admin.service_detail", request_id=service_req.id))


# ============================================================
# CONTRIBUTIONS & PAYMENTS MANAGEMENT (STAGE 6)
# ============================================================

@admin_bp.route("/contributions")
@role_required("admin")
def contributions_list():
    search_query = request.args.get("search", "").strip()
    selected_status = request.args.get("status", "").strip()
    selected_class = request.args.get("service_class", "").strip()
    selected_month = request.args.get("month", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = select(Contribution).join(Contribution.participant)

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Participant.participant_number.ilike(pattern),
                Participant.full_name.ilike(pattern),
            )
        )

    if selected_status in CONTRIBUTION_STATUS_LABELS:
        query = query.filter(Contribution.status == selected_status)

    if selected_class in SIMULATED_RATES:
        query = query.filter(Participant.service_class == selected_class)

    if selected_month:
        try:
            m_date = datetime.strptime(selected_month, "%Y-%m").date()
            query = query.filter(
                db.extract("year", Contribution.billing_period) == m_date.year,
                func.month(Contribution.billing_period) == m_date.month,
            )
        except ValueError:
            pass

    query = query.order_by(Contribution.billing_period.desc(), Contribution.created_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    contributions = pagination.items

    generate_form = AdminGenerateContributionForm()

    return render_template(
        "admin/contributions/list.html",
        contributions=contributions,
        pagination=pagination,
        search_query=search_query,
        selected_status=selected_status,
        selected_class=selected_class,
        selected_month=selected_month,
        status_labels=CONTRIBUTION_STATUS_LABELS,
        simulated_rates=SIMULATED_RATES,
        generate_form=generate_form,
        rate_desc=RATE_DESCRIPTION,
    )


@admin_bp.route("/contributions/generate", methods=["POST"])
@role_required("admin")
def contributions_generate():
    form = AdminGenerateContributionForm()
    if form.validate_on_submit():
        try:
            parsed = datetime.strptime(form.billing_month.data.strip(), "%Y-%m").date()
            target_period = date(parsed.year, parsed.month, 1)
            result = generate_contributions_for_active_participants(target_period)
            period_str = result["period"].strftime("%B %Y")
            flash(
                f"Tagihan periode {period_str} berhasil diproses: "
                f"{result['created']} tagihan baru dibuat, {result['skipped']} dilewati (sudah ada) "
                f"dari total {result['total_active']} peserta aktif.",
                "success",
            )
        except ValueError as ve:
            flash(str(ve), "danger")
        except Exception:
            flash("Terjadi kesalahan sistem saat membuat tagihan bulanan.", "danger")
    else:
        for field, errors in form.errors.items():
            for err in errors:
                flash(f"Generate Tagihan: {err}", "danger")

    return redirect(url_for("admin.contributions_list"))


@admin_bp.route("/contributions/<int:contribution_id>")
@role_required("admin")
def contribution_detail(contribution_id):
    contribution = db.session.execute(
        select(Contribution).filter_by(id=contribution_id)
    ).scalar_one_or_none()

    if not contribution:
        abort(404)

    return render_template(
        "admin/contributions/detail.html",
        contribution=contribution,
        status_labels=CONTRIBUTION_STATUS_LABELS,
        payment_status_labels=PAYMENT_STATUS_LABELS,
        method_labels=VALID_PAYMENT_METHODS,
        rate_desc=RATE_DESCRIPTION,
    )


@admin_bp.route("/payments")
@role_required("admin")
def payments_list():
    search_query = request.args.get("search", "").strip()
    selected_method = request.args.get("payment_method", "").strip()
    selected_status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = (
        select(Payment)
        .join(Payment.contribution)
        .join(Contribution.participant)
    )

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Payment.payment_number.ilike(pattern),
                Participant.participant_number.ilike(pattern),
                Participant.full_name.ilike(pattern),
            )
        )

    if selected_method in VALID_PAYMENT_METHODS:
        query = query.filter(Payment.payment_method == selected_method)

    if selected_status in PAYMENT_STATUS_LABELS:
        query = query.filter(Payment.status == selected_status)

    query = query.order_by(Payment.created_at.desc())

    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    payments = pagination.items

    return render_template(
        "admin/payments/list.html",
        payments=payments,
        pagination=pagination,
        search_query=search_query,
        selected_method=selected_method,
        selected_status=selected_status,
        status_labels=PAYMENT_STATUS_LABELS,
        method_labels=VALID_PAYMENT_METHODS,
        simulation_notice=SIMULATION_NOTICE,
    )


# ============================================================
# COMPLAINTS MANAGEMENT (STAGE 7)
# ============================================================

@admin_bp.route("/complaints")
@role_required("admin")
def complaints_list():
    status_filter = request.args.get("status", "").strip().upper()
    search_query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1
    per_page = 10

    query = select(Complaint).join(Complaint.user)

    if status_filter in VALID_COMPLAINT_STATUSES:
        query = query.filter(Complaint.status == status_filter)
    else:
        status_filter = ""

    if search_query:
        pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                Complaint.ticket_number.ilike(pattern),
                Complaint.subject.ilike(pattern),
                User.name.ilike(pattern),
                User.email.ilike(pattern),
            )
        )

    query = query.order_by(Complaint.created_at.desc(), Complaint.id.desc())
    pagination = db.paginate(query, page=page, per_page=per_page, error_out=False)
    complaints = pagination.items

    return render_template(
        "admin/complaints/list.html",
        complaints=complaints,
        pagination=pagination,
        status_filter=status_filter,
        search_query=search_query,
        status_labels=COMPLAINT_STATUS_LABELS,
        status_badges=COMPLAINT_STATUS_BADGES,
        valid_statuses=VALID_COMPLAINT_STATUSES,
    )


@admin_bp.route("/complaints/<int:complaint_id>")
@role_required("admin")
def complaint_detail(complaint_id):
    complaint = db.session.execute(
        select(Complaint).filter_by(id=complaint_id)
    ).scalar_one_or_none()

    if not complaint:
        abort(404)

    resolve_form = AdminResolveComplaintForm()
    reject_form = AdminRejectComplaintForm()

    return render_template(
        "admin/complaints/detail.html",
        complaint=complaint,
        status_labels=COMPLAINT_STATUS_LABELS,
        status_badges=COMPLAINT_STATUS_BADGES,
        resolve_form=resolve_form,
        reject_form=reject_form,
    )


@admin_bp.route("/complaints/<int:complaint_id>/start", methods=["POST"])
@role_required("admin")
def complaint_start(complaint_id):
    complaint = db.session.execute(
        select(Complaint).filter_by(id=complaint_id)
    ).scalar_one_or_none()

    if not complaint:
        abort(404)

    if complaint.status != STATUS_OPEN:
        flash(
            f"Tidak dapat memulai proses pengaduan. Status saat ini: {COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}.",
            "warning",
        )
        return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))

    try:
        start_complaint_processing(complaint)
        flash("Pengaduan mulai diproses.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception:
        flash("Terjadi kesalahan saat memproses pengaduan.", "danger")

    return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))


@admin_bp.route("/complaints/<int:complaint_id>/resolve", methods=["POST"])
@role_required("admin")
def complaint_resolve(complaint_id):
    complaint = db.session.execute(
        select(Complaint).filter_by(id=complaint_id)
    ).scalar_one_or_none()

    if not complaint:
        abort(404)

    if complaint.status != STATUS_IN_PROGRESS:
        flash(
            f"Hanya pengaduan dengan status Sedang Diproses yang dapat diselesaikan. Status saat ini: {COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}.",
            "warning",
        )
        return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))

    form = AdminResolveComplaintForm()
    if form.validate_on_submit():
        try:
            resolve_complaint(complaint, admin_response=form.admin_response.data)
            flash("Pengaduan berhasil diselesaikan.", "success")
            return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Terjadi kesalahan saat menyelesaikan pengaduan.", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))


@admin_bp.route("/complaints/<int:complaint_id>/reject", methods=["POST"])
@role_required("admin")
def complaint_reject(complaint_id):
    complaint = db.session.execute(
        select(Complaint).filter_by(id=complaint_id)
    ).scalar_one_or_none()

    if not complaint:
        abort(404)

    if complaint.status not in (STATUS_OPEN, STATUS_IN_PROGRESS):
        flash(
            f"Pengaduan dengan status '{COMPLAINT_STATUS_LABELS.get(complaint.status, complaint.status)}' tidak dapat ditolak.",
            "warning",
        )
        return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))

    form = AdminRejectComplaintForm()
    if form.validate_on_submit():
        try:
            reject_complaint(complaint, reason=form.admin_response.data)
            flash("Pengaduan telah ditolak.", "warning")
            return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception:
            flash("Terjadi kesalahan saat menolak pengaduan.", "danger")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(error, "danger")

    return redirect(url_for("admin.complaint_detail", complaint_id=complaint.id))

