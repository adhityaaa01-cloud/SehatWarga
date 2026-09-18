# Laporan redesign SehatWarga

## Peningkatan visual ekosistem — revisi terbaru

- Palet diperluas dari navy/teal menjadi enam warna terarah: navy untuk kepercayaan,
  teal untuk kepesertaan, biru untuk layanan, amber untuk iuran, coral untuk
  pengaduan, dan violet untuk asisten.
- Hero publik dibangun ulang dengan ilustrasi orbit layanan 3D berbasis CSS,
  empat node layanan, status sistem, trust indicator, dan hierarki CTA baru.
- Akses cepat kini berupa empat service tile berwarna. Bagian fitur, alur tiga
  langkah, direktori fasilitas, dan CTA akhir memiliki komposisi visual berbeda.
- Dashboard warga/admin, kartu statistik, tabel, form autentikasi, fasilitas,
  dan asisten memakai depth, aksen kategori, serta feedback interaksi konsisten.
- Motion mencakup scroll reveal progresif, pointer tilt terbatas, orbit, radar,
  progress scroll, hover lift, dan shimmer tombol. Konten tetap terlihat tanpa
  JavaScript dan seluruh motion non-esensial tunduk pada reduced-motion.
- Tidak ada perubahan route, model, migration, service, validasi, CSRF, RBAC,
  database, ataupun business logic. Suite lengkap 143 test tetap lulus.

## Max Motion 3D — revisi lanjutan

- Hero kini memiliki particle network Canvas yang bereaksi terhadap pointer,
  spotlight dinamis, 18 serpihan energi, orbit berlapis, pulsating shell, serta
  depth node yang lebih kuat.
- Kartu statistik, akses layanan, fasilitas, profil, autentikasi, dan action card
  mendapat pointer tilt, spotlight lokal, translate-Z, serta shadow responsif.
- Tombol utama memakai efek magnetic pointer dengan perpindahan kecil sehingga
  target klik tetap stabil. Headline memakai spektrum warna bergerak dan konten
  hero masuk secara staggered.
- Panel alur, mini-map, dashboard, summary panel, serta border autentikasi memiliki
  motion 3D tersendiri. Particle loop berhenti ketika hero keluar viewport atau
  tab tidak aktif, DPR dibatasi 1,5, dan jumlah partikel dibatasi maksimal 56.
- Perangkat pointer kasar, layar kecil, mode cetak, dan `prefers-reduced-motion`
  memperoleh versi ringan atau statis. Setelah revisi, syntax JavaScript valid
  dan seluruh 143 test kembali lulus.

## Living Aurora Background — revisi warna

- Background putih/abu dominan diganti dengan aurora mesh global lima warna:
  teal, biru, violet, coral, dan amber dalam saturasi lembut yang konsisten.
- Lima blob organik bergerak lintas layar, dua orbit dekoratif berputar, grid
  perspektif berjalan, dan spotlight background mengikuti pointer.
- Kartu statistik memakai tint kategori masing-masing; panel detail, tabel,
  fasilitas, action card, sidebar, navbar, empty state, dan footer ikut memakai
  permukaan berwarna transparan yang selaras.
- Mobile mengurangi opacity serta detail dekorasi. Reduced-motion membekukan
  seluruh gerakan background tetapi tetap mempertahankan komposisi warnanya.
- Navigasi sticky dan semua lapisan interaktif dipertahankan di atas background.
  Syntax CSS/JavaScript valid dan seluruh 143 test tetap lulus.

Tanggal verifikasi: 16 September 2026. Implementasi dilakukan pada salinan arsip yang dikirim, bukan langsung pada `/home/adhitya/Documents/WPF/SehatWarga` di laptop. Tidak ada perubahan schema/migration, penghapusan fitur, atau perubahan URL route. Arsip asal tidak berisi repository Git; salinan baseline bersih dibuat sebelum perubahan. Tidak ada commit otomatis.

## Ringkasan hasil

Flask, Jinja, CSS, JavaScript vanilla, Leaflet dan OpenStreetMap dipertahankan. Identitas Modern Civic Health menggunakan navy/teal, permukaan putih, font Plus Jakarta Sans dan IBM Plex Mono WOFF2 lokal beserta lisensi. Autentikasi, RBAC, CSRF, validasi server, escaping, ownership check, state machine, dan transaksi pembayaran tetap aktif.

