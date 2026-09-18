# SehatWarga · Modern Civic Health

Identitas mandiri untuk prototipe akademik layanan kesehatan warga. Terpercaya,
tenang, mudah dipahami, dan profesional. Tidak meniru identitas BPJS/pemerintah.

## Sistem visual

Sumber token tunggal: `frontend/static/css/main.css`, blok `:root`.

| Peran | Warna |
| --- | --- |
| Primary / hover | #102F46 / #0A2235 |
| Accent / hover | #0C9B87 / #087969 |
| Secondary accents | #3275D8 / #E9675A / #E7A62B / #7359C9 |
| Background | #F4F8F8 |
| Surface / secondary | #FFFFFF / #EEF3F2 |
| Text / muted | #172B35 / #586C75 |
| Border | #DCE5E3 |
| Success / warning | #16845B / #B7791F |
| Danger / info | #C2414B / #2878B5 |

Muted diperkuat dari palet awal #60747D menjadi #586C75 agar teks kecil di surface secondary memenuhi kontras AA. Aksen teal terang untuk penanda visual; link kecil menggunakan #0B716A agar lebih
terbaca. Tombol utama navy dengan teks putih. Status memiliki label teks.

Plus Jakarta Sans 400–800 untuk antarmuka; IBM Plex Mono 400/600 hanya untuk kode,
nomor peserta, dan data teknis. WOFF2 disimpan lokal dengan `font-display: swap`;
fallback system-ui/ui-monospace. Lisensi OFL disertakan di folder fonts.

Spacing utama 4/8/12/16/24/32 px. Radius kartu 16 px, komponen 12 px, tombol 10 px.
Bayangan bertingkat secukupnya; focus ring 3 px. Gradient hanya dipakai untuk
membangun kedalaman pada hero, panel utama, dan tombol penting. Tidak menggunakan
glassmorphism berat, glow neon, atau ilustrasi generatif.

## Struktur informasi

- Publik: beranda berisi manfaat, akses layanan, alur penggunaan, dan direktori.
- Warga: ringkasan kepesertaan, tagihan penting, empat indikator utama, akses cepat,
  pengajuan terbaru, dan rincian sekunder yang dapat dibuka.
- Admin: sidebar desktop, empat antrean tindakan, statistik sekunder, daftar terbaru.
- Semua route tersedia pada drawer di bawah 1024 px; tombol Escape, overlay,
  scroll lock, fokus terperangkap, dan fokus kembali ke pemicu.
- Tabel menjadi daftar berlabel pada mobile. Kartu dan kuitansi tetap ramah cetak.
- Asisten: percakapan temporer, jawaban berbasis pengetahuan terverifikasi, kartu
  fasilitas terpisah dari ketersediaan peta, dan izin lokasi eksplisit.
- Tombol bantuan berada di area footer agar tidak menutup form/pagination.

## Komponen dan gerakan

`form-group`, `form-control`, `form-error`, `filter-bar`, `badge`, `empty-state`,
`timeline`, `summary-panel`, `secondary-details`, dan utilities tipografi/layout
bersifat reusable. Inline style Jinja yang bergantung state tidak diganti membabi buta.

Transisi cepat 160 ms dan normal 220 ms. Beranda memakai ilustrasi orbit layanan
3D berbasis CSS, tilt pointer terbatas, scroll reveal, radar peta, progress scroll,
dan micro-interaction kartu. Dashboard memakai depth dan kode warna kategori.
Seluruh gerak memakai transform/opacity, tidak menghalangi interaksi, dan
`prefers-reduced-motion` mematikannya. Validasi server, CSRF, escaping, dan
otorisasi tetap wajib.

## Batasan data

Tidak ada perubahan schema. Nilai tarif, status, metode pembayaran, dan transisi
mengacu pada konstanta service aktif; AI mengimpor konstanta tersebut.
Dokumentasi fakta bisnis diperbarui dengan `python scripts/sync_knowledge.py`.
