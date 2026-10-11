---
title: ADR-009 YouTube URL Normalization & Installer Permission Hardening
type: adr
tags:
  - project/studio-download
  - adr/architecture
  - fix/youtube-playlist-urls
  - fix/windows-permissions
date: 2026-10-03
status: accepted
aliases:
  - ADR-009
---

# ADR-009 // YouTube URL Normalization & Windows Installer Permission Hardening

## 1. Konteks & Masalah
1. **Perbedaan Hasil Parsing Antara Link YouTube Single vs Link dalam Playlist**:
   - Pengguna melaporkan bahwa link video pendek `https://youtu.be/ZRe3rT2WZto?si=...` menampilkan kartu resolusi lengkap (4K, 1440p, 1080p, dll.), durasi, thumbnail, dan views.
   - Namun link yang sama saat disalin dari playlist `https://www.youtube.com/watch?v=ZRe3rT2WZto&list=PLWcl...&index=18` justru menampilkan judul playlist (*Arknights: Endfield Story Quest Walkthrough...*), thumbnail hilang (`// NO_PREVIEW`), durasi `--`, dan kartu resolusi kosong.
   - **Akar Masalah**: Keberadaan parameter `&list=` dan opsi `extract_flat: 'in_playlist'` di `yt-dlp` tanpa parameter `'noplaylist': True` menyebabkan yt-dlp mengekstrak objek playlist alih-alih data video tunggal yang diminta.

2. **Dialog "Who Are You" Macet / Aplikasi Tidak Bisa Ditutup Setelah Instalasi Windows**:
   - Pengguna yang menginstal aplikasi melalui installer Windows (`Setup.exe`) ke direktori sistem `C:\Program Files\Studio Download` mengalami bug di mana jendela dialog onboarding `$ auth session // ONBOARDING_PROFILE` membeku (*freeze*), tombol `[✕]`, `[SKIP / ENTER AS GUEST]`, dan `[SAVE LOGIN]` tidak dapat ditekan, dan aplikasi tidak bisa ditutup.
   - **Akar Masalah**:
     - Direktori `C:\Program Files\...` bersifat *read-only* bagi proses standar tanpa hak Administrator (UAC).
     - Saat dialog menyimpan pengaturan atau sesi tamu (`logout_to_guest`), `save_settings()` mencoba menulis ke `C:\Program Files\Studio Download\settings.json`, memicu `PermissionError: [Errno 13] Permission denied`.
     - Karena slot PySide6 tidak membungkus I/O dalam `try...finally`, pengecualian tersebut memutus alur fungsi sebelum `self.reject()` atau `self.accept()` dieksekusi. Dialog tetap berstatus modal aktif (`dlg.exec()`) dan mengunci seluruh jendela utama.
     - Setiap peluncuran aplikasi kembali memicu dialog karena sesi tamu sebelumnya gagal tersimpan atau diset `user_profile: None`.

---

## 2. Keputusan Desain & Solusi

### A. Normalisasi URL YouTube & Opsi `noplaylist`
1. **Fungsi `normalize_youtube_url(url: str)`** (`backend/parser.py`):
   - Mendeteksi apakah URL berisi ID video spesifik (baik melalui `v=...`, `youtu.be/...`, `/shorts/...`, atau `/live/...`).
   - Membersihkan seluruh parameter pelacak atau playlist (`list=...`, `index=...`, `si=...`, `t=...`, `feature=...`) dan menghasilkan URL kanonikal tunggal: `https://www.youtube.com/watch?v={video_id}`.
   - Mempertahankan URL playlist murni (misal `/playlist?list=...`) yang memang tidak memiliki ID video.
2. **Konfigurasi `noplaylist: True`**:
   - Ditambahkan pada konfigurasi `ydl_opts` di `backend/parser.py` (`parse_url`) dan `backend/downloader.py` (`_run_ytdlp`).
   - Memastikan `yt-dlp` secara tegas mengekstrak video individual ketika URL memuat referensi video dan playlist.
3. **Penyelarasan Input UI** (`ui/main_window.py`):
   - Memperbarui teks URL di kolom input secara otomatis ke URL kanonikal saat tombol `RUN_ANALYZE` ditekan maupun saat stream diterima dari ekstensi browser.

### B. Penyimpanan User Data di `%APPDATA%` & Ketahanan Modal Dialog
1. **Pemisahan Bundle Dir vs User Data Dir** (`backend/config.py`):
   - `get_bundle_dir()`: Mengarah ke aset *read-only* (template frontend, ikon, biner).
   - `get_app_dir()`: Menguji izin tulis pada direktori biner. Jika aplikasi terpasang di direktori sistem (misal `C:\Program Files\...`) atau direktori biner tidak memiliki hak tulis, penyimpanan dialihkan secara otomatis ke `%APPDATA%\StudioDownload`.
   - Menyalin berkas konfigurasi bawaan `settings.json` ke `%APPDATA%\StudioDownload` saat peluncuran pertama.
   - Mode portabel (`portable.flag` atau folder lokal yang *writable*) tetap didukung penuh.
2. **Ketahanan Eksekusi Dialog (`WhoAreYouDialog`)** (`ui/dialogs/user_dialog.py`):
   - Membungkus seluruh operasi I/O dan jaringan di `_on_skip_or_close()` dan `_on_submit()` dalam blok `try...except...finally:` yang menjamin `self.reject()` atau `self.accept()` pasti dieksekusi.
   - Menambahkan penangan tombol `Escape` (`keyPressEvent`) agar pengguna dapat menutup dialog dengan instan.
   - Memperbaiki penanganan `mousePressEvent`, `mouseMoveEvent`, dan `mouseReleaseEvent` agar tidak memblokir sinyal klik elemen anak.
3. **Pencegahan Perulangan Onboarding**:
   - Menambahkan flag `"onboarding_completed": True` di `settings.json` saat pengguna memilih mode Tamu (*Guest*) ataupun masuk dengan akun.
   - `MainWindow._check_initial_user_profile()` memeriksa flag ini sehingga dialog onboarding tidak akan pernah muncul kembali secara mengganggu pada pembukaan aplikasi berikutnya.

---

## 3. Hasil & Verifikasi
- Pengujian langsung `parse_url()` dengan URL video biasa (`youtu.be/ZRe3rT2WZto?si=...`) dan URL video dalam playlist (`youtube.com/watch?v=ZRe3rT2WZto&list=...&index=18`) menghasilkan keluaran metadata yang **100% identik**:
  - `type: "video"`
  - `title: "Arknights Endfield 1.4 Wuling Story Quest - VII Walkthrough (JP Voice)"`
  - 8 kartu resolusi (2160p, 1440p, 1080p, 720p, 480p, 360p, 240p, 144p) dengan estimasi ukuran akurat.
- Dialog profil dan onboarding kini dapat ditutup secara instan via tombol `[✕]`, `[SKIP / ENTER AS GUEST]`, `[SAVE LOGIN]`, maupun tombol `Escape` tanpa risiko macet pada instalasi Windows standar.