Gemini menggunakan adapter SDK resmi `google-genai==2.23.0` untuk klasifikasi intent JSON. Jawaban berasal dari knowledge base terverifikasi atau database. Provider tidak melakukan perubahan data. Konfigurasi kosong/tidak valid, error, timeout, dan output tidak valid kembali ke fallback lama.

## Audit dan baseline

- 51 rule route termasuk static; daftar lengkap ada di `qa/routes.txt`. 40 template diaudit beserta backend, model, service, migration, CSS/JavaScript, konfigurasi dan test.
- Fitur warga: register/login/logout, profil, kartu digital, keluarga, permohonan layanan, iuran, pembayaran simulasi, kuitansi, pengaduan.
- Fitur admin: dashboard, pengelolaan fasilitas, verifikasi/jadwal/penyelesaian layanan, penerbitan tagihan, pembayaran dan penanganan pengaduan.
- Fasilitas: direktori/filter/detail, peta, jarak, lokasi dengan persetujuan. Asisten awal berbasis fallback/keyword.
- Masalah awal: navigasi mobile kehilangan akses menu, gaya/font tidak konsisten, inline style berulang, prioritas dashboard kurang jelas, kontras/fokus belum memadai, knowledge base berbeda dari implementasi.
- Baseline aktual 112 test, berbeda dengan dokumentasi lama yang menyebut 91. Percobaan awal pada SQLite tanpa fixture lengkap menghasilkan 4 failure dan 200 error termasuk subtest. Setelah setup database terisolasi, tersisa 7 failure dan 1 error (104 pass); root cause diperbaiki, bukan menghapus pengujian.
- TestingConfig diterapkan pada create_app sebelum inisialisasi extension. Suite membuat schema SQLite in-memory sendiri, CSRF tetap aktif, dan tidak memuat `.env` atau memakai MySQL produksi.

## Konflik dan perbaikan akar masalah

| Temuan | Penyelesaian |
| --- | --- |
| Tarif kelas 3/anggota keluarga berbeda antara AI dan business logic | KB memakai SIMULATED_RATES: 150.000/100.000/50.000 per peserta utama; tidak dikalikan keluarga. |
| Status dan metode pembayaran generik/tidak aktif | KB mengimpor konstanta/state machine aktif; README dibangkitkan oleh scripts/sync_knowledge.py. |
| Panduan NIK, upload, kategori pengaduan tidak sesuai model | Panduan disesuaikan dengan field dan flow aktif. |
| func.year tidak portable SQLite | Menggunakan SQLAlchemy extract; perilaku filter tahun tetap sama. |
| SQLite tidak menegakkan panjang VARCHAR seperti asumsi test lama | Validasi gender/kelas dilakukan pada service sebelum persist. |
| Test tiket melarang digit user ID muncul di kode tanggal acak | Diganti pembuktian deterministik bahwa generator tidak memakai identitas user; tanggal dapat mengandung digit yang sama secara sah. |
| Fixture fasilitas/test cleanup tidak tepat | Seed eksplisit di database test dan nama relasi histories diperbaiki. |
| Akun demo .test ditolak validator login | Login menerima domain demo khusus; password, CSRF, dan validator registrasi tetap berlaku. |
| family_member_number/participant.nik tidak ada pada model | Memakai member_number aktif; baris NIK yang tidak tersedia dihapus dari tampilan. |
| Akun nonaktif masih dapat mengakses role guard | role_required juga memeriksa is_active. |

## Perubahan UI per halaman

