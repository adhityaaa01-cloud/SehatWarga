from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import select
from app.extensions import db
from app.models.user import User
from app.forms.auth import RegisterForm, LoginForm
from app.services.participant_service import register_citizen

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("citizen.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        cleaned_name = form.name.data.strip()
        cleaned_email = form.email.data.strip().lower()

        # Check for duplicate email
        existing_user = db.session.execute(
            select(User.id).filter_by(email=cleaned_email)
        ).scalar_one_or_none()

        if existing_user:
            flash("Email sudah terdaftar.", "danger")
            return render_template("auth/register.html", form=form), 400

        try:
            register_citizen(
                name=cleaned_name,
                email=cleaned_email,
                password=form.password.data,
                birth_date=form.birth_date.data,
                gender=form.gender.data,
                service_class=form.service_class.data,
            )
            flash("Registrasi berhasil! Silakan masuk menggunakan akun Anda.", "success")
            return redirect(url_for("auth.login"))
        except ValueError as ve:
            flash(str(ve), "danger")
            return render_template("auth/register.html", form=form), 400
        except Exception:
            flash("Terjadi kesalahan saat memproses registrasi. Silakan coba lagi.", "danger")
            return render_template("auth/register.html", form=form), 500

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("citizen.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        cleaned_email = form.email.data.strip().lower()
        user = db.session.execute(
            select(User).filter_by(email=cleaned_email)
        ).scalar_one_or_none()

        if not user or not user.check_password(form.password.data):
            flash("Email atau password salah.", "danger")
            return render_template("auth/login.html", form=form), 401

        if not user.is_active:
            flash("Akun Anda dinonaktifkan. Silakan hubungi administrator.", "danger")
            return render_template("auth/login.html", form=form), 403

        login_user(user)
        flash(f"Selamat datang kembali, {user.name}!", "success")

        # Check for safe internal next redirect
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/") and not next_page.startswith("//") and not next_page.startswith("/\\"):
            from urllib.parse import urlparse
            parsed = urlparse(next_page)
            if not parsed.netloc and not parsed.scheme:
                if user.role != "admin" and next_page.startswith("/admin"):
                    next_page = None
                elif user.role != "citizen" and next_page.startswith("/citizen"):
                    next_page = None
                if next_page:
                    return redirect(next_page)

        # Default redirect according to role
        if user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("citizen.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Anda telah berhasil keluar dari sistem.", "info")
    return redirect(url_for("main.index"))
