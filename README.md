# SehatWarga

**SehatWarga** adalah prototipe portal layanan jaminan kesehatan masyarakat berbasis web modern yang dikembangkan menggunakan arsitektur modular **Flask 3.x** dan **MariaDB / MySQL**. Sistem ini dirancang secara independen sebagai instrumen riset dan demonstrasi sistem informasi *e-governance* untuk kebutuhan akademik.

---

> ### ⚠️ PEMBERITAHUAN & DISCLAIMER AKADEMIK PENTING
>
> 1. **Bukan Situs Resmi BPJS / Pemerintah**: Proyek ini merupakan **prototipe akademik independen** dan **tidak terafiliasi**, tidak disponsori, serta tidak didukung oleh BPJS Kesehatan, BPJS Ketenagakerjaan, Kementerian Kesehatan, maupun institusi pemerintah Republik Indonesia mana pun.
> 2. **Simulasi Transaksi & Pelayanan Medis**: Seluruh mekanisme pembayaran iuran, penerbitan kuitansi, rujukan faskes, jadwal layanan medis, dan nomor kepesertaan merupakan **simulasi perangkat lunak murni**. Tidak ada pemotongan uang riil, tidak ada integrasi perbankan nyata, dan tidak ada pelayanan medis klinis nyata.
> 3. **Bukan Layanan Diagnosis atau Kegawatdaruratan**: Sistem ini tidak menyediakan konsultasi medis, diagnosis berbasis kecerdasan buatan (AI), rekam medis klinis, maupun penanganan darurat (UGD/ambulans).
> 4. **Kepatuhan Data Simulasi**: Seluruh data yang digunakan dalam pengembangan, pengujian, dan demonstrasi adalah data dummy / simulasi.

---

## Daftar Isi

