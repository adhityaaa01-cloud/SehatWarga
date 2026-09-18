from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError


class ComplaintCreateForm(FlaskForm):
    subject = StringField(
        "Judul Pengaduan",
        validators=[
            DataRequired(message="Judul pengaduan wajib diisi."),
            Length(min=5, max=150, message="Judul pengaduan harus antara 5 hingga 150 karakter."),
        ],
    )
    message = TextAreaField(
        "Isi Pengaduan",
        validators=[
            DataRequired(message="Isi pengaduan wajib diisi."),
            Length(min=10, max=5000, message="Isi pengaduan harus antara 10 hingga 5000 karakter."),
        ],
    )
    submit = SubmitField("Kirim Pengaduan")

    def validate_subject(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Judul pengaduan tidak boleh hanya berupa spasi.")
        if field.data and len(field.data.strip()) < 5:
            raise ValidationError("Judul pengaduan minimal 5 karakter setelah spasi dihilangkan.")

    def validate_message(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Isi pengaduan tidak boleh hanya berupa spasi.")
        if field.data and len(field.data.strip()) < 10:
            raise ValidationError("Isi pengaduan minimal 10 karakter setelah spasi dihilangkan.")


class AdminResolveComplaintForm(FlaskForm):
    admin_response = TextAreaField(
        "Tanggapan Penyelesaian",
        validators=[
            DataRequired(message="Tanggapan admin wajib diisi."),
            Length(min=10, max=5000, message="Tanggapan admin harus antara 10 hingga 5000 karakter."),
        ],
    )
    submit = SubmitField("Selesaikan Pengaduan")

    def validate_admin_response(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Tanggapan admin tidak boleh hanya berupa spasi.")
        if field.data and len(field.data.strip()) < 10:
            raise ValidationError("Tanggapan admin minimal 10 karakter setelah spasi dihilangkan.")


class AdminRejectComplaintForm(FlaskForm):
    admin_response = TextAreaField(
        "Alasan Penolakan",
        validators=[
            DataRequired(message="Alasan penolakan wajib diisi."),
            Length(min=10, max=5000, message="Alasan penolakan harus antara 10 hingga 5000 karakter."),
        ],
    )
    submit = SubmitField("Tolak Pengaduan")

    def validate_admin_response(self, field):
        if field.data and not field.data.strip():
            raise ValidationError("Alasan penolakan tidak boleh hanya berupa spasi.")
        if field.data and len(field.data.strip()) < 10:
            raise ValidationError("Alasan penolakan minimal 10 karakter setelah spasi dihilangkan.")
