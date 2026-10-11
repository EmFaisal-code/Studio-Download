---
title: Tasks & Development Roadmap
type: task
tags:
  - project/studio-download
  - tasks/roadmap
date: 2026-09-20
status: active
aliases:
  - Tasks
  - Roadmap
---

# Studio Download // Tasks & Roadmap

## 🏁 Milestone yang Telah Diselesaikan
- [x] **Migrasi Native Desktop**: Beralih dari webview ke GUI native PySide6 (Qt) dengan tema JetBrains Mono dark zinc.
- [x] **Konsolidasi Multi-Tab Settings**: Menggabungkan pengaturan direktori, ekstensi, cookies/auth, dan rilis ke dalam `SettingsDialog` dengan sidebar vertikal.
- [x] **Pembersihan Branding Header**: Menghilangkan logo grafis di header atas dan mengubah badge versi menjadi teks bersih `v1.0`.
- [x] **Perbaikan Bug Border Kapsul**: Menghilangkan bug cascading border elips/putus-putus pada petunjuk autentikasi di tab Auth Cookies menggunakan ID selector terisolasi `#authInfoBox`.
- [x] **Standardisasi Bahasa Indonesia**: Mengonfigurasi default `settings.json` ke `"id"`, merapikan label dwibahasa ke bahasa Indonesia murni, dan menambahkan *live retranslation*.
- [x] **Perbaikan Akurasi Perkiraan Ukuran File**:
  - Menyaring manifest internal HLS (`m3u8`) YouTube ber-bitrate palsu.
  - Memprioritaskan ukuran server riil (*CDN Content-Length*).
  - Mengatasi diskrepansi 19.5 GB vs 4 GB pada resolusi 1440p serta 2.9 GB pada 144p.
- [x] **Sinkronisasi Satuan Progres**: Mengubah satuan antrean aktif menjadi dinamis (`MB` jika $<$ 1 GB, dan `GB` jika $\ge$ 1 GB) agar selaras dengan kartu format.
- [x] **Identitas Pengguna & Admin Dashboard**: Dialog onboarding "Who Are You", opsi masuk sebagai Tamu (Guest Session), registrasi database `users.json` & Supabase, badge profil di Title Bar, serta dialog Admin Dashboard lengkap.
- [x] **Perkiraan Ukuran Dinamis Berbasis Transkode & Eliminasi Titik Bullet**: Menghilangkan ketergantungan perkiraan ukuran hanya pada H.264, menghubungkan dropdown Transkode ke pembaruan dinamis kartu format secara real-time (H.264, AV1, ProRes 422), memastikan yt-dlp mengunduh format yang tepat, dan menghapus seluruh karakter titik (`●` dan `•`) dari antarmuka.
- [x] **Windows Installer (.exe) & Default Bahasa Inggris**: Mengonfigurasi default bahasa aplikasi ke English ("en") secara menyeluruh, membundel dependensi native PySide6, FFmpeg, dan ekstensi pendamping, serta mengompilasi installer mandiri Windows (.exe) via Inno Setup 6 tanpa melakukan git push.
- [x] **Normalisasi URL YouTube & Perbaikan Izin Instalasi Windows**:
  - Menyelesaikan masalah perbedaan link video dalam playlist (`&list=...&index=...`) vs link biasa dengan normalisasi URL kanonikal dan opsi `noplaylist: True` sehingga metadata (thumbnail, 4K/1440p/1080p, durasi, views) tampil konsisten dan identik.
  - Memperbaiki bug dialog onboarding yang membeku setelah instalasi Windows dengan memindahkan berkas konfigurasi *writeable* ke `%APPDATA%\StudioDownload` dan membungkus aksi tombol dialog dalam `try...finally` serta penanganan tombol Escape.
- [x] **Sistem Kontrol Jeda (Pause) & Lanjutkan (Resume) Unduhan**:
  - Menyediakan kontrol tombol `[JEDA]` / `[PAUSE]` dan `[LANJUTKAN]` / `[RESUME]` pada antarmuka kartu unduhan aktif (PySide6 & Web GUI).
  - Mekanisme jeda *thread-safe* berbasis `threading.Event` terintegrasi pada hook yt-dlp, direct HTTP stream loop TikTok, dan segmen HLS fallback.
  - Pelacakan `active_threads` untuk mencegah duplikasi thread saat resume serta mempertahankan slot batas antrean bersamaan.
  - Pembatalan bersih (`[BATALKAN]` / `[ABORT]`) seketika saat berstatus dijeda tanpa menyebabkan thread *freeze* / kebocoran memori.
- [x] **Pemotong Rentang Waktu (Multi-Clip) & Download Segmen**:
  - Menghadirkan panel Multi-Clip Slicer untuk memotong satu atau beberapa rentang durasi video (`MM:SS` atau `HH:MM:SS`).
  - Efisiensi bandwidth tinggi melalui `download_ranges` yt-dlp yang hanya mengunduh potongan pecahan fragmen CDN relevan (tanpa mengunduh seluruh file video).
  - Menghasilkan file video terpisah per klip dengan penamaan tag rentang waktu otomatis (`[01.00-02.30]`).
  - Pemotongan presisi didukung pada YouTube, TikTok, dan stream HLS fallback.

- [x] **Batch / Playlist Downloader**:
  - Deteksi otomatis link playlist YouTube & media collections.
  - Ekstraksi metadata instan (~2 detik) menggunakan `extract_flat: 'in_playlist'`.
  - Modal dialog khusus `PlaylistDialog` dengan filter pencarian real-time, checklist pilihan cepat (Pilih Semua / Batal Pilih), dan preset resolusi/format global.
  - Antrean unduhan batch otomatis masuk ke antrean unduhan bertahap sesuai batas `max_concurrent_downloads`.
- [x] **Pembedaan Cerdas Video di Playlist vs Pure Playlist**:
  - Menyelesaikan masalah saat menyalin tautan video YouTube yang sedang diputar di dalam antrean playlist (`watch?v=...&list=...&index=...`).
  - Menghadirkan dialog prompt Cyberpunk `PlaylistPromptDialog` yang menanyakan apakah pengguna ingin mengunduh **Hanya Video Ini** (fokus default) atau **Seluruh Playlist**.
  - Opsi "Unduh Hanya Video Ini" secara otomatis menormalisasi URL menjadi link video tunggal murni dan menampilkan matriks format 4K/1080p, transkode, dan pemotong klip biasa.
  - Opsi "Unduh Seluruh Playlist" menandai video aktif dengan badge cyan `[VIDEO INI]` dan menyediakan tombol `[Hanya Video Ini]` di toolbar `PlaylistDialog`.
- [x] **Pembersihan Fitur Clipboard Auto-Detect**:
  - Menghapus pemantauan clipboard otomatis latar belakang per permintaan pengguna guna menjaga kebersihan antarmuka dan efisiensi memori. Tombol manual `[PASTE]` tetap dipertahankan.

## 📌 Rencana & Tugas Mendatang (Backlog)
- [ ] **Visual Scrubber / Dual-Handle Range Slider untuk Klip**: Kontrol slider visual dengan thumbnail scrubbing untuk memotong segmen klip secara intuitif (Arsip perencanaan di `notes/02_Decisions/ADR-012-Visual-Scrubber-and-Batch-Playlist-Architecture.md`).
- [ ] **Subtitle / CC Downloader**: Pilihan mengunduh subtitle otomatis (`.srt` / `.vtt`) terpisah atau di-embed ke dalam file MKV.
- [ ] **Bandwidth Graph Visualizer**: Grafik kecepatan unduhan real-time mini di bagian telemetri bawah.
