---
title: ADR-002 Settings Multi-Tab Modular Consolidation
type: adr
tags:
  - project/studio-download
  - adr/settings
  - ui/ux
date: 2026-09-18
status: completed
aliases:
  - ADR-002
---

# ADR-002: Settings Multi-Tab Modular Consolidation

## Status
**Completed** (Diimplementasikan di `ui/dialogs/settings_dialog.py`)

## Konteks
Sebelumnya tombol Pengaturan, Direktori, Ekstensi, dan Info Rilis terpencar di navbar atas dan dialog terpisah. Pengguna meminta:
1. Menyatukan konfigurasi **Direktori**, **Ekstensi Browser**, **Cookies/Auth**, **Preferensi Bahasa/Tema**, dan **Rilis & Info** ke dalam satu jendela modal Pengaturan yang memiliki navigasi sidebar kiri berhalaman-halaman (*sidebar pages*).
2. Menghilangkan logo grafis di header yang tidak disukai pengguna.
3. Menghilangkan kotak border pada versi aplikasi di pojok kiri atas, cukup teks polos `v1.0`.

## Keputusan
1. Membuat dialog `SettingsDialog` (`QDialog`) dengan layout dua kolom:
   - **Sidebar Kiri**: `QButtonGroup` dengan tombol-tombol:
     - `[01] PREF // Preferensi Umum`
     - `[02] DIR // Direktori Unduhan`
     - `[03] AUTH // Cookies YouTube`
     - `[04] EXT // Ekstensi Browser`
     - `[05] INFO // Rilis & Pembaruan`
   - **Konten Kanan**: `QStackedWidget` dengan 5 halaman terisolasi.
2. Menghapus seluruh logo gambar/icon dari header dan menggantinya dengan typography JetBrains Mono minimalis.
3. Mengubah badge versi menjadi teks bersih `v1.0` tanpa border kotak.
4. Memperbaiki bug visual *cascading border* pada tab Auth dengan menggunakan scoped selector `QFrame#authInfoBox QLabel { background: transparent; border: none; }` dan aksen kiri indigo modern (`border-left: 3px solid #818cf8`).

## Konsekuensi Positif
- Akses pengaturan terpusat dan rapi.
- Desain antarmuka lebih bersih dan bebas elemen grafis yang mengganggu.
- Bebas dari bug garis elips/kapsul putus-putus pada instruksi autentikasi.
