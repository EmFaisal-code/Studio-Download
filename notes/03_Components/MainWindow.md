---
title: Component MainWindow & Telemetry Dashboard
type: component
tags:
  - project/studio-download
  - component/ui
  - stack/pyside6
date: 2026-09-20
status: active
aliases:
  - MainWindow
---

# Component: MainWindow & Telemetry Dashboard

## File Sumber
- Path: `ui/main_window.py`
- Stylesheet: `ui/styles.py`

## Deskripsi
Jendela utama aplikasi desktop Studio Download yang menyajikan alur kerja penarikan media dari URL hingga pemantauan progres unduhan.

## Struktur Elemen Utama
1. **Title Bar & System Telemetry**:
   - Menampilkan judul aplikasi, versi bersih `v1.0`, indikator status `[SYS:READY_200|ENGINE:PYSIDE6]`.
   - Tombol cepat akses riwayat `[LOG] Riwayat` dan pengaturan `[CONFIG] Pengaturan`.
2. **Hero Input Section**:
   - Input line edit URL (`>_ URI:`) dengan tombol `[TEMPEL]` otomatis dari clipboard dan tombol eksekusi `ANALISIS_VIDEO()`.
   - Panel toggle Header/Referer opsional untuk streaming yang dilindungi token atau 403 Forbidden.
3. **Manifest & Format Selection Area**:
   - Pratinjau thumbnail beresolusi tinggi dengan fallback berantai (*cache local, hqdefault, webp*).
   - Metadata video: Judul yang dapat diedit langsung, Kreator, Durasi, Jumlah Tayangan.
   - Tab switcher: `VIDEO + AUDIO` vs `HANYA AUDIO`.
   - Grid kartu format (`FormatCardWidget`) yang menampilkan nomor indeks (`#01`), resolusi, FPS, codec, dan perkiraan ukuran akurat.
   - Pilihan format kontainer (MP4 / MKV) dan transkode (H.264 NLE, ProRes 422, AV1/Sumber Asli).
4. **Active Queue Ledger (`storage_ledger.log`)**:
   - Daftar tugas unduhan aktif (`TaskItemWidget`) dengan progress bar, status badge pengemasan FFmpeg, telemetri kecepatan (MB/s), sisa waktu (ETA), dan format ukuran ganda (`[46.8 MB / 3.97 GB]`).
   - Tombol kontrol per tugas: `[BATALKAN]`, `[PUTAR]`, `[FOLDER]`, `[HAPUS]`, `[COBA LAGI]`.