1. [Tech Stack & Arsitektur](#tech-stack--arsitektur)
2. [Fitur Utama Sistem (Stage 1 – 8)](#fitur-utama-sistem-stage-1--8)
3. [Panduan Instalasi & Menjalankan Sistem](#panduan-instalasi--menjalankan-sistem)
4. [Dokumentasi Perintah CLI](#dokumentasi-perintah-cli)
5. [Alur Status & State Machine](#alur-status--state-machine)
6. [Pengujian Otomatis (Automated Testing)](#pengujian-otomatis-automated-testing)
7. [Struktur Direktori Proyek](#struktur-direktori-proyek)

---

## Tech Stack & Arsitektur

- **Backend Framework**: Python 3.10+ / Flask 3.x
- **Arsitektur**: Flask Application Factory (`create_app`) & Modular Blueprints
- **Database & ORM**: MariaDB / MySQL dengan SQLAlchemy 2.x & Flask-SQLAlchemy
- **Migrasi Database**: Alembic melalui Flask-Migrate
- **Autentikasi & Sesi**: Flask-Login dengan hashing password melalui Werkzeug (default scrypt)
- **Formulir & Keamanan**: Flask-WTF (Proteksi CSRF aktif di seluruh transaksi mutasi)
- **Peta Interaktif**: Leaflet 1.9.4 & OpenStreetMap untuk visualisasi geospasial faskes
- **Frontend & UI/UX**: HTML5 Semantik, CSS3 murni berbasis design tokens terstruktur (`design.md`)

---

## Fitur Utama Sistem (Stage 1 – 8)

### 1. Autentikasi & Role-Based Access Control (RBAC)
- Registrasi mandiri warga dengan pembuatan identitas peserta otomatis (`SW-YYYY-XXXXXXXX`).
- Pemisahan hak akses mutlak antara peran **Warga / Peserta (`citizen`)** dan **Petugas Administrasi (`admin`)**.
- Proteksi terhadap *Open Redirect*, isolasi sesi, dan hashing password terenkripsi.

### 2. Administrasi Peserta & Anggota Keluarga
- Profil kepesertaan digital dan kartu identitas peserta digital ramah cetak.
- Pengelolaan data tanggungan keluarga (Anak, Pasangan, Orang Tua, dll.) dengan kode unik keluarga (`SWF-YYYY-XXXXXXXX`).

### 3. Katalog Fasilitas Kesehatan & Peta Interaktif
- Direktori fasilitas kesehatan tingkat pertama (FKTP) dan rujukan lanjutan (FKRTL).
- Visualisasi peta interaktif berbasis koordinat lintang/bujur riil menggunakan Leaflet & OpenStreetMap.
- Manajemen status keaktifan operasional faskes oleh admin.

### 4. Permohonan Layanan Kesehatan & Riwayat Audit
- Pengajuan permohonan layanan rujukan faskes mandiri atau untuk anggota keluarga dengan nomor pengajuan unik (`SWR-YYYYMMDD-XXXXXXXX`).
- Mesin alur status terstruktur: `SUBMITTED` ➔ `VERIFIED` ➔ `SCHEDULED` ➔ `COMPLETED` (atau `REJECTED` / `CANCELLED`).
- Catatan jejak audit permanen (`ServiceHistory`) di setiap mutasi status layanan.

### 5. Penagihan Iuran & Pembayaran Simulasi
- Tarif simulasi bersumber pada `SIMULATED_RATES`; lihat referensi business logic aktif di bawah.
- Penerbitan tagihan bulanan idempoten dengan batas jatuh tempo tanggal 10.
- Deteksi tagihan kedaluwarsa otomatis (`OVERDUE`).
- Simulasi pelunasan instan (`SIMULATION_CASH`, `SIMULATION_TRANSFER`, `SIMULATION_VIRTUAL_ACCOUNT`) dengan kuitansi digital bernomor unik (`SWP-YYYYMMDD-XXXXXXXX`).
- Halaman cetak bukti bayar elektronik resmi ramah dokumen fisik (`window.print()`).

### 6. Pengaduan Layanan Administratif (Complaint / Ticketing)
- Penyampaian aspirasi dan kendala administratif warga dengan nomor tiket acak kriptografis (`SWT-YYYYMMDD-XXXXXXXX`).
- Alur kerja status tiket: `OPEN` ➔ `IN_PROGRESS` ➔ `RESOLVED` / `REJECTED`.
- Penanganan resmi oleh admin dengan catatan tanggapan wajib minimal 10 karakter.
- Perlindungan integritas data pengaduan: tidak dapat diubah/dihapus warga setelah dikirim untuk menjamin akuntabilitas pelayanan publik.

### 7. Keamanan & Penanganan Kesalahan Sistem
- Halaman kesalahan kustom yang informatif dan aman tanpa membocorkan rincian *stack trace* atau kredensial database (HTTP 400, 403, 404, 500).
- Perlindungan penuh dari serangan Cross-Site Scripting (XSS) dengan auto-escaping Jinja2 (0 penggunaan filter `|safe`).
- Proteksi mutlak serangan Cross-Site Request Forgery (CSRF) pada seluruh *endpoint* pengubah data.
- Validasi ketat pengalihan URL (*Safe Relative Redirect*) pasca-otentikasi.

---

## Panduan Instalasi & Menjalankan Sistem

### 1. Prasyarat Lingkungan
- Python 3.10 atau versi yang lebih baru (direkomendasikan Python 3.12 - 3.14).
- MariaDB Server / MySQL Server aktif.

### 2. Kloning & Virtual Environment
```bash
# Pindah ke direktori proyek
cd /home/adhitya/Documents/WPF/SehatWarga

# Buat virtual environment
python3 -m venv .venv

# Aktifkan virtual environment
source .venv/bin/activate
```

### 3. Instalasi Pustaka Dependensi
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variable
Salin berkas template `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Sesuaikan konfigurasi koneksi MariaDB dan kunci rahasia pada file `.env`:
```env
FLASK_ENV=development
FLASK_DEBUG=0
SECRET_KEY=ganti-dengan-secret-acak-lokal
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/sehatwarga
```

### 5. Eksekusi Migrasi Database
Terapkan skema tabel terbaru ke database MariaDB:
```bash
flask --app run.py db upgrade
```
Pastikan status migrasi berada di versi *head*:
```bash
flask --app run.py db current
# Output: 3dfb67eddef4 (head)
```

### 6. Pengisian Data Awal (Seeding)
Jalankan perintah seeder CLI untuk mengisi fasilitas kesehatan dan data demo siap pakai:
```bash
# Seed katalog fasilitas kesehatan
flask --app run.py seed-facilities

# Seed data demonstrasi lengkap (Admin, Warga, Keluarga, Layanan, Iuran, Pengaduan)
flask --app run.py seed-demo --admin-password=AdminDemo123! --citizen-password=WargaDemo123!
```

### 7. Menjalankan Server Aplikasi
```bash
# Menjalankan server aplikasi dari root (kompatibilitas utama)
python run.py

# Atau menjalankan langsung dari direktori backend
python backend/run.py
```
Aplikasi dapat dibuka melalui peramban web pada:
- Portal Utama: `http://127.0.0.1:5000/`
- Health Check: `http://127.0.0.1:5000/health`

### Kredensial Akun Demonstrasi
- **Administrator**:
  - Email: `admin.demo@sehatwarga.test`
  - Password: `AdminDemo123!`
- **Warga / Peserta**:
  - Email: `warga.demo@sehatwarga.test`
  - Password: `WargaDemo123!`

---

## Dokumentasi Perintah CLI

Sistem SehatWarga dilengkapi perintah antarmuka baris perintah (CLI) untuk administrasi operasional:

### 1. `create-admin`
Membuat akun administrator baru secara interaktif atau terpandu:
```bash
flask --app run.py create-admin
```

### 2. `seed-facilities`
Mengisi data awal fasilitas kesehatan (Puskesmas, Klinik, Rumah Sakit Umum) beserta titik koordinat peta secara idempoten:
```bash
flask --app run.py seed-facilities
```

### 3. `generate-contributions`
Menerbitkan tagihan iuran bulanan untuk seluruh peserta aktif:
```bash
# Menerbitkan untuk bulan berjalan (default)
flask --app run.py generate-contributions

# Menerbitkan untuk periode tertentu (format YYYY-MM)
flask --app run.py generate-contributions --month 2026-10
```

### 4. `update-overdue`
Memindai seluruh tagihan berstatus `UNPAID` yang melewati tanggal jatuh tempo dan mengubah statusnya menjadi `OVERDUE`:
```bash
# Menggunakan tanggal hari ini
flask --app run.py update-overdue

# Menggunakan tanggal referensi simulasi
flask --app run.py update-overdue --as-of 2026-09-15
```

### 5. `seed-demo`
Membuat paket data demonstrasi lengkap dan idempoten untuk simulasi pengujian dan presentasi:
```bash
flask --app run.py seed-demo [--admin-password <password>] [--citizen-password <password>]
```

---

## Alur Status & State Machine

### 1. Alur Permohonan Layanan Kesehatan (`ServiceRequest`)
```text
           ┌──────────────────────┐
           │      SUBMITTED       │
           └──────────┬───────────┘
                      │
        ┌─────────────┴─────────────┐
        │ [Admin Verifikasi]        │ [Warga Batal / Admin Tolak]
        ▼                           ▼
 ┌──────────────┐            ┌──────────────┐
 │   VERIFIED   │            │  CANCELLED / │
 └──────┬───────┘            │   REJECTED   │
        │                    └──────────────┘
        │ [Admin Jadwalkan]
        ▼
 ┌──────────────┐
 │  SCHEDULED   │
 └──────┬───────┘
        │ [Faskes Selesaikan Pelayanan]
        ▼
 ┌──────────────┐
 │  COMPLETED   │
 └──────────────┘
```

### 2. Alur Pengaduan Layanan Administratif (`Complaint`)
```text
                  ┌──────────────────────┐
                  │         OPEN         │
                  └──────────┬───────────┘
                             │
               ┌─────────────┴─────────────┐
               │ [Admin Mulai Proses]      │ [Admin Tolak + Alasan]
               ▼                           ▼
        ┌──────────────┐            ┌──────────────┐
        │ IN_PROGRESS  │            │   REJECTED   │
        └──────┬───────┘            └──────────────┘
               │                           ▲
               │                           │ [Admin Tolak + Alasan]
               │ [Admin Selesaikan]        │
               ├───────────────────────────┘
               ▼
        ┌──────────────┐
        │   RESOLVED   │
        └──────────────┘
```

### 3. Alur Penagihan Iuran & Pembayaran Simulasi (`Contribution`)
```text
 ┌──────────────┐
 │    UNPAID    │ ──(Lewat Jatuh Tempo)──> ┌──────────────┐
 └──────┬───────┘                          │   OVERDUE    │
        │                                  └──────┬───────┘
        │ [Bayar Simulasi]                        │ [Bayar Simulasi]
        └───────────────────┬─────────────────────┘
                            ▼
                     ┌──────────────┐
                     │     PAID     │ ──> (Penerbitan Kuitansi Digital SWP)
                     └──────────────┘
```

---

## Pengujian Otomatis (Automated Testing)

Seluruh komponen logika bisnis, otorisasi RBAC, integritas data, dan keamanan form diuji menggunakan pengujian unit otomatis bawaan Python (`unittest`).

### Menjalankan Seluruh Rangkaian Uji
```bash
.venv/bin/python -m unittest discover tests
```

### Rekapitulasi pengujian

Hasil run terbaru dan rincian baseline dicatat dalam `REDESIGN_REPORT.md` dan
`qa/test-results.txt`. Ada 112 test lama dan test tambahan integrasi/safety.
Test menggunakan `create_app(TestingConfig)` **sebelum** database diinisialisasi;
SQLite in-memory terpisah per suite dan CSRF tetap aktif. `.env` tidak dimuat.
Test tidak memerlukan MySQL atau API key. Tidak ada expectation keamanan yang dilonggarkan.

---

## Struktur Direktori Proyek

```text
sehatwarga/
├── backend/
│   ├── app/
│   │   ├── __init__.py                 # Application factory (templates & static path resolver)
│   │   ├── cli.py                      # Perintah CLI (create-admin, seed-facilities, seed-demo, dll.)
│   │   ├── decorators.py               # Proteksi hak akses peran (@role_required)
│   │   ├── extensions.py               # Inisialisasi DB, Migrate, LoginManager, CSRF
│   │   ├── forms/                      # Validasi formulir WTForms (auth, citizen, admin)
│   │   ├── models/                     # Model ORM SQLAlchemy (9 entitas terhubung)
│   │   │   ├── user.py                 # Pengguna & peran (citizen/admin)
│   │   │   ├── participant.py          # Profil peserta jaminan
│   │   │   ├── family_member.py        # Anggota keluarga tanggungan
│   │   │   ├── health_facility.py      # Fasilitas kesehatan rujukan
│   │   │   ├── service_request.py      # Permohonan layanan kesehatan
│   │   │   ├── service_history.py      # Jejak audit riwayat mutasi layanan
│   │   │   ├── contribution.py         # Tagihan iuran bulanan
│   │   │   ├── payment.py              # Catatan transaksi pembayaran simulasi
│   │   │   └── complaint.py            # Tiket pengaduan layanan administratif
│   │   ├── routes/                     # Blueprint controllers
│   │   │   ├── auth.py                 # Autentikasi login/logout/registrasi & proteksi redirect
│   │   │   ├── citizen.py              # Fitur warga (layanan, keluarga, iuran, tiket)
│   │   │   ├── admin.py                # Panel administrasi & verifikasi alur kerja
│   │   │   ├── facilities.py           # Katalog fasilitas & rute publik
│   │   │   └── main.py                 # Beranda & pemeriksaan kesehatan (/health)
│   │   └── services/                   # Layanan logika bisnis inti
│   ├── config.py                       # Konfigurasi backend & pemuatan .env
│   ├── run.py                          # Titik masuk eksekusi langsung backend
│   └── requirements.txt                # Dependensi kanonikal paket Python backend
├── frontend/
│   ├── static/                         # Aset web statis (CSS, JS, Uploads)
│   │   ├── css/main.css                # Stylesheet & desain tokens UI/UX
│   │   ├── js/main.js                  # Interaktivitas DOM & script global
│   │   ├── js/facility-map.js          # Integrasi peta geospasial Leaflet
│   │   └── uploads/                    # Direktori penampung file statis/upload
│   └── templates/                      # Template Jinja2 responsif
│       ├── base.html                   # Shell navigasi & footer global
│       ├── admin/                      # Tampilan dashboard & manajemen admin
│       ├── auth/                       # Tampilan masuk & daftar
│       ├── citizen/                    # Tampilan portal mandiri warga
│       ├── errors/                     # Halaman kesalahan kustom (400, 403, 404, 500)
│       └── public/                     # Tampilan beranda & katalog faskes
├── migrations/                         # Riwayat migrasi skema database Alembic
├── tests/                              # Pengujian otomatis dengan SQLite terpisah
├── design.md                           # Panduan sistem desain & visual tokens UI/UX
├── .env.example                        # Template variabel konfigurasi lingkungan
├── .gitignore                          # Berkas pengecualian Git
├── requirements.txt                    # Wrapper dependensi root (-r backend/requirements.txt)
├── run.py                              # Titik masuk eksekusi utama root
└── README.md                           # Dokumentasi lengkap proyek
```



## Redesign dan Gemini

Antarmuka Modern Civic Health menggunakan Flask/Jinja, CSS, JavaScript vanilla,
Plus Jakarta Sans dan IBM Plex Mono WOFF2 lokal. Tidak ada migrasi schema atau
perubahan URL route. Sidebar admin, drawer mobile, tabel menjadi card list,
focus states, dan reduced motion tersedia.

Preview aman menggunakan database sementara (semua data hilang saat dihentikan):

```bash
python -m pip install -r requirements.txt
python scripts/preview.py
# Buka http://127.0.0.1:5055
```

Preview menggunakan akun demonstrasi yang sudah didefinisikan seeder lama:
`admin.demo@sehatwarga.test` / `AdminDemo123!` dan
`warga.demo@sehatwarga.test` / `WargaDemo123!`. Hanya untuk preview lokal.

Untuk aplikasi dengan database development yang sudah dikonfigurasi, jalankan
`python run.py` (http://127.0.0.1:5000). Debug default mati. Tidak perlu migrasi baru
untuk redesign ini. Pertahankan `.env` lokal Anda; jangan menimpanya dengan file contoh.

Untuk mengaktifkan Gemini, edit variabel berikut **hanya pada `.env` lokal**:

```dotenv
AI_PROVIDER=gemini
AI_API_KEY=ISI_KEY_PRIBADI_DI_LOKAL
AI_MODEL=ISI_ID_MODEL_YANG_TERSEDIA_DI_AKUN_GEMINI
```

Jangan kirim key ke chat, template, JavaScript, atau Git. Restart Flask setelah
mengubah konfigurasi. `AI_PROVIDER=fallback` berjalan tanpa key dan tanpa panggilan AI.
Model/key/provider tidak valid, timeout, error SDK, maupun output JSON tidak valid
kembali ke fallback. SDK resmi: `google-genai==2.23.0`.

Gemini melakukan klasifikasi intent JSON dengan timeout 8 detik (tanpa retry SDK).
Jawaban kemudian disusun dari knowledge base terverifikasi dan hasil query DB.
Safety check dijalankan lokal terlebih dahulu. Data akun, koordinat, serta riwayat
chat tidak dikirim ke provider. Identifier numerik, kode peserta, e-mail, URL, dan
string token panjang disaring dari pesan. Asisten tidak melakukan tindakan tulis
atau pembayaran dan tidak membuat diagnosis. Mode ini bukan chatbot medis bebas.

Rujukan: [Dokumentasi SDK resmi Google Gen AI](https://googleapis.github.io/python-genai/).

Verifikasi:

```bash
python -m unittest discover tests -v
python -m compileall -q backend tests scripts
python scripts/sync_knowledge.py --check
# Opsional untuk browser QA:
python -m pip install playwright
python -m playwright install chromium
python scripts/check_browser.py
```

Browser QA menghidupkan server localhost dengan SQLite sementara, menguji enam
viewport, drawer, form, dan asisten; hasil serta screenshot berada di `qa/`.
Untuk memakai Chromium yang sudah terpasang, atur `BROWSER_EXECUTABLE` ke path-nya.
Tidak perlu memasukkan dependensi browser QA ke runtime Flask.

<!-- BEGIN VERIFIED BUSINESS KNOWLEDGE -->

## Referensi business logic aktif

### Account Guide

Panduan Akun & Profil: pilih Daftar, isi nama, email, kata sandi minimal 8 karakter, tanggal lahir, jenis kelamin, dan kelas layanan. Setelah masuk, buka Profil atau Kartu Digital.

### Family Guide

Panduan Anggota Keluarga: buka Keluarga > Tambah Anggota Keluarga. Isi nama, hubungan (pasangan, anak, orang tua, atau lainnya), tanggal lahir, dan jenis kelamin. Anggota aktif dapat dipilih sebagai penerima pengajuan layanan. Tidak ada pengisian NIK pada model aktif.

### Service Request Guide

Panduan Pengajuan Layanan Kesehatan: buka Layanan > Ajukan Layanan. Pilih penerima aktif, fasilitas aktif, jenis layanan, dan tanggal kunjungan; keluhan singkat opsional. Tidak ada unggah berkas pada implementasi ini. Alur status: SUBMITTED (Menunggu Verifikasi) → CANCELLED, REJECTED, VERIFIED; VERIFIED (Terverifikasi) → CANCELLED, REJECTED, SCHEDULED; SCHEDULED (Dijadwalkan) → COMPLETED. Warga hanya dapat membatalkan SUBMITTED atau VERIFIED miliknya; tindakan verifikasi, penjadwalan, penolakan, dan penyelesaian dilakukan admin.

### Contribution Guide

Panduan Iuran Peserta — Tarif simulasi SehatWarga (bukan tarif resmi BPJS):
- Kelas 1: Rp150.000 / bulan
- Kelas 2: Rp100.000 / bulan
- Kelas 3: Rp50.000 / bulan.
Tagihan diterbitkan per peserta utama aktif, bukan dikalikan jumlah anggota keluarga. Jatuh tempo tanggal 10. Status UNPAID (Belum Dibayar), OVERDUE (Terlambat), atau PAID (Lunas). Buka menu Iuran untuk rincian.

### Payment Guide

Panduan Pembayaran Simulasi: buka Iuran > rincian tagihan > Bayar. Metode: Simulasi Tunai (SIMULATION_CASH), Simulasi Transfer (SIMULATION_TRANSFER), Simulasi Virtual Account (SIMULATION_VIRTUAL_ACCOUNT). Setujui pemberitahuan simulasi dan konfirmasikan sendiri. Pembayaran berhasil langsung melunasi tagihan dan menerbitkan kuitansi. Tidak ada transfer uang nyata, e-wallet, unggah bukti, atau verifikasi bank.

### Complaint Guide

Panduan Pengaduan Warga: buka Pengaduan > Buat Pengaduan. Isi judul 5–150 karakter dan pesan 10–5000 karakter. Tidak ada field kategori. Tinjau sebelum mengirim. Pengaduan tidak dapat diedit/dihapus warga setelah terkirim. Alur: OPEN (Baru) → IN_PROGRESS, REJECTED; IN_PROGRESS (Sedang Diproses) → REJECTED, RESOLVED. Petugas wajib mengisi tanggapan minimal 10 karakter saat menyelesaikan atau menolak.

### Facility Guide

Cari fasilitas aktif di direktori Fasilitas berdasarkan nama, kota, atau jenis. Lokasi perangkat hanya digunakan setelah menekan Gunakan Lokasi Saya. Jarak merupakan perkiraan garis lurus. Koordinat pengguna tidak disimpan.

### General Help

SehatWarga menyediakan kepesertaan dan kartu digital, anggota keluarga, pengajuan layanan, iuran, pembayaran simulasi, pengaduan, dan direktori fasilitas. Prototipe akademik independen, bukan BPJS atau pemerintah. Asisten hanya membaca informasi; semua tindakan tetap melalui form dan konfirmasi pengguna.

<!-- END VERIFIED BUSINESS KNOWLEDGE -->
