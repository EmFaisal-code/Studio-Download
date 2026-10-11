---
title: Component Companion Browser Extension
type: component
tags:
  - project/studio-download
  - component/extension
  - browser/chrome
date: 2026-09-20
status: active
aliases:
  - CompanionExtension
---

# Component: Companion Browser Extension

## File Sumber
- Path: `0.7.2_0/` (Manifest V3 Chrome Extension)

## Deskripsi
Ekstensi pendamping browser untuk Chromium (Google Chrome, Microsoft Edge, Brave, Opera) yang menyediakan integrasi 1-klik untuk:
1. Sinkronisasi session cookies YouTube ke aplikasi Studio Download.
2. Penangkapan stream m3u8/HLS saat browsing video di web.

## File & Alur Kerja
- `manifest.json`: Konfigurasi Manifest V3 dengan permission `cookies`, `webRequest`, `activeTab`, dan `storage`.
- `background.js`: Mendengarkan klik toolbar pada tab YouTube, mengekstrak cookies domain `.youtube.com`, dan mengirimkan POST HTTP ke `http://localhost:19283/sync-cookies`.
- `popup.html` & `popup.js`: Antarmuka popup cepat untuk memicu sinkronisasi manual atau memasukkan URL stream.

## Cara Instalasi
1. Buka `chrome://extensions` di browser.
2. Aktifkan **Developer mode** di sudut kanan atas.
3. Klik **Load unpacked** dan pilih folder `0.7.2_0` di dalam direktori aplikasi Studio Download.
