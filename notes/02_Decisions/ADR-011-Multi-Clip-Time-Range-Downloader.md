---
title: ADR-011 Multi-Clip Time Range Slicer & Segment Downloader
type: adr
tags:
  - project/studio-download
  - adr/architecture
  - feature/multi-clip
  - feature/time-range
date: 2026-10-03
status: accepted
aliases:
  - ADR-011
---

# ADR-011 // Multi-Clip Time Range Slicer & Segment Downloader

## 1. Konteks & Kebutuhan Pengguna
Pengguna membutuhkan kapabilitas untuk mengunduh segmen durasi tertentu dari sebuah video (misal dari durasi A ke durasi B). Selain satu rentang waktu, pengguna secara khusus memilih kapabilitas untuk menentukan **beberapa rentang waktu sekaligus** (misalnya klip 1 dari `01:00` s/d `02:30` dan klip 2 dari `05:00` s/d `07:15`), di mana masing-masing rentang dipotong dan diunduh secara independen menjadi berkas video terpisah.

---

## 2. Analisis Masalah & Arsitektur Solusi

### A. Ekstraksi Fragmen Jaringan Efisien (Bandwidth & Time Saving)
- Mengunduh video penuh (misal 2 jam, ukuran 8 GB) hanya untuk memotong klip 2 menit adalah pemborosan kuota dan waktu yang masif.
- **Solusi dengan `yt-dlp`**:
  Menggunakan opsi bawaan `download_ranges`:
  ```python
  from yt_dlp.utils import download_range_func
  ydl_opts['download_ranges'] = download_range_func(None, [(sec_start, sec_end)])
  ydl_opts['force_keyframes_at_cuts'] = True
  ```
  Pada server video berformat DASH/HLS (YouTube), `yt-dlp` **hanya mengunduh pecahan fragmen/chunk jaringan di rentang waktu tersebut** langsung dari CDN. Ukuran unduhan berkurang hingga 95%+ dan selesai dalam hitungan detik.

### B. Fallback Slicing FFmpeg untuk Seluruh Sumber Stream
- Untuk sumber non-DASH atau TikTok (TikWM/TokCDN) serta stream HLS eksternal:
  - Pemotongan durasi dieksekusi secara presisi menggunakan FFmpeg dengan opsi *fast stream copy*:
    ```bash
    ffmpeg -y -ss {sec_start} -to {sec_end} -i {source} -c copy -avoid_negative_ts make_zero {dest}
    ```
  - Menghindari *black frame*, menjaga sinkronisasi audio-video, serta tidak memerlukan transkode lambat jika format kontainer sudah kompatibel.

### C. Pembuatan Tugas Antrean Multi-Clip Terisolasi
- Dibandingkan menjalankan satu proses batch monolitik yang membingungkan:
  - Setiap klip waktu diekstrak dan didaftarkan sebagai **Task terpisah** di dalam `DownloadManager`.
  - Masing-masing klip memiliki progress bar mandiri, telemetri kecepatan (MB/s), tombol `[JEDA]` / `[LANJUTKAN]`, serta tombol `[PUTAR]` dan `[FOLDER]` saat selesai.
  - Nama file diberi akhiran tag rentang waktu otomatis:  
    `{Judul_Video} [01.00-02.30].mp4` atau `{Judul_Video} [Label 01.00-02.30].mp4`.
  - Durasi tugas dihitung presisi sesuai panjang potongan klip (`end_sec - start_sec`).

---

## 3. Komponen yang Diperbarui

1. **`backend/parser.py`**:
   - Menambahkan fungsi helper `parse_time_str(val)` yang memvalidasi format `HH:MM:SS`, `MM:SS`, atau detik numerik.
   - Menambahkan `format_time_label(seconds)` untuk penamaan tag file Windows yang bersih (`01.30` alih-alih `01:30`).
