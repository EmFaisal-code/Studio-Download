---
title: Component Parser Engine & Format Matrix
type: component
tags:
  - project/studio-download
  - component/parser
  - backend/yt-dlp
date: 2026-09-20
status: active
aliases:
  - ParserEngine
---

# Component: Parser Engine & Format Matrix

## File Sumber
- Path: `backend/parser.py`

## Deskripsi
Modul pengekstraksi informasi dan format stream video/audio dari tautan web. Bertanggung jawab menentukan resolusi yang tersedia, kodek, FPS, dan perkiraan ukuran file akurat.

## Logika Kunci & Perbaikan Terbaru
1. **Penyaringan Manifest HLS YouTube**:
   - Mengabaikan format internal HLS (`m3u8_native` dan format seri `600`) pada YouTube yang kerap memiliki bitrate burst jaringan palsu (misal 37.000 kbps untuk 1440p atau 5.300 kbps untuk 144p).
2. **Prioritas Format Berdasarkan Ukuran Nyata CDN**:
   - Membandingkan stream berdasarkan `has_real_size` (ada nilai byte dari CDN Google).
   - Memprioritaskan non-AV1 (VP9/H.264), FPS lebih tinggi (60fps > 30fps), dan bitrate riil.
3. **Kalkulasi Ukuran Gabungan (Video + Audio)**:
   - `total_filesize = video_size + best_audio_size`.
   - Menghasilkan perkiraan presisi (misal `~ 3.97 GB` untuk video 1:14:50 yang aslinya memang berukuran ~4 GB saat diunduh).
4. **Preset Audio**:
   - Menyediakan 3 profil: MP3 320 kbps (Studio), MP3 192 kbps (Standard), dan M4A Original AAC (Lossless).
