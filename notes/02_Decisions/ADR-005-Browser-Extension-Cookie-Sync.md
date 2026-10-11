---
title: ADR-005 Browser Extension 1-Click Cookie & Stream Sync
type: adr
tags:
  - project/studio-download
  - adr/extension
  - auth/cookies
date: 2026-09-19
status: completed
aliases:
  - ADR-005
---

# ADR-005: Browser Extension 1-Click Cookie & Stream Sync

## Status
**Completed** (Diimplementasikan di `0.7.2_0/`, `backend/ipc_bridge.py`, & `backend/config.py`)

## Konteks
Pengguna menanyakan apakah fitur sinkronisasi cookies otomatis lewat ekstensi browser masih berfungsi setelah migrasi ke GUI PySide6 desktop.
Chrome di Windows versi terbaru menggunakan enkripsi DPAPI terikat aplikasi (*App-Bound Encryption*), sehingga library Python tidak dapat langsung membaca SQLite database cookie Chrome yang sedang terkunci.

## Keputusan
1. Mempertahankan companion browser extension Chromium Manifest V3 di folder `0.7.2_0/`.
2. Menjalankan HTTP IPC local bridge di port `19283` (`http://localhost:19283/sync-cookies` dan `/send-url`).
3. Ketika pengguna mengklik ikon ekstensi pada tab YouTube yang aktif:
   - Ekstensi membaca cookies YouTube melalui Chrome Extension API (`chrome.cookies.getAll({domain: ".youtube.com"})`).
   - Ekstensi memformat cookies ke format Netscape standard.
   - Mengirimkan payload via POST HTTP ke `http://localhost:19283/sync-cookies`.
   - Backend menyimpan payload ke `cookies.txt` di direktori data aplikasi.
4. Fungsi `get_ydl_cookie_opts()` di `backend/config.py` dikonfigurasi untuk memeriksa keberadaan `cookies.txt` di folder data aplikasi secara otomatis.

## Konsekuensi Positif
- Sinkronisasi cookies 1-klik tetap berjalan lancar tanpa terhambat enkripsi DPAPI Windows.
- Memungkinkan download video privat YouTube dan melewati pemeriksaan bot (*bot verification bypass*).