2. **`backend/downloader.py`**:
   - `start_download()`: Mengalkulasi durasi klip spesifik dan menambahkan tag `[start-end]` ke judul tugas.
   - `_run_ytdlp()`: Menginjeksi `download_ranges` dan `force_keyframes_at_cuts` pada `ydl_opts`.
   - `_download_tiktok()`: Menambahkan pemotongan segmen FFmpeg sebelum pemindahan ke file akhir.
   - `_download_hls_fallback()`: Memotong stream HLS langsung saat remuxing MP4.
3. **`backend/app.py`**:
   - Menambahkan field `section_start`, `section_end`, dan array `clips` pada schema `DownloadRequest`.
   - Menangani pembuatan antrean batch multi-clip secara otomatis.
4. **`backend/i18n.py`**:
   - Menambahkan lokalisasi lengkap untuk Bahasa Indonesia dan Inggris:
     `clip_section_title`, `clip_enable_toggle`, `clip_add_btn`, `clip_badge`, `clip_dur_label`, `clip_btn_start_clips`, `clip_err_invalid`.
5. **Desktop PySide6 GUI (`ui/components/clip_selector.py` & `ui/main_window.py`)**:
   - Membuat komponen `ClipSelectorWidget` dengan antarmuka baris dinamis:
     - Checkbox pengaktifan pemotongan durasi.
     - Baris input waktu mulai (`00:00:00`), tanda panah (`➔`), waktu selesai (`01:00:00`), label durasi dinamis `[01:00:00]`, field nama klip opsional, dan tombol hapus `[✕]`.
     - Lebar input field disesuaikan menjadi 85px agar format 3 segmen `HH:MM:SS` muat nyaman.
     - Penambahan klip cerdas berbasis jam: video berdurasi $\ge$ 1 jam otomatis menginisiasi rentang jam (`00:00:00` s/d `01:00:00`, tombol tambah melompat per 1 jam).
     - Tombol `[+ TAMBAH RENTANG KLIP]`.
   - Tombol unduh utama berubah secara real-time: `UNDUH {count} KLIP SEKALIGUS()`.
   - Validasi otomatis mencegah input waktu mulai $\ge$ waktu selesai.
6. **Web Frontend (`frontend/index.html` & `frontend/app.js`)**:
   - Menambahkan panel `clipDeckContainer` di bawah kartu format.
   - Implementasi logika penambahan/penghapusan baris klip dan pengiriman `payload.clips`.

---

## 4. Penanganan YouTube Bot Check & Autentikasi Cookies
1. **Latar Belakang Bot Check (`Sign in to confirm you're not a bot`)**:
   - YouTube secara aktif menguji request stream video/audio tertentu dengan tantangan BotGuard / JS challenge (`LOGIN_REQUIRED`).
   - Ekstraksi informasi video publik (`extract_flat`) dapat berhasil sementara pengunduhan format stream gagal jika sesi IP diblokir atau file `cookies.txt` telah kedaluwarsa.
2. **Mitigasi & Solusi di Studio Download**:
   - Auto-detection runtime Node.js di sistem Windows (`C:\Program Files\nodejs\node.exe`) untuk eksekusi solver EJS yt-dlp.
   - Pendaftaran fallback player clients (`web`, `mweb`, `android`, `ios`) pada `extractor_args.youtube`.
   - Tombol aksi `[ATUR COOKIES]` interaktif pada kartu antrean jika terdeteksi `BOT_CHECK_REQUIRED` untuk membuka menu pengaturan secara langsung.
   - Panduan pengguna untuk mengekspor file `cookies.txt` segar via browser companion extension ketika sesi YouTube kedaluwarsa.

---

## 5. Hasil Verifikasi
- Pengujian unit otomatis di `scratch/test_multiclip.py` membuktikan:
  - Parsing format waktu `MM:SS`, `HH:MM:SS`, dan detik numerik berhasil 100%.
  - Fungsi `format_duration_hms()` menjamin format 3-segmen `HH:MM:SS` presisi (`00:00:00`, `01:00:00`, `04:27:00`).
  - Pembuatan tugas batch Multi-Clip menghasilkan durasi dan penamaan tag yang akurat.
  - Kompilasi Python (`py_compile`) bebas galat sintaks.
