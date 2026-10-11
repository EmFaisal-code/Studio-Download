---
title: ADR-001 Native PySide6 Desktop GUI Migration
type: adr
tags:
  - project/studio-download
  - adr/gui
  - stack/pyside6
date: 2026-09-06
status: completed
aliases:
  - ADR-001
---

# ADR-001: Native PySide6 Desktop GUI Migration

## Status
**Completed** (Diimplementasikan di `main_qt.py` & `ui/`)

## Konteks
Sebelumnya aplikasi menggunakan web frontend (FastAPI + HTML/JS webview) yang memiliki keterbatasan interaksi dengan sistem file Windows, overhead browser runtime (Chromium/webview2), serta dependensi server port lokal yang rentan bentrok. Pengguna menginginkan antarmuka desktop modern, responsif, tanpa lag, dan bergaya JetBrains Mono developer dark IDE.

## Keputusan
1. Mengadopsi **PySide6 (Qt 6.x)** sebagai kerangka kerja antarmuka pengguna utama.
2. Membangun struktur modular:
   - `ui/main_window.py`: Jendela utama aplikasi.
   - `ui/dialogs/`: Modal dialog (`settings_dialog.py`, `history_dialog.py`).
   - `ui/components/`: Widget kartu format (`format_cards.py`), widget antrean tugas (`task_item.py`).
   - `ui/styles.py`: Seluruh token CSS/QSS terpusat tanpa hardcode sporadis.
3. Menjaga kompatibilitas dengan backend Python (`backend/parser.py`, `backend/downloader.py`).

## Konsekuensi Positif
- Waktu start instan (< 1 detik).
- Integrasi Windows shell native (pembukaan file di explorer via `os.startfile`, drag & drop, clipboard monitoring).
- Konsumsi memori RAM turun drastis dibanding Electron/webview.
- Tampilan Dark Zinc developer yang konsisten dan rapi.
