from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, DateField, SelectField, SubmitField
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    EqualTo,
    ValidationError,
)


class RegisterForm(FlaskForm):
    name = StringField(
        "Nama Lengkap",
        validators=[
            DataRequired(message="Nama lengkap wajib diisi."),
            Length(min=2, max=100, message="Nama harus antara 2 hingga 100 karakter."),
        ],
    )
    email = StringField(
        "Alamat Email",
        validators=[
            DataRequired(message="Alamat email wajib diisi."),
            Email(message="Format email tidak valid."),
            Length(max=150, message="Email maksimal 150 karakter."),
        ],
    )
    password = PasswordField(
        "Kata Sandi",
        validators=[
            DataRequired(message="Kata sandi wajib diisi."),
            Length(min=8, message="Kata sandi minimal 8 karakter."),
        ],
    )
    confirm_password = PasswordField(
        "Konfirmasi Kata Sandi",
        validators=[
            DataRequired(message="Konfirmasi kata sandi wajib diisi."),
            EqualTo("password", message="Konfirmasi kata sandi tidak cocok."),
        ],
    )
    birth_date = DateField(
        "Tanggal Lahir",
        format="%Y-%m-%d",
        validators=[
            DataRequired(message="Tanggal lahir wajib diisi."),
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
    service_class = SelectField(
        "Kelas Layanan Simulasi",
        choices=[
            ("", "-- Pilih Kelas Layanan --"),
            ("CLASS_1", "Kelas 1 (Simulasi Rawat Inap Kelas 1)"),
            ("CLASS_2", "Kelas 2 (Simulasi Rawat Inap Kelas 2)"),
            ("CLASS_3", "Kelas 3 (Simulasi Rawat Inap Kelas 3)"),
        ],
        validators=[
            DataRequired(message="Kelas layanan wajib dipilih."),
        ],
    )
    submit = SubmitField("Daftar Sekarang")

    def validate_name(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Nama tidak boleh hanya berupa spasi.")

    def validate_birth_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Tanggal lahir tidak boleh di masa depan.")


class LoginEmail(Email):
    """Accept the existing seeder's reserved offline demo domain at login only.

    Normal addresses retain WTForms validation. This never bypasses password,
    active-account checks, CSRF or role authorization.
    """
    def __call__(self, form, field):
        if isinstance(field.data, str) and field.data.strip().lower().endswith("@sehatwarga.test"):
            from email_validator import validate_email, EmailNotValidError
            try:
                validate_email(field.data.strip(), check_deliverability=False, test_environment=True)
            except EmailNotValidError as error:
                raise ValidationError(self.message or "Format email tidak valid.") from error
        else:
            super().__call__(form, field)


class LoginForm(FlaskForm):
    email = StringField(
        "Alamat Email",
        validators=[
            DataRequired(message="Alamat email wajib diisi."),
            LoginEmail(message="Format email tidak valid."),
        ],
    )
    password = PasswordField(
        "Kata Sandi",
        validators=[
            DataRequired(message="Kata sandi wajib diisi."),
        ],
    )
    submit = SubmitField("Masuk")
