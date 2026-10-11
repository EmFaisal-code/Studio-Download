---
title: ADR-007 Transcode-Aware Filesize Estimation & Dot Bullet Elimination
type: adr
tags:
  - project/studio-download
  - adr/parser
  - adr/ui
  - bugfix/filesize
date: 2026-09-20
status: completed
aliases:
  - ADR-007
---

# ADR-007: Transcode-Aware Filesize Estimation & Dot Bullet Elimination

## Status
**Completed** (Diimplementasikan di `backend/parser.py`, `backend/downloader.py`, `ui/main_window.py`, `ui/components/format_cards.py`, `ui/components/task_item.py`, dan `ui/dialogs/settings_dialog.py`)

## Konteks & Masalah
1. **Perkiraan Ukuran Terpatok pada H.264**:
   - Sebelumnya, parser (`backend/parser.py`) menyaring seluruh stream resolusi ke dalam satu entri tunggal yang mengutamakan H.264 (karena bitrate `tbr` H.264 lebih tinggi dari VP9 dan AV1 pada stream DASH).
   - Akibatnya, kartu format selalu menampilkan ukuran statis H.264 (misal 1080p ~540.8 MB).
   - Ketika pengguna mengganti opsi transkode pada dropdown `TRANSCODE` (misalnya memilih `AV1 / Sumber Asli` atau `ProRes 422`), kartu format sama sekali tidak merespons perubahan tersebut.
   - Saat pengguna mengunduh dalam mode AV1/Original, ukuran file unduhan asli adalah **602.4 MB** (untuk 1440p) atau **279.1 MB** (untuk 1080p), sementara kartu format dan antrean awal terkunci pada angka H.264/VP9 (~1.05 GB atau ~540 MB).
   - Selain itu, `downloader.py` mengabaikan `format_id` spesifik untuk YouTube (`if not is_yt`), sehingga yt-dlp memilih stream default yang berbeda dari pilihan pengguna.
2. **Penggunaan Karakter Titik/Bullet (`●` dan `•`) pada Antarmuka**:
   - Pengguna meminta agar seluruh indikator titik bullet seperti `● COOKIE_ACTIVE`, `● COOKIES_SYNCED`, titik hijau di title bar, dan pemisah `•` dihilangkan karena mengganggu kerapian estetika antarmuka terminal.

## Keputusan & Solusi
1. **Multi-Codec Parsing di `backend/parser.py`**:
   - Untuk setiap resolusi, parser mengelompokkan stream ke dalam kamus `codecs`:
     - `"compatible"`: Memilih stream asli H.264 (`avc1`) jika tersedia, atau kalkulasi transkode H.264 jika resolusi >1080p (seperti 1440p).
      - `"original"`: Memilih stream AV1 (`av01`) hemat bandwidth jika tersedia, atau VP9/Source asli.
      - `"prores"`: Menggunakan ukuran unduhan stream sumber berkualitas tertinggi (`prores_src_stream["total_filesize"]`), selaras 100% dengan kuota/antrean unduhan riil yt-dlp (~1.05 GB untuk 1440p, ~415 MB untuk 1080p, bukan perkiraan teoritis kamera uncompressed 57 GB).
2. **Pembaruan Dinamis Kartu Format di `ui/main_window.py`**:
   - Menghubungkan event `self.combo_codec.currentIndexChanged` ke `_on_codec_changed()`.
   - Mengganti pilihan transkode langsung memperbarui badge codec dan perkiraan ukuran file di seluruh kartu format secara real-time tanpa parsing ulang.
3. **Presisi Downloader di `backend/downloader.py`**:
   - Menggunakan `format_id` spesifik dari kartu format yang terpilih pada `ydl_opts['format']`.
   - Menambahkan transcoding otomatis standar Apple ProRes 422 menggunakan FFmpeg (`-c:v prores_ks -profile:v 2 -vendor apl0 -c:a pcm_s16le`) saat profil ProRes dipilih.
4. **Pembersihan Total Karakter Titik (`●` dan `•`)**:
   - Mengganti `● COOKIE_ACTIVE` menjadi badge `[ COOKIE_ACTIVE (size KB) ]`.
   - Menghapus titik hijau pada Title Bar.
   - Mengganti pemisah `•` pada Format Card, Task Item, History Dialog, dan i18n tip menjadi pipa `|` atau spasi terstruktur.

## Hasil & Konsekuensi Positif
- Memilih `AV1 / Sumber Asli` pada video 1440p langsung mengubah perkiraan kartu menjadi `~ 602.7 MB [AV1]`, selaras 100% dengan ukuran unduhan akhir 602.4 MB.
- Memilih `H.264 (Kompatibel NLE)` menampilkan `~ 540.8 MB [H.264]`.
- Memilih `ProRes 422 (Master Edit)` menampilkan `~ 1.05 GB [ProRes 422]`, selaras presisi dengan antrean unduhan riil (1.03 GB) sebelum di-transcode ke `.mov`.
- Seluruh antarmuka bersih dari karakter titik bullet sesuai preferensi visual pengguna.