| Area | Hasil |
| --- | --- |
| Shell publik | Navbar ringkas, active state, skip link, footer akademik ringkas. |
| Shell warga | Menu layanan dikelompokkan, dropdown pengguna dan logout POST di user menu. |
| Shell admin | Sidebar desktop dan drawer mobile; tautan tetap tersedia. |
| Beranda | Hero manfaat, CTA daftar/layanan, alur tiga langkah, fasilitas dan CTA akhir tanpa ilustrasi/angka palsu. |
| Dashboard warga | Ringkasan kepesertaan, maksimal empat statistik utama, tagihan penting, quick action, aktivitas dan jejak status; informasi sekunder lewat disclosure. |
| Dashboard admin | Prioritas verifikasi layanan, pengaduan terbuka, tagihan bermasalah, fasilitas nonaktif; tabel terbaru dan statistik sekunder. |
| Form/login/register | Komponen label/input/error/disabled/focus konsisten; error terhubung ARIA dan pencegahan submit ganda. |
| Daftar/detail | Filter, badge berteks, empty state, tabel menjadi card berlabel di mobile; riwayat layanan/pengaduan tetap tersedia. |
| Kartu/kuitansi | Identitas visual baru; aturan print menyembunyikan navigasi dan kontrol. |
| Fasilitas | Filter/peta/hasil lebih rapi, loading/empty/error, popup DOM aman, lokasi hanya setelah tombol ditekan. |
| Asisten | Suggested prompts kontekstual, typing/loading, retry, kartu fasilitas, peta hanya bila koordinat valid, input Enter/Shift+Enter, timeout fetch20 detik. |

Drawer mendukung overlay, Escape, focus trap, pengembalian fokus, ARIA dan scroll lock. Tombol sekitar44px, fokus jelas, heading utama tunggal dan status tidak hanya warna. Teks muted disesuaikan dari #60747D menjadi #586C75 untuk memperbaiki kontras pada surface sekunder. Tombol bantuan ditempatkan di area footer yang menyediakan ruang sehingga tidak menutup isi.

Sebagian besar pola inline umum diekstrak menjadi class reusable. Inline dinamis/kasus khusus yang tersisa dipertahankan agar kondisi Jinja tidak rusak; refactor tidak mengklaim nol inline style.

## Motion

Content fade-up6px/200ms, hover kartu maksimal−2px, tombol aktif scale(.98), drawer slide220ms, flash slide-in, chat fade-up, transisi timeline, spinner dan skeleton peta. Motion memakai transform/opacity dan mendukung prefers-reduced-motion. Tidak ditambahkan modal palsu atau animasi dekoratif looping.

## Keamanan dan cara konfigurasi Gemini

Safety check deterministik berjalan sebelum provider: darurat, diagnosis/resep, ekstraksi rahasia, prompt injection dan permintaan berbahaya ditangani lokal. Hanya pesan saat ini yang dibatasi dan disaring yang dapat dikirim; riwayat, koordinat, data akun, NIK/nomor peserta penuh tidak dimasukkan ke konteks provider. Jangan masukkan data pribadi ke chat. Filter berbasis pola tetap memiliki keterbatasan terhadap format/obfuscation yang belum dikenali; output model hanya menjadi intent, bukan instruksi/tool bebas.

Schema: intent, confidence, requires_location, facility_type, city, safe_to_answer, reason. Semua intent yang diminta didukung. Timeout SDK8 detik dengan satu percobaan. Log error memakai pesan statis. Ringkasan akun membutuhkan autentikasi/role dan query ownership lokal. Fasilitas berasal dari database aktif. Tidak ada penyimpanan permanen chat maupun tindakan bayar/kirim pengaduan otomatis.

Pada `.env` lokal yang sudah dimiliki, isi hanya di komputer sendiri:

```dotenv
AI_PROVIDER=gemini
AI_API_KEY=ISI_KEY_PRIBADI_DI_LOKAL
AI_MODEL=ISI_ID_MODEL_YANG_TERSEDIA_DI_AKUN_GEMINI
```

Restart Flask. Untuk tanpa AI gunakan AI_PROVIDER=fallback. `.env.example` hanya placeholder. SDK: https://googleapis.github.io/python-genai/.

## Menjalankan aplikasi dan test

