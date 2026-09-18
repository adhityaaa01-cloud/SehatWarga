from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length, ValidationError


class FamilyMemberForm(FlaskForm):
    full_name = StringField(
        "Nama Lengkap",
        validators=[
            InputRequired(message="Nama lengkap wajib diisi."),
            Length(min=2, max=150, message="Nama harus antara 2 hingga 150 karakter."),
        ],
    )
    relationship = SelectField(
        "Hubungan Keluarga",
        choices=[
            ("", "-- Pilih Hubungan Keluarga --"),
            ("SPOUSE", "Pasangan"),
            ("CHILD", "Anak"),
            ("PARENT", "Orang Tua"),
            ("OTHER", "Lainnya"),
        ],
        validators=[
            DataRequired(message="Hubungan keluarga wajib dipilih."),
        ],
    )
    gender = SelectField(
        "Jenis Kelamin",
        choices=[
            ("", "-- Pilih Jenis Kelamin --"),
            ("MALE", "Laki-laki"),
            ("FEMALE", "Perempuan"),
        ],
        validators=[
            DataRequired(message="Jenis kelamin wajib dipilih."),
        ],
    )
    birth_date = DateField(
        "Tanggal Lahir",
        format="%Y-%m-%d",
        validators=[
            DataRequired(message="Tanggal lahir wajib diisi."),
        ],
    )
    submit = SubmitField("Simpan Anggota Keluarga")

    def validate_full_name(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Nama tidak boleh hanya berupa spasi.")

    def validate_birth_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Tanggal lahir tidak boleh di masa depan.")
