---
title: Studio Download - Project Memory Index
type: project-index
tags:
  - project/studio-download
  - memory/index
  - stack/python
  - stack/pyside6
date: 2026-09-20
status: active
aliases:
  - Studio Download Index
  - Knowledge Base
---

# Studio Download // Persistent Knowledge Base

Selamat datang di memori persisten **Studio Download** (Universal Media Downloader & NLE Asset Prep Engine). Vault ini dikelola secara mandiri menggunakan Obsidian Project Memory Schema untuk mempertahankan seluruh keputusan arsitektural, dokumentasi komponen, riwayat perbaikan bug, dan log sesi percakapan lintas waktu.

---

## 🗺️ Peta Navigasi Vault

### 1. [[01_Architecture|Arsitektur Sistem & Alur Data]]
Fondasi arsitektur aplikasi: PySide6 Desktop GUI, Dark Zinc Developer Theme, integrasi yt-dlp, TikWM HD API, IPC Bridge Localhost, dan arsitektur threading background.

### 2. Keputusan Arsitektural (ADR)
- [[ADR-001-PySide6-Migration|ADR-001: Migrasi Native Desktop ke PySide6 (Qt)]]
- [[ADR-002-Settings-MultiTab-Modal|ADR-002: Konsolidasi Menu Settings ke Dialog Multi-Tab Modular]]
- [[ADR-003-YouTube-DASH-Filesize-Estimation|ADR-003: Eliminasi Bug Manifest HLS & Akurasi Ukuran File YouTube]]
- [[ADR-004-Language-Unification-Indonesian|ADR-004: Standardisasi Bahasa Indonesia Murni & Real-Time Retranslation]]
- [[ADR-005-Browser-Extension-Cookie-Sync|ADR-005: Integrasi Ekstensi Browser & Sinkronisasi Cookies Otomatis]]
- [[ADR-006-User-Identity-Guest-Session-Admin-Dashboard|ADR-006: Identitas Pengguna Onboarding, Sesi Tamu, & Admin Dashboard]]
- [[ADR-007-Transcode-Aware-Filesize-Estimation|ADR-007: Perkiraan Ukuran Dinamis Berbasis Transkode & Eliminasi Karakter Titik]]
- [[ADR-008-UI-Stability-Logo-Persistence-and-Extension-Toast-Redesign|ADR-008: Stabilitas UI, Persistensi Logo, & Desain Ulang Toast Ekstensi]]
- [[ADR-009-YouTube-URL-Normalization-and-Installer-Permission-Hardening|ADR-009: Normalisasi URL YouTube & Perbaikan Izin Instalasi Windows]]
- [[ADR-010-Download-Pause-and-Resume-System|ADR-010: Sistem Kontrol Jeda (Pause) & Lanjutkan (Resume) Unduhan]]
- [[ADR-011-Multi-Clip-Time-Range-Downloader|ADR-011: Pemotong Rentang Waktu (Multi-Clip) & Download Segmen]]
- [[ADR-012-Visual-Scrubber-and-Batch-Playlist-Architecture|ADR-012: Batch Playlist Downloader, Prompt Video-in-Playlist, & Visual Scrubber]]

### 3. Komponen Utama
- [[MainWindow|Komponen 01: MainWindow & Telemetry Dashboard]]
- [[SettingsDialog|Komponen 02: SettingsDialog (Multi-Tab Modular)]]
- [[DownloaderEngine|Komponen 03: Downloader Engine (yt-dlp + FFmpeg)]]
- [[ParserEngine|Komponen 04: Parser Engine & Bitrate Estimator]]
- [[CompanionExtension|Komponen 05: Companion Browser Extension (Chrome/Edge)]]
- [[UserProfile|Komponen 06: UserProfile & WhoAreYou Dialogs (Client Space)]]
- [[PlaylistDialog|Komponen 07: PlaylistDialog & PlaylistPromptDialog (Batch Ingestion)]]

### 4. Pelacakan Tugas & Roadmap
- [[04_Tasks|Daftar Tugas, Milestone, dan Roadmap Fitur]]

### 5. Log Sesi Percakapan & Harian
- [[2026-09-19|Log Sesi 2026-09-19: Perbaikan UI/UX, Bug Kapsul Border, dan Kalkulasi Ukuran File]]
- [[2026-09-20|Log Sesi 2026-09-20: Pembentukan Memori Mandiri Obsidian]]
- [[2026-10-03|Log Sesi 2026-10-03: Normalisasi URL YouTube & Perbaikan Izin Instalasi Windows]]
- [[2026-10-11|Log Sesi 2026-10-11: Batch Playlist Downloader, Prompt Video-in-Playlist, & Handover Baru]]

---

## ⚡ Ringkasan Status Proyek Saat Ini
- **Engine**: PySide6 (Qt 6.8) Native Desktop GUI.
- **Backend Media**: `yt-dlp` (2026.8+) + FFmpeg 7.x portable.
- **Bahasa Utama**: Bahasa Indonesia (`id`) default pada `settings.json`.
- **Tema Visual**: JetBrains Mono dark zinc developer aesthetic (`#09090b` base, `#14151b` surface, `#27272a` border, `#38bdf8` cyan primary).
- **Integritas Cookies**: Sinkronisasi 1-klik via companion browser extension ke `cookies.txt` lokal.