Ekstrak arsip ke folder terpisah untuk meninjau perubahan. Pertahankan `.env` lokal pengguna; jangan menimpanya. Perintah berikut dijalankan dari root proyek hasil ekstraksi:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Preview aman: SQLite in-memory, tanpa membaca .env, data demo lama
python scripts/preview.py
# Buka http://127.0.0.1:5055 ; Ctrl+C untuk berhenti
# Test dan konsistensi knowledge base
python -m unittest discover tests -v
python -m compileall -q backend tests scripts
python scripts/sync_knowledge.py --check
# Aplikasi dengan database development lokal yang telah dikonfigurasi
python run.py
# Review di repository Git lokal setelah perubahan diterapkan
# Jangan jalankan git add . atau commit tanpa meninjau file
 git status
 git diff --stat
 git diff
```

Preview memakai akun seed-demo lama: warga.demo@sehatwarga.test / WargaDemo123! dan admin.demo@sehatwarga.test / AdminDemo123!. Ini akun fixture lokal sementara, bukan kredensial produksi. Untuk pengujian browser opsional, petunjuk instalasi Playwright ada di README. Audit axe opsional ada di scripts/check_accessibility.py (AXE_SOURCE dan BROWSER_EXECUTABLE).

## Hasil verifikasi

| Pemeriksaan | Hasil |
| --- | --- |
| Seluruh automated unittest | 143 pass, 0 fail/error |
| Browser responsive/interaksi | 321 pass, 0 fail; viewport320/375/480/768/1024/1440 |
| Axe WCAG A/AA dan2.1 | 22 kombinasi halaman/viewport, 0 violation otomatis |
| Print media kartu dan kuitansi | 2 halaman lulus: navigasi tersembunyi, tanpa horizontal overflow |
| Python compileall dan JavaScript node --check | Lulus |
| Sinkronisasi KB README vs konstanta aktif | Lulus |
| Render StrictUndefined | Seluruh route halaman publik/warga/admin yang diuji lulus, termasuk detail relasi keluarga/pembayaran |

Cakupan mencakup register/login/logout, RBAC/ownership, CSRF, fasilitas, state machine layanan/pengaduan, iuran/pembayaran simulasi, fallback provider, error/timeout Gemini tiruan, redaksi data sensitif, request kosong/panjang, koordinat invalid dan output fasilitas dari DB. Bukti terstruktur: qa/browser-results.json, qa/accessibility-results.json, qa/print-results.json, qa/test-results.txt. `/`, `/health`, `/login`, `/register`, `/facilities`, `/assistant`, dashboard warga/admin berhasil dirender.

## Screenshot dan batas verifikasi

Screenshot tersedia di qa/: beranda, asisten, dashboard warga dan admin pada1440px/375px. Desktop memakai ruang putih, hierarki navy, sidebar admin dan tabel; mobile memakai drawer, susunan satu kolom serta tabel card. Peta/tiles OSM tetap membutuhkan jaringan; aplikasi menampilkan pesan error jika gagal.

- Tidak ada API key nyata dipakai; integrasi Gemini diuji melalui mock SDK, belum live terhadap akun/model pengguna.
- MySQL lokal pengguna/produksi tidak diakses. Verifikasi transaksi dilakukan pada SQLite; migration/schema dipertahankan.
- Audit otomatis tidak menggantikan audit aksesibilitas manual menyeluruh atau seluruh kombinasi browser/perangkat.
- Tidak ditambahkan penyusun draft pengaduan baru; pengaduan tetap ditulis, ditinjau dan dikirim sendiri melalui form yang sudah ada.
- Tidak ada deploy/publish, commit, atau perubahan langsung pada laptop. Diff teks tersimpan di qa/review.patch untuk review; aset font biner disertakan dalam arsip.
- Paket tidak menyertakan .env, virtual environment, cache, database runtime, node_modules, atau upload runtime selain .gitkeep. File dokumen lama dipertahankan.

## File dibuat

- `backend/app/services/assistant_safety.py`
- `frontend/static/fonts/ibm-plex-mono-0.woff2`
- `frontend/static/fonts/ibm-plex-mono-1.woff2`
- `frontend/static/fonts/ibmplexmono-OFL.txt`
- `frontend/static/fonts/plus-jakarta-sans-0.woff2`
- `frontend/static/fonts/plus-jakarta-sans-1.woff2`
- `frontend/static/fonts/plus-jakarta-sans-2.woff2`
- `frontend/static/fonts/plus-jakarta-sans-3.woff2`
- `frontend/static/fonts/plus-jakarta-sans-4.woff2`
- `frontend/static/fonts/plusjakartasans-OFL.txt`
- `qa/accessibility-results.json`
- `qa/admin-admin-dashboard-1440.png`
- `qa/admin-admin-dashboard-375.png`
- `qa/browser-results.json`
- `qa/citizen-citizen-dashboard-1440.png`
- `qa/citizen-citizen-dashboard-375.png`
- `qa/print-results.json`
- `qa/public--1440.png`
- `qa/public--375.png`
- `qa/public-assistant-1440.png`
- `qa/public-assistant-375.png`
- `qa/routes.txt`
- `requirements.txt`
- `scripts/check_accessibility.py`
- `scripts/check_browser.py`
- `scripts/preview.py`
- `scripts/sync_knowledge.py`
- `tests/test_redesign_ai.py`
- `tests/test_render_routes.py`
- `REDESIGN_REPORT.md`
- `qa/review.patch`
- `qa/test-results.txt`

## File diubah

- `.env.example`
- `.gitignore`
- `README.md`
- `backend/app/__init__.py`
- `backend/app/decorators.py`
- `backend/app/forms/auth.py`
- `backend/app/routes/admin.py`
- `backend/app/routes/assistant.py`
- `backend/app/routes/citizen.py`
- `backend/app/services/ai_service.py`
- `backend/app/services/assistant_knowledge.py`
- `backend/app/services/assistant_service.py`
- `backend/app/services/participant_service.py`
- `backend/config.py`
- `backend/requirements.txt`
- `backend/run.py`
- `design.md`
- `frontend/static/css/assistant.css`
- `frontend/static/css/main.css`
- `frontend/static/js/assistant.js`
- `frontend/static/js/facility-map.js`
- `frontend/static/js/main.js`
- `frontend/templates/admin/complaints/detail.html`
- `frontend/templates/admin/complaints/list.html`
- `frontend/templates/admin/contributions/detail.html`
- `frontend/templates/admin/contributions/list.html`
- `frontend/templates/admin/dashboard.html`
- `frontend/templates/admin/facilities/create.html`
- `frontend/templates/admin/facilities/edit.html`
- `frontend/templates/admin/facilities/list.html`
- `frontend/templates/admin/payments/list.html`
- `frontend/templates/admin/services/detail.html`
- `frontend/templates/admin/services/list.html`
- `frontend/templates/assistant/chat.html`
- `frontend/templates/auth/login.html`
- `frontend/templates/auth/register.html`
- `frontend/templates/base.html`
- `frontend/templates/citizen/card.html`
- `frontend/templates/citizen/complaints/create.html`
- `frontend/templates/citizen/complaints/detail.html`
- `frontend/templates/citizen/complaints/list.html`
- `frontend/templates/citizen/contributions/detail.html`
- `frontend/templates/citizen/contributions/list.html`
- `frontend/templates/citizen/contributions/pay.html`
- `frontend/templates/citizen/dashboard.html`
- `frontend/templates/citizen/family/add.html`
- `frontend/templates/citizen/family/detail.html`
- `frontend/templates/citizen/family/edit.html`
- `frontend/templates/citizen/family/list.html`
- `frontend/templates/citizen/payments/detail.html`
- `frontend/templates/citizen/payments/list.html`
- `frontend/templates/citizen/profile.html`
- `frontend/templates/citizen/services/detail.html`
- `frontend/templates/citizen/services/list.html`
- `frontend/templates/citizen/services/request.html`
- `frontend/templates/errors/400.html`
- `frontend/templates/errors/403.html`
- `frontend/templates/errors/404.html`
- `frontend/templates/errors/500.html`
- `frontend/templates/public/facilities/detail.html`
- `frontend/templates/public/facilities/list.html`
- `frontend/templates/public/home.html`
- `run.py`
- `tests/__init__.py`
- `tests/test_stage3.py`
- `tests/test_stage4.py`
- `tests/test_stage5.py`
- `tests/test_stage6.py`
- `tests/test_stage7.py`
- `tests/test_stage8.py`
- `tests/test_stage9.py`
