from datetime import date
from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


class ServiceRequestForm(FlaskForm):
    beneficiary_type = SelectField(
        "Penerima Layanan",
        choices=[
            ("SELF", "Peserta Utama (Saya Sendiri)"),
            ("FAMILY", "Anggota Keluarga Terdaftar"),
        ],
        default="SELF",
        validators=[DataRequired(message="Pilih penerima layanan.")],
    )
    family_member_id = SelectField(
        "Pilih Anggota Keluarga",
        choices=[],
        validators=[Optional()],
    )
    health_facility_id = SelectField(
        "Fasilitas Kesehatan Tujuan",
        choices=[],
        validators=[DataRequired(message="Fasilitas kesehatan wajib dipilih.")],
    )
    service_type = SelectField(
        "Jenis Layanan",
        choices=[
            ("", "-- Pilih Jenis Layanan --"),
            ("GENERAL", "Layanan Umum"),
            ("DENTAL", "Layanan Gigi"),
            ("MATERNAL", "Layanan Ibu dan Anak"),
            ("SPECIALIST", "Layanan Spesialis"),
            ("OTHER", "Layanan Lainnya"),
        ],
        validators=[DataRequired(message="Jenis layanan wajib dipilih.")],
    )
    scheduled_date = DateField(
        "Rencana Tanggal Kunjungan",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Tanggal kunjungan wajib diisi.")],
    )
    complaint_summary = TextAreaField(
        "Keperluan / Keluhan Singkat",
        validators=[
            Optional(),
            Length(max=500, message="Keperluan layanan maksimal 500 karakter."),
        ],
    )
    submit = SubmitField("Kirim Pengajuan Layanan")

    def validate_scheduled_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Tanggal layanan tidak boleh di masa lalu.")

    def validate_complaint_summary(self, field):
        if field.data and field.data.strip():
            if len(field.data.strip()) < 5:
                raise ValidationError("Keperluan layanan minimal 5 karakter.")


class ScheduleServiceRequestForm(FlaskForm):
    scheduled_date = DateField(
        "Tanggal Layanan Ditetapkan",
        format="%Y-%m-%d",
        validators=[DataRequired(message="Tanggal jadwal wajib diisi.")],
    )
    note = TextAreaField("Catatan Jadwal", validators=[Optional()])
    submit = SubmitField("Tetapkan Jadwal")

    def validate_scheduled_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Jadwal layanan tidak boleh di masa lalu.")


class RejectServiceRequestForm(FlaskForm):
    reason = TextAreaField(
        "Alasan Penolakan",
        validators=[
            DataRequired(message="Alasan penolakan wajib diisi."),
            Length(min=5, max=500, message="Alasan penolakan harus antara 5 hingga 500 karakter."),
        ],
    )
    submit = SubmitField("Tolak Pengajuan")

    def validate_reason(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Alasan penolakan tidak boleh hanya berupa spasi.")
