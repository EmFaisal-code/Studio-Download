---
title: ADR-003 YouTube DASH Filesize Accuracy & HLS Manifest Filtering
type: adr
tags:
  - project/studio-download
  - adr/parser
  - bugfix/filesize
date: 2026-09-20
status: completed
aliases:
  - ADR-003
---

# ADR-003: YouTube DASH Filesize Accuracy & HLS Manifest Filtering

## Status
**Completed** (Diimplementasikan di `backend/parser.py` & `backend/downloader.py`)

## Konteks
Pada video YouTube panjang (seperti *Arknights - Endfield 1.1*, durasi 1:14:50), pengguna memilih resolusi 1440p yang di kartu format tertulis `~ 19.5 GB`. Namun ketika unduhan berjalan, total file sebenarnya hanya `3992.7 MB` (~4 GB). Resolusi 144p bahkan tertera `~ 2.9 GB`.

### Investigasi Mendalam (*Root Cause*)
1. YouTube menyajikan dua jenis stream:
   - **HTTPS DASH (Direct)**: Format video standar (misal `308`, `303`, `298`, dll.) yang memiliki informasi byte asli terverifikasi dari Google Video CDN (`filesize` riil). Format `308` 1440p berukuran asli `4.186.665.575` byte (~3.90 GB).
   - **HLS Manifest (`m3u8_native`)**: Format seri `600`–`625` tanpa informasi ukuran file (`filesize = None`), di mana field `tbr` mencatat *peak buffer burst rate* jaringan (format `623` memiliki `tbr = 37.269 kbps`, format `603` 144p memiliki `tbr = 5.327 kbps`).
2. Logika parser lama mengganti format DASH asli dengan format HLS karena menganggap nilai `tbr` HLS lebih besar. Karena ukuran byte kosong, parser mengalikan `tbr * duration` yang menghasilkan angka astronomis 19.5 GB untuk 1440p dan 2.9 GB untuk 144p!
3. Namun saat mengunduh, yt-dlp secara default memilih format HTTPS DASH asli (`308` + audio AAC `140`), yang total sebenarnya hanya 3.97 GB. Terjadi ketidaksesuaian drastis antara janji di kartu format dengan kenyataan unduhan.
4. Selain itu, progress logger di `backend/downloader.py` memaksakan pembagian dalam satuan MB (`total_downloaded / 1024 / 1024`), menghasilkan angka aneh `[46.8 MB / 3992.7 MB]`.

## Keputusan
1. **Penyaringan Manifest HLS YouTube**:
   - Menambahkan filter `if is_yt and (protocol.startswith("m3u8") or format_id_str.startswith("6")): continue` pada `backend/parser.py`.
2. **Prioritas Format Berukuran Server Riil**:
   - Format yang memiliki ukuran byte riil dari server (`has_real_size = True`) diprioritaskan di atas format tanpa ukuran pasti.
3. **Batas Ambang (*Sanity Clamp*) Bitrate**:
   - Jika ada stream yang tidak memiliki ukuran byte, `tbr` dibatasi secara wajar per resolusi (144p maks 350 kbps, 720p maks 6.000 kbps, 1080p maks 12.000 kbps, 1440p maks 25.000 kbps).
4. **Format Satuan Otomatis**:
   - Format GB kini menggunakan 2 desimal (misal `3.97 GB`).
   - Antrean unduh menggunakan `format_bytes(total_bytes)` sehingga menampilkan `[46.8 MB / 3.97 GB]`, serasi 100% dengan kartu format `~ 3.97 GB`.

## Konsekuensi Positif
- Kartu format 1440p menampilkan `~ 3.97 GB`, kartu 144p menampilkan `~ 148.9 MB`.
- Angka di kartu format dan antrean unduhan kini sinkron dan akurat.
