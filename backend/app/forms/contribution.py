from datetime import date
from flask_wtf import FlaskForm
from wtforms import SelectField, BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired, Regexp


class SimulatedPaymentForm(FlaskForm):
    payment_method = SelectField(
        "Metode Pembayaran Simulasi",
        choices=[
            ("SIMULATION_CASH", "Simulasi Tunai (Kasir/Mitra)"),
            ("SIMULATION_TRANSFER", "Simulasi Transfer Bank"),
            ("SIMULATION_VIRTUAL_ACCOUNT", "Simulasi Virtual Account"),
        ],
        validators=[DataRequired(message="Pilih metode pembayaran simulasi.")],
    )
    agreement = BooleanField(
        "Saya memahami bahwa proses ini adalah simulasi akademik prototype SehatWarga tanpa transaksi keuangan nyata.",
        validators=[DataRequired(message="Anda harus menyetujui pernyataan simulasi untuk melanjutkan.")],
    )
    submit = SubmitField("Konfirmasi Pembayaran (Simulasi)")


class AdminGenerateContributionForm(FlaskForm):
    billing_month = StringField(
        "Periode Bulan Tagihan (YYYY-MM)",
        validators=[
            DataRequired(message="Bulan tagihan wajib diisi."),
            Regexp(r"^\d{4}-(0[1-9]|1[0-2])$", message="Format bulan tagihan harus YYYY-MM (contoh: 2026-09)."),
        ],
        default=lambda: date.today().strftime("%Y-%m"),
    )
    submit = SubmitField("Generate Tagihan Peserta Aktif")
