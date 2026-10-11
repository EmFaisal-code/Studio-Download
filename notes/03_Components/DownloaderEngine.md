---
title: Component Downloader Engine
type: component
tags:
  - project/studio-download
  - component/downloader
  - backend/yt-dlp
date: 2026-09-20
status: active
aliases:
  - DownloaderEngine
---

# Component: Downloader Engine

## File Sumber
- Path: `backend/downloader.py`

## Deskripsi
Mesin orkestrasi unduhan yang mengelola antrean tugas (*task queue*), isolasi thread, eksekusi `yt-dlp`, pengemasan/transcoding FFmpeg, dan pelaporan progres real-time.

## Fitur & Alur Kerja Utama
1. **Thread Worker Terisolasi**: Setiap unduhan dieksekusi dalam folder temporary terisolasi `.studio_temp_<task_id>` untuk mencegah penguncian file Windows (*file locking*) saat proses muxing atau pembatalan.
2. **Pembatalan Aman (*Clean Cancellation*)**: Memanfaatkan `threading.Event` terdedikasi per tugas (`cancel_events[task_id]`) yang diperiksa pada `ytdl_hook` dan `postprocessor_hook`.
3. **Format Selection String**:
   - Menghindari AV1 jika memilih preferensi kompatibel, memprioritaskan stream video resolusi target dengan audio AAC (`[ext=m4a]`) terbaik.
   - Menggabungkan kontainer ke MP4 atau MKV sesuai pilihan pengguna.
4. **Telemetri Progress Hook**:
   - Menghitung persentase kumulatif video + audio (`min(pct, 98.0)`).
   - Menggunakan `format_bytes()` dinamis: menampilkan ukuran MB jika $<$ 1 GB, dan GB (2 desimal) jika $\ge$ 1 GB (misal `[46.8 MB / 3.97 GB]`).
5. **Penanganan Khusus TikTok**:
   - Jalur cepat tanpa watermark via TikWM API dengan ekstraksi file asli uncompressed.
