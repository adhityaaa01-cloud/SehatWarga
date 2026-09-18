"""
SehatWarga - Knowledge Base for AI Assistant
Contains verified facts, guidelines, system identity, and safety policies.
No web scraping, no dynamic external untrusted data.
"""

ASSISTANT_NAME = "Asisten SehatWarga"

SYSTEM_IDENTITY = (
    "Asisten SehatWarga adalah asisten digital untuk membantu pengguna memahami "
    "fitur SehatWarga, mencari informasi layanan, dan menemukan fasilitas kesehatan "
    "dari data SehatWarga."
)

ACADEMIC_DISCLAIMER = (
    "SehatWarga adalah portal prototype akademik untuk simulasi jaminan kesehatan masyarakat. "
    "Asisten SehatWarga bukan dokter, tidak memberikan diagnosis medis, dan tidak "
    "menggantikan peran tenaga kesehatan resmi."
)

MEDICAL_SAFETY_RESPONSE = (
    "Saya tidak dapat menentukan diagnosis. Untuk keluhan kesehatan, sebaiknya hubungi "
    "tenaga kesehatan atau fasilitas kesehatan terdekat untuk mendapatkan penanganan medis langsung."
)

EMERGENCY_SAFETY_RESPONSE = (
    "Kondisi yang Anda sebutkan memerlukan tindakan cepat. Segera hubungi atau datangi "
    "Unit Gawat Darurat (UGD) rumah sakit terdekat atau panggil bantuan medis darurat di sekitar Anda. "
    "Asisten ini tidak dapat memberikan pertolongan medis darurat."
)

SECRET_PROTECTION_RESPONSE = (
    "Sebagai Asisten SehatWarga, saya tidak memiliki akses ke konfigurasi internal server, "
    "kunci rahasia (seperti SECRET_KEY, DATABASE_URL), atau kredensial sistem demi alasan keamanan."
)

# These dictionaries are the same objects used by UI controllers and services.
from app.services.contribution_service import SIMULATED_RATES
from app.services.payment_service import VALID_PAYMENT_METHODS
from app.services.service_request_service import VALID_STATUSES, ALLOWED_TRANSITIONS as SERVICE_TRANSITIONS
from app.services.complaint_service import COMPLAINT_STATUS_LABELS, ALLOWED_TRANSITIONS as COMPLAINT_TRANSITIONS


def rupiah(amount):
    return "Rp" + f"{int(amount):,}".replace(",", ".")


def transition_description(transitions, labels):
    return "; ".join(f"{code} ({labels[code]}) → " + ", ".join(sorted(targets))
                     for code, targets in transitions.items() if targets)


KNOWLEDGE_TOPICS = {
    "ACCOUNT_GUIDE": "Panduan Akun & Profil: pilih Daftar, isi nama, email, kata sandi minimal 8 karakter, tanggal lahir, jenis kelamin, dan kelas layanan. Setelah masuk, buka Profil atau Kartu Digital.",
    "FAMILY_GUIDE": "Panduan Anggota Keluarga: buka Keluarga > Tambah Anggota Keluarga. Isi nama, hubungan (pasangan, anak, orang tua, atau lainnya), tanggal lahir, dan jenis kelamin. Anggota aktif dapat dipilih sebagai penerima pengajuan layanan. Tidak ada pengisian NIK pada model aktif.",
    "SERVICE_REQUEST_GUIDE": "Panduan Pengajuan Layanan Kesehatan: buka Layanan > Ajukan Layanan. Pilih penerima aktif, fasilitas aktif, jenis layanan, dan tanggal kunjungan; keluhan singkat opsional. Tidak ada unggah berkas pada implementasi ini. Alur status: " + transition_description(SERVICE_TRANSITIONS, VALID_STATUSES) + ". Warga hanya dapat membatalkan SUBMITTED atau VERIFIED miliknya; tindakan verifikasi, penjadwalan, penolakan, dan penyelesaian dilakukan admin.",
    "CONTRIBUTION_GUIDE": "Panduan Iuran Peserta — Tarif simulasi SehatWarga (bukan tarif resmi BPJS):\n" + "\n".join(f"- Kelas {code[-1]}: {rupiah(rate)} / bulan" for code, rate in SIMULATED_RATES.items()) + ".\nTagihan diterbitkan per peserta utama aktif, bukan dikalikan jumlah anggota keluarga. Jatuh tempo tanggal 10. Status UNPAID (Belum Dibayar), OVERDUE (Terlambat), atau PAID (Lunas). Buka menu Iuran untuk rincian.",
    "PAYMENT_GUIDE": "Panduan Pembayaran Simulasi: buka Iuran > rincian tagihan > Bayar. Metode: " + ", ".join(f"{label} ({code})" for code, label in VALID_PAYMENT_METHODS.items()) + ". Setujui pemberitahuan simulasi dan konfirmasikan sendiri. Pembayaran berhasil langsung melunasi tagihan dan menerbitkan kuitansi. Tidak ada transfer uang nyata, e-wallet, unggah bukti, atau verifikasi bank.",
    "COMPLAINT_GUIDE": "Panduan Pengaduan Warga: buka Pengaduan > Buat Pengaduan. Isi judul 5–150 karakter dan pesan 10–5000 karakter. Tidak ada field kategori. Tinjau sebelum mengirim. Pengaduan tidak dapat diedit/dihapus warga setelah terkirim. Alur: " + transition_description(COMPLAINT_TRANSITIONS, COMPLAINT_STATUS_LABELS) + ". Petugas wajib mengisi tanggapan minimal 10 karakter saat menyelesaikan atau menolak.",
    "FACILITY_GUIDE": "Cari fasilitas aktif di direktori Fasilitas berdasarkan nama, kota, atau jenis. Lokasi perangkat hanya digunakan setelah menekan Gunakan Lokasi Saya. Jarak merupakan perkiraan garis lurus. Koordinat pengguna tidak disimpan.",
    "GENERAL_HELP": "SehatWarga menyediakan kepesertaan dan kartu digital, anggota keluarga, pengajuan layanan, iuran, pembayaran simulasi, pengaduan, dan direktori fasilitas. Prototipe akademik independen, bukan BPJS atau pemerintah. Asisten hanya membaca informasi; semua tindakan tetap melalui form dan konfirmasi pengguna.",
}
