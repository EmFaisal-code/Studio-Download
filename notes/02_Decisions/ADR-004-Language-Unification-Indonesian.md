---
title: ADR-004 Language Unification to Pure Indonesian
type: adr
tags:
  - project/studio-download
  - adr/i18n
  - ui/ux
date: 2026-09-19
status: completed
aliases:
  - ADR-004
---

# ADR-004: Language Unification to Pure Indonesian

## Status
**Completed** (Diimplementasikan di `backend/i18n.py` & `settings.json`)

## Konteks
Sebelumnya terdapat teks antarmuka yang bercampur antara Bahasa Inggris dan Bahasa Indonesia, atau menggunakan garis miring dwibahasa seperti `UNDUH / DOWNLOAD` atau label `COOKIE_ACTIVE`. Pengguna meminta penyesuaian bahasa agar bersih dan tidak tercampur.

## Keputusan
1. Menetapkan nilai default pada `settings.json` menjadi `"language": "id"`.
2. Menghilangkan label dwibahasa dan menggantinya dengan istilah Bahasa Indonesia yang rapi:
   - `[IMPOR COOKIES.TXT]`, `[HAPUS]`.
   - `● COOKIES_AKTIF (16 KB)`.
   - `// PETUNJUK_AUTENTIKASI:`.
   - `[SINKRONISASI_OTOMATIS]: Buka tab YouTube...`.
   - `[TUTUP]`, `[SIMPAN PENGATURAN]`.
3. Mengimplementasikan metode `retranslate_ui()` pada dialog pengaturan yang terhubung ke sinyal `currentIndexChanged` dropdown bahasa, memungkinkan pergantian bahasa langsung (*live*) tanpa perlu restart aplikasi.

## Konsekuensi Positif
- Tampilan antarmuka profesional, konsisten, dan mudah dipahami pengguna berbahasa Indonesia.
- Fleksibilitas tetap terjaga bagi pengguna yang ingin beralih ke Bahasa Inggris melalui dropdown pengaturan.
