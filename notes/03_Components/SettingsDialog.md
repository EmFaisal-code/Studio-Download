---
title: Component SettingsDialog (Multi-Tab Modular)
type: component
tags:
  - project/studio-download
  - component/settings
  - stack/pyside6
date: 2026-09-20
status: active
aliases:
  - SettingsDialog
---

# Component: SettingsDialog (Multi-Tab Modular)

## File Sumber
- Path: `ui/dialogs/settings_dialog.py`

## Deskripsi
Dialog modal pengaturan terpadu dengan navigasi vertikal berbasis tab sidebar kiri dan panel konten multi-halaman di sebelah kanan.

## Halaman / Tab:
1. **`[01] PREF // Preferensi Umum`**:
   - Pilihan bahasa antarmuka (Bahasa Indonesia / English) dengan pembaruan dinamis (*real-time retranslation*).
   - Pilihan tema (Developer Zinc / Cyber Yellow).
   - Batas unduhan serentak (*Max concurrent downloads*).
   - Batas kecepatan download dalam KB/s (0 = tanpa batas).
2. **`[02] DIR // Direktori Unduhan`**:
   - Penentuan folder penyimpanan unduhan default.
   - Tombol `[PILIH FOLDER]` (file dialog native) dan `[BUKA DI EXPLORER]`.
3. **`[03] AUTH // Cookies YouTube`**:
   - Status cookies aktif dengan indikator visual: `● COOKIES_AKTIF (16 KB)`.
   - Tombol aksi: `[IMPOR COOKIES.TXT]` dan `[HAPUS]` (danger style crimson).
   - Kotak petunjuk terisolasi (`#authInfoBox`) bebas dari bug border kapsul elips, beraksen garis kiri indigo (`border-left: 3px solid #818cf8`).
4. **`[04] EXT // Ekstensi Browser`**:
   - Path folder ekstensi lokal dengan tombol `[BUKA FOLDER EKSTENSI]` dan `[SALIN PATH]`.
   - Panduan 3 langkah instalasi Unpacked Extension di Chrome/Edge (`chrome://extensions`).
   - Penjelasan fitur sinkronisasi cookies dan penangkapan stream m3u8.
5. **`[05] INFO // Rilis & Pembaruan`**:
   - Informasi build, runtime environment, dan tautan langsung ke repositori GitHub serta halaman rilis.
