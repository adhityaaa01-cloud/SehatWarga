# Audit performa SehatWarga — 23 September 2026

## Baseline dan cakupan

Baseline sebelum optimasi: commit `7f4e87b`. Saat pekerjaan dilanjutkan sudah ada perubahan belum di-commit pada 11 PNG, `main.js`, `assistant.js`, `base.html`, dan `home.html`. Perubahan tersebut ikut diaudit; snapshot awal kelanjutan disimpan di `/tmp/sehatwarga-perf-start/frontend` dan baseline commit di `/tmp/sehatwarga-perf-head/frontend`.

Audit mencakup kedua stylesheet, seluruh JavaScript frontend, dan seluruh template beserta pemuatan gambar, font, CSS, script lokal, serta Leaflet. Backend, route, database aplikasi, autentikasi, AI, isi halaman, dan business logic tidak diubah. Semua pengujian aplikasi memakai SQLite sementara melalui `scripts/preview.py` / `tests.create_test_app`; tidak membaca `.env` dan tidak memakai database produksi.

Sumber beban yang ditemukan:

- Pointer tilt dan magnetic sebelumnya membaca geometri dan menulis style pada setiap event. Ambient pointer memiliki scheduler tersendiri.
- Canvas membaca ukuran pada setiap frame dan menghitung jarak semua pasangan partikel; callback pause/resume perlu menangani tab tersembunyi tanpa loop ganda.
- Animasi CSS berulang tetap aktif untuk section di luar viewport.
- Tidak ada pengaman terhadap inisialisasi frontend/chat/peta berulang.
- Total 11 PNG sebelum kompresi: 6.502.870 byte. Tidak ada perubahan dimensi atau penggantian aset.
- `main.css` sekitar 127 KB, `assistant.css` sekitar 16,6 KB. Banyak selector berulang merupakan override dengan cascade yang disengaja, sehingga tidak aman dihapus hanya karena nama selector sama.
- Font lokal Instrument Sans sudah memakai `font-display: swap`; preload latin utama sudah benar. Tidak ditemukan pemuatan CSS/JS ganda dalam template.

## Perubahan final

| File | Perubahan |
| --- | --- |
| `frontend/static/js/main.js` | Guard inisialisasi; scheduler pointer/scroll/resize berbasis rAF dengan pembacaan geometri yang dicache per frame; membatalkan update tilt tertunda saat pointerleave; cache ukuran canvas; menolak pasangan partikel yang pasti di luar jarak sebelum menghitung `hypot`; pause/resume canvas dan animasi CSS infinite berdasarkan viewport/visibility. |
| `frontend/static/js/assistant.js` | Guard inisialisasi chat. Timeout, request, geolocation, rendering respons, dan pembersihan map saat pesan dibuang tetap menggunakan alur yang ada. |
| `frontend/static/js/facility-map.js` | Memastikan container ada/terhubung dan initializer hanya berjalan sekali per container, sehingga map, marker, dan listener lokasi tidak digandakan. |
| `frontend/templates/base.html` | Dimensi intrinsik tiga logo dan `defer` untuk `main.js`. |
| `frontend/templates/public/home.html` | Dimensi intrinsik logo hero dan empat gambar layanan; `loading="lazy" decoding="async"` hanya untuk tiga ikon bagian informasi. Logo/hero/gambar layanan tetap eager. |
| `frontend/static/css/main.css` | `height: auto` pada logo hero mempertahankan rasio alami saat atribut dimensi intrinsik ditambahkan. Tidak mengubah keyframes atau nilai visual animasi. |
| `frontend/templates/assistant/chat.html` | `defer` pada script chat lokal. |
| `frontend/templates/public/facilities/{list,detail}.html` | `defer` pada script peta lokal; Leaflet tetap dimuat lebih dahulu dan initializer tetap dijalankan melalui DOMContentLoaded. |
| 11 PNG di `frontend/static/images/` | Kompresi lossless yang sudah dimulai sebelumnya diverifikasi piksel-per-piksel. |
| `scripts/check_performance.py` | Regression check runtime untuk event per frame, duplikasi init, pause/resume, Leaflet, dan chat. |
| `scripts/check_performance_visual.py` | Fixture pembandingan geometri, timing animasi, jumlah dekorasi, dan screenshot pada fase animasi yang sama. |

`assistant.css` tidak diubah. Tidak menambahkan library, `contain`, atau `content-visibility`; tidak menghapus selector maupun dekorasi. `will-change` yang berkaitan dengan transform/efek 3D tetap dipertahankan untuk menghindari perubahan compositing. Tidak mengubah jumlah partikel, rumus geraknya, radius, warna, opacity, koneksi, durasi, delay, easing, atau keyframes. Pause hanya berlaku pada loop dan animasi berulang di luar viewport atau tab tersembunyi; animasi entrance finite tetap berjalan seperti sebelumnya.

