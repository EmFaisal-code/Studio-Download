---
title: ADR-008 UI Stability, Logo Persistence, & Extension Toast Redesign
type: adr
tags:
  - project/studio-download
  - adr/ui
  - adr/extension
  - bugfix/stability
date: 2026-09-20
status: completed
aliases:
  - ADR-008
---

# ADR-008: UI Stability, Logo Persistence, & Extension Toast Redesign

## Status
**Completed** (Diimplementasikan di `main_qt.py`, `ui/main_window.py`, `ui/components/title_bar.py`, `ui/components/task_item.py`, `backend/downloader.py`, dan `extra/bg.js`)

## Konteks & Masalah
1. **Logo Software Sering Kosong ("Kadang Kosong Kadang Ada")**:
   - Ikon taskbar Windows dan jendela frameless sering kali menampilkan ikon dokumen default kosong (generic blank sheet).
   - Hal ini disebabkan oleh tidak adanya pemanggilan `self.setWindowIcon()` langsung pada instance `MainWindow`, ketiadaan pengiriman pesan native Win32 `WM_SETICON` ke `HWND`, dan ketiadaan logo aplikasi pada `CustomTitleBar`.
2. **Desain Notifikasi Ekstensi Terlihat "AI-Slop"**:
   - Toast notifikasi browser ekstensi sebelumnya menggunakan kotak kuning (`#facc15`), font standar Segoe UI, dan emoji petir oranye (`⚡`) yang terkesan murahan/kurang profesional. Pengguna meminta desain ulang agar selaras dengan tema gelap cyberpunk/developer Studio Download tanpa logo petir.
3. **List Antrean Unduhan Bergetar ("Geter-Geter") & Tombol Abort Sulit Ditekan**:
   - Saat proses unduhan berlangsung, item kartu di `ACTIVE_QUEUE` bergetar hebat. Pengguna bahkan kesulitan menekan tombol `[ABORT]`.
   - Penyebab utama:
     - `_refresh_buttons()` di `TaskItemWidget` dipanggil setiap kali ada pembaruan data (10–30 kali per detik). Akibatnya, tombol `[ABORT]` dihancurkan (`deleteLater()`) dan dibuat ulang terus-menerus. Klik pengguna terputus antara `mousePress` dan `mouseRelease`.
     - Ketiadaan *height lock* pada `TaskItemWidget` menyebabkan layout vertikal berosilasi naik-turun.
     - `ytdl_hook` pada `downloader.py` memancarkan event kemajuan pada setiap chunk kecil tanpa *rate throttling*.

## Keputusan & Solusi
1. **Persistensi Logo Software & Taskbar**:
   - Pada `main_qt.py`: Menambahkan `get_application_icon_path()` dan mengaitkan icon secara langsung ke `MainWindow`.
   - Mengirim pesan native Win32 `WM_SETICON` (baik `ICON_BIG` maupun `ICON_SMALL`) langsung ke `HWND` via `user32.SendMessageW`.
   - Menyematkan logo resmi 18x18 yang tajam langsung pada `CustomTitleBar` di samping judul teks "Studio Download".
   - Mengaitkan `setWindowIcon` pada seluruh dialog turunan (`SettingsDialog`, `HistoryDialog`, `UserProfileDialog`, `WhoAreYouDialog`).
2. **Desain Ulang Toast Notifikasi Ekstensi**:
   - Menghapus total emoji petir `⚡` dan emoji lainnya dari `extra/bg.js`.
   - Merombak total toast browser dengan gaya developer Studio Download:
     - Background `#0c0d12` dengan `backdrop-filter: blur(16px)` dan bayangan gelap lembut.
     - Border halus `#27272a` dengan aksen garis tepi kiri `3px solid #38bdf8`.
     - Header monospace `[STUDIO_DOWNLOAD] // INGEST_SENT` dan `SYS:200`.
     - Tipografi kontras tinggi yang rapi dan elegan.
3. **Eliminasi Total Getaran Antrean Unduhan & Stabilisasi Tombol Abort**:
   - **Gating Button Refresh**: Mengisolasi pemanggilan `_refresh_buttons()` di `TaskItemWidget` agar HANYA dieksekusi saat status unduhan benar-benar berubah (`if status != self._current_status`). Tombol `[ABORT]` tetap hidup secara stabil sepanjang proses unduhan, sehingga hover dan klik instan 100% responsif pada percobaan pertama.
   - **Dimension Lock & Layout Proportions**: 
     - Menghapus konflik double-padding (`padding: 0px` pada QSS `QFrame#taskCard`, menyerahkan padding seutuhnya ke `contentsMargins(16, 12, 16, 12)`).
     - Menetapkan tinggi presisi pada elemen vertikal: `lbl_badge` (tinggi 24px, lebar 185px), `progress_bar` (tinggi 6px), dan tombol aksi (tinggi 26px).
     - Mengunci tinggi kartu unduhan secara proporsional dan nyaman pada `self.setFixedHeight(118)`, serta menetapkan lebar minimum pada `lbl_stats` (230px) dan `lbl_eta` (90px). Dengan demikian kartu tidak gepeng/tertekan ("ngecil") dan layout tetap 100% bebas getaran.
   - **Downloader Progress Throttling**: Membatasi pemancaran progress pada `ytdl_hook` di `backend/downloader.py` menjadi maksimal ~12 kali per detik (interval >= 80ms) per tugas aktif, sembari tetap memancarkan event transisi status secara instan tanpa tunda.

## Hasil & Konsekuensi Positif
- Ikon aplikasi selalu muncul secara permanen di taskbar Windows, Alt+Tab, dan titlebar aplikasi tanpa pernah menjadi ikon kosong.
- Toast ekstensi Chrome tampil konsisten dengan tema desktop Studio Download, bebas dari emoji dan kesan AI-slop.
- Antrean unduhan berjalan hening dan stabil tanpa getaran (zero jitter). Tombol `[ABORT]` merespons dalam 1 klik tanpa jeda atau kegagalan klik.
- Kartu unduhan di `ACTIVE_QUEUE` tampil proporsional, lapang, dan estetis tanpa teks terhimpit atau tombol gepeng.
