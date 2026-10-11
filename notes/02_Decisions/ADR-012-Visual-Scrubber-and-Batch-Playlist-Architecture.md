---
title: ADR-012 Visual Scrubber, Batch Playlist Downloader & Smart Detection
type: adr
tags:
  - project/studio-download
  - adr/architecture
  - feature/playlist
  - feature/visual-scrubber
date: 2026-10-11
status: accepted
aliases:
  - ADR-012
---

# ADR-012 // Visual Scrubber, Batch Playlist Downloader & Intelligent URL Parsing

## 1. Konteks & Latar Belakang
Studio Download v1.0 telah berhasil menghadirkan pemotongan klip (*Time Range Slicing*), transkode dinamis (H.264, AV1, ProRes 422), dan sistem *pause/resume*. Untuk mempercepat workflow kreator konten, dilakukan eksplorasi fitur:
1. **Batch / Playlist Downloader** (Diimplementasikan): Pengunduhan massal daftar putar YouTube dan media collections dengan filter pencarian, preset kualitas global, dan antrean bertahap.
2. **Pembedaan Cerdas Video di Playlist vs Pure Playlist** (Diimplementasikan): Menangani tautan YouTube dari antrean pemutar (`watch?v=...&list=...&index=...`) agar tidak langsung memaksa unduhan seluruh playlist, melainkan menawarkan pilihan instan antara mengunduh hanya video aktif atau seluruh playlist.
3. **Smart Clipboard Auto-Detect** (Dihapus/Dibatalkan per Permintaan Pengguna): Fitur deteksi clipboard otomatis sempat diuji, namun diputuskan untuk dihapus sepenuhnya karena dinilai kurang berguna dan dapat mengganggu aktivitas salin-tempel umum pengguna. Tombol manual `[PASTE]` tetap dipertahankan.
4. **Visual Scrubber / Mini Range Slider untuk Klip** (Rencana Fase Selanjutnya): Mengatur titik potong klip secara visual dengan slider ganda (*dual-slider*) dan cuplikan frame thumbnail.

---

## 2. Rencana Masa Depan: Visual Scrubber / Mini Range Slider (Next Phase)

### A. Konsep & Kebutuhan
- Saat ini pengaturan rentang waktu klip dilakukan dengan mengetik teks `HH:MM:SS` pada panel Multi-Clip Slicer.
- Pada fase berikutnya, antarmuka akan dilengkapi dengan **Dual-Handle Visual Range Slider**:
  - Track slider horizontal yang merepresentasikan total durasi video.
  - Handle kiri untuk `Start Time` dan handle kanan untuk `End Time`.
  - Preview thumbnail melayang (*floating tooltip thumbnail*) saat handle digeser.

### B. Arsitektur Teknis yang Diarsipkan
1. **Thumbnail Storyboard / Frame Sprites**:
   - Memanfaatkan yt-dlp `--write-thumbnail` atau ekstraksi frame ringan FFmpeg (`fps=1/60,scale=160:-1`) ke direktori cache sementara.
   - Alternatif: Storyboard sprite manifest bawaan YouTube player jika tersedia.
2. **Komponen Visual Dual Slider**:
   - Subclass `QSlider` atau kustom `QFrame` dengan penanganan event mouse `paintEvent`, `mousePressEvent`, dan `mouseMoveEvent`.
   - Snapping otomatis ke batas detik/menit terdekat.
3. **Penyimpanan Rencana**:
   - Rencana ini disimpan di backlog roadmap dan siap diimplementasikan pada pembaruan pasca-v1.0.

---

## 3. Arsitektur Batch / Playlist Downloader & Solusi Bug Video-in-Playlist

### A. Fast Playlist Metadata Extraction (`extract_flat`)
- Menggunakan opsi yt-dlp `extract_flat: 'in_playlist'` dan `dump_single_json: True`.
- Berjalan dalam 1-2 detik tanpa mengunduh manifest stream masing-masing video satu per satu.
- Mengembalikan daftar terstruktur berisi `id`, `title`, `duration`, `uploader`, dan `thumbnail`.

### B. Dialog Pilihan Cerdas (`PlaylistPromptDialog`)
- **Masalah**: Ketika pengguna menyalin link video YouTube yang sedang diputar di antrean playlist, URL mengandung `watch?v=_g34owoPBWw&list=PLWcl...&index=17`. Jika langsung diunduh sebagai playlist, pengguna terkejut karena yang diinginkan adalah video tersebut.
- **Solusi**: Dibuat pemisahan deteksi URL:
  1. `is_pure_playlist_url(url)`: Link playlist murni tanpa parameter `v=` (misal `/playlist?list=...`). Langsung membuka `PlaylistDialog`.
  2. `is_video_in_playlist_url(url)`: Link yang memiliki parameter video `v=` sekaligus playlist `list=`. Memunculkan `PlaylistPromptDialog` dengan opsi:
     - `[ 🎬 UNDUH HANYA VIDEO INI ]` (Fokus utama / Default): Membersihkan URL dengan `normalize_youtube_url()` ke link video murni dan menganalisis single video (4K/1080p, ProRes, clip slicer).
     - `[ 📑 UNDUH SELURUH PLAYLIST ]`: Melanjutkan ekstraksi playlist dan membuka `PlaylistDialog`.
     - `[ BATAL ]`.

### C. Antarmuka Dialog Batch (`PlaylistDialog`)
- **Pencarian Real-Time**: Kolom input `grep` untuk menyaring daftar video secara instan tanpa re-render widget (`card.setVisible()`).
- **Kontrol Pilihan**: Tombol `[Pilih Semua]` dan `[Batal Pilih]`.
- **Target Video Highlight**: Jika dibuka dari link video di playlist, video tersebut otomatis ditandai dengan badge cyan `[VIDEO INI]`, auto-scroll ke kartu tersebut, serta disediakan tombol cepat `[Hanya Video Ini]` di toolbar.
- **Preset Kualitas & Format Global**:
  - `1080p | Full HD (MP4)`
  - `Best Resolution | Max (MKV)`
  - `720p | HD (MP4)`
  - `Audio Only | MP3 320k`
  - `Audio Only | M4A Original`
- **Integrasi Antrean**: Setiap video terpilih dimasukkan ke `download_manager.start_download()` dan berjalan bertahap sesuai batas `max_concurrent_downloads`.

---

## 4. Penghapusan Fitur Smart Clipboard Auto-Detect
- Pengguna memutuskan untuk menonaktifkan dan menghapus fitur auto-detect clipboard (`ctrl+c monitoring`).
- Seluruh listener clipboard latar belakang, banner popup, dan pengaturan terkait telah dibersihkan dari codebase untuk menjaga efisiensi memori dan menghindari gangguan saat beraktivitas di aplikasi lain.
- Tombol manual `[PASTE]` di samping kolom URI tetap tersedia sebagai metode input cepat.