## Hasil pengujian

- Test proyek: **156/157 lulus**. Satu kegagalan lama: `test_16_academic_disclaimer_present_across_pages` mencari frasa lama `kebutuhan akademik` / `prototype`, sedangkan halaman memakai `Prototipe akademik independen`. Kegagalan yang sama direproduksi pada template baseline. Isi halaman dan test tidak diubah untuk menyembunyikan kegagalan ini.
- Browser QA proyek: **321/321 lulus**, mencakup publik/warga/admin, lebar 320, 375, 480, 768, 1024, 1440, drawer/focus/keyboard, render, overflow, dan chat fallback.
- Regression performa: **22/22 lulus**; tidak ada exception JavaScript maupun console error pada run ini. Burst 100 pointer events menghasilkan satu flush rAF dan dua pembacaan bounds (kartu dan hero induknya, masing-masing sekali). Canvas berhenti di luar viewport dan kembali aktif saat terlihat. Pengujian visibility tersembunyi memakai simulasi properti `document.hidden` dan event `visibilitychange`.
- Inisialisasi ulang tidak menambah listener, canvas, dekorasi, atau instance peta. Satu submit chat menghasilkan satu request. Leaflet eksternal berhasil dimuat dalam pengujian. Klik marker membuka popup, geolocation uji memperbarui feedback, dan halaman detail menampilkan satu peta/popup dengan initializer idempotent.
- `node --check` pada ketiga file JS, `compileall` Python untuk backend/scripts/tests/run.py, dan `git diff --check`: lulus.
- Semua PNG memiliki **RGBA, dimensi, dan metadata identik** dengan baseline. Ukuran final 6.231.836 byte, berkurang **271.034 byte (4,17%)**. Rincian ada di `assets.json`.

Tidak mengklaim persentase penurunan CPU, skor Lighthouse, atau percepatan jaringan yang belum diukur. Bukti pengurangan kerja adalah coalescing event, cache geometri, serta berhentinya callback canvas dan animasi berulang pada kondisi tidak terlihat.

## Pembandingan visual

Pada lebar **375 dan 1440 px**, fixture fase animasi tetap membandingkan **236 elemen per viewport**: geometri, transform, opacity, dan filter sama; jumlah dekorasi dan metadata animasi (nama, durasi, delay, easing, iterasi) juga sama. Rincian tersimpan di `visual-results.json`.

Screenshot halaman publik (beranda, login, register, asisten, fasilitas) dibandingkan pada kedua ukuran tersebut. Beranda desktop/mobile dan asisten identik pada run reduced-motion terakhir; sebagian screenshot lain memiliki variasi rasterisasi tepi tombol sebesar 1–2 tingkat kanal warna. Screenshot fase animasi tetap memiliki selisih maksimum 3/255 (mobile) dan 1/255 (desktop), dengan geometri serta nilai visual yang identik. Pengambilan screenshot berulang dari baseline sendiri juga menghasilkan variasi rasterisasi kecil. Tile peta eksternal dapat berbeda antar-pengambilan; marker/popup/geolocation diperiksa secara fungsional.

Karena itu, **identitas byte/piksel setiap screenshot dinamis tidak diklaim**. Tidak ditemukan perubahan layout, tipografi, jumlah elemen, atau parameter animasi dalam cakupan yang diuji. Tidak ada optimasi pengurangan efek atau perubahan desain yang dipertahankan. Screenshot baseline/final fase tetap tersedia sementara di `/tmp/sehatwarga-visual-verified-head` dan `/tmp/sehatwarga-visual-verified-final`; hasil geometri lengkap ada di `results.json` masing-masing direktori. Pengujian lintas browser selain Chromium belum dilakukan.

## Mengulang pemeriksaan

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_browser.py
.venv/bin/python scripts/check_performance.py
.venv/bin/python scripts/check_performance_visual.py /tmp/sehatwarga-perf-head/frontend /tmp/sehatwarga-visual-baseline
.venv/bin/python scripts/check_performance_visual.py frontend /tmp/sehatwarga-visual-current
node --check frontend/static/js/main.js
node --check frontend/static/js/assistant.js
node --check frontend/static/js/facility-map.js
.venv/bin/python -m compileall -q backend scripts tests run.py
```

Chromium/Playwright sudah tersedia di lingkungan ini. Browser memerlukan izin eksekusi di luar sandbox. Fixture visual hanya membekukan timeline/transisi/observer/event pointer pada browser pengujian; tidak mengubah animasi aplikasi. Screenshot gerak tidak dipakai untuk menilai frame rate.

Belum ada commit.
