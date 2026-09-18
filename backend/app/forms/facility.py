from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange, ValidationError


class HealthFacilityForm(FlaskForm):
    facility_code = StringField(
        "Kode Fasilitas Kesehatan",
        validators=[
            DataRequired(message="Kode faskes wajib diisi."),
            Length(min=3, max=50, message="Kode faskes harus antara 3 hingga 50 karakter."),
        ],
    )
    name = StringField(
        "Nama Fasilitas Kesehatan",
        validators=[
            DataRequired(message="Nama faskes wajib diisi."),
            Length(min=2, max=150, message="Nama faskes harus antara 2 hingga 150 karakter."),
        ],
    )
    facility_type = SelectField(
        "Jenis Fasilitas",
        choices=[
            ("", "-- Pilih Jenis Faskes --"),
            ("PUSKESMAS", "Puskesmas"),
            ("CLINIC", "Klinik"),
            ("HOSPITAL", "Rumah Sakit"),
            ("DENTAL_CLINIC", "Klinik Gigi"),
            ("OTHER", "Lainnya"),
        ],
        validators=[
            DataRequired(message="Jenis fasilitas wajib dipilih."),
        ],
    )
    address = TextAreaField(
        "Alamat Lengkap",
        validators=[
            DataRequired(message="Alamat wajib diisi."),
        ],
    )
    city = StringField(
        "Kota / Kabupaten",
        validators=[
            DataRequired(message="Kota / Kabupaten wajib diisi."),
            Length(max=100, message="Nama kota maksimal 100 karakter."),
        ],
    )
    phone = StringField(
        "Nomor Telepon",
        validators=[
            Optional(),
            Length(max=30, message="Nomor telepon maksimal 30 karakter."),
        ],
    )
    latitude = DecimalField(
        "Latitude (Garis Lintang)",
        places=7,
        validators=[
            Optional(),
            NumberRange(min=Decimal("-90.0"), max=Decimal("90.0"), message="Latitude harus antara -90 dan 90."),
        ],
    )
    longitude = DecimalField(
        "Longitude (Garis Bujur)",
        places=7,
        validators=[
            Optional(),
            NumberRange(min=Decimal("-180.0"), max=Decimal("180.0"), message="Longitude harus antara -180 dan 180."),
        ],
    )
    is_active = BooleanField(
        "Status Aktif",
        default=True,
    )
    submit = SubmitField("Simpan Fasilitas Kesehatan")

    def validate_facility_code(self, field):
        if field.data:
            field.data = field.data.strip().upper()


class HealthFacilityEditForm(HealthFacilityForm):
    # On edit, facility_code can be read-only in UI, so DataRequired is not strictly needed or kept readonly
    pass
