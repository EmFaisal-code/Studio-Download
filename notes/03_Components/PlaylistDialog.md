---
title: "Komponen: PlaylistDialog & PlaylistPromptDialog"
type: component
tags:
  - project/studio-download
  - component/dialog
  - feature/playlist
date: 2026-10-11
status: active
aliases:
  - PlaylistDialog
  - PlaylistPromptDialog
---

# PlaylistDialog & PlaylistPromptDialog // Batch Downloader

## 1. Ikhtisar
Modul dialog native PySide6 yang menangani seluruh alur kerja pengunduhan daftar putar (playlist/koleksi) dan resolusi tautan video-dalam-playlist di Studio Download.

Berkas sumber: [`ui/dialogs/playlist_dialog.py`](file:///d:/Project/YT/ui/dialogs/playlist_dialog.py)

---

## 2. Komponen Kelas

### A. `PlaylistPromptDialog(QDialog)`
Dialog interaktif yang muncul ketika pengguna memasukkan tautan YouTube yang berisi ID video spesifik sekaligus ID playlist (misalnya `watch?v=...&list=...&index=...`).

* **Tujuan**: Mencegah salah unduh seluruh playlist saat pengguna sebenarnya hanya ingin mengunduh satu klip yang sedang ditonton.
* **Pilihan**:
  1. `btn_single` (`[ 🎬 UNDUH HANYA VIDEO INI ]`): Menghapus parameter `&list=` dan langsung menganalisis video tunggal ke layar utama (kartu format, transkode, clip slicer). Fokus default saat dialog terbuka.
  2. `btn_playlist` (`[ 📑 UNDUH SELURUH PLAYLIST ]`): Melanjutkan ekstraksi playlist dan membuka `PlaylistDialog`.
  3. `btn_cancel` (`[ BATAL ]`): Membatalkan operasi.

### B. `PlaylistDialog(QDialog)`
Dialog modal bertema Dark Zinc Cyberpunk untuk memilih dan mengunduh massal item dalam playlist.

* **Fitur**:
  - **Pencarian Instan**: Kolom input `grep` untuk memfilter video berdasarkan judul secara langsung.
  - **Pilihan Cepat**: Tombol `[Pilih Semua]` dan `[Batal Pilih]`.
  - **Target Video Highlight**: Jika dibuka dari link video di playlist, video tersebut ditandai dengan badge cyan `[VIDEO INI]`, auto-scroll ke kartu tersebut, serta disediakan tombol `[Hanya Video Ini]` di toolbar.
  - **Preset Kualitas & Format**: Dropdown global (1080p MP4, Max MKV, 720p MP4, MP3 320k, M4A Original).
  - **Tombol Eksekusi**: `[UNDUH X MEDIA TERPILIH]` yang terhubung ke sinyal `batch_confirmed(list, dict)`.

### C. `PlaylistItemCard(QFrame)`
Kartu baris individual untuk setiap media dalam daftar playlist:
- Checkbox seleksi.
- Nomor urut (`#01`, `#02`, ...).
- Judul media.
- Informasi durasi dan kreator/uploader.
- Badge opsional `[VIDEO INI]` untuk video rujukan awal.

---

## 3. Integrasi Alur Data
1. `MainWindow._start_analysis()` mendeteksi tipe URL melalui `is_video_in_playlist_url()` dan `is_pure_playlist_url()`.
2. Jika video-dalam-playlist: `PlaylistPromptDialog` dipanggil.
3. Jika playlist dipilih: `ParseWorker(url, is_playlist=True)` memanggil `backend.parser.parse_playlist()`.
4. Setelah selesai, `_open_playlist_dialog()` menampilkan `PlaylistDialog`.
5. Pilihan batch dipancarkan ke `_on_playlist_batch_confirmed()`, yang kemudian memanggil `download_manager.start_download()` untuk setiap item terpilih.
