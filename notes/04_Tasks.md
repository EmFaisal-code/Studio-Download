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
- [x] **Visual Media Player & Precision Clip Trimmer (Widescreen Hybrid Modal)**:
  - Menyediakan modal kerja leluasa berbentang lebar (`VisualTrimmerDialog`) yang terhubung langsung dengan tombol `[BUKA VISUAL TRIMMER]` di panel klip.
  - Pemutar video stream langsung berbasis `QMediaPlayer` + `QVideoWidget` (Qt 6 WMF) memanfaatkan stream H.264/AAC ringan dari YouTube, TikTok, dan web stream HLS.
  - Interactive timeline scrubber (`TrimmerTimelineTrack`) dengan highlight warna cyan pada rentang terpilih, playhead drag, dan penanda visual In/Out.
  - Kontrol pemotongan presisi NLE: Tombol `SET IN [I]`, `SET OUT [O]`, tombol transport (`-5s`, `-1s`, `PLAY/PAUSE`, `+1s`, `+5s`), serta shortcut keyboard cepat.
  - Panel daftar klip tersimpan di sisi samping dengan tombol pratinjau teks `PLAY` dan `DEL`.
  - Sinkronisasi dua arah instan ke antrean unduhan utama via tombol `APPLY TO DOWNLOAD`.
- [x] **Overhaul UI/UX Visual Trimmer & Spektrum Resolusi Lengkap (Max - 144p)**:
  - **Eliminasi Total "AI Slop" & Emoji/Logo Tombol**: Menghapus seluruh ikon/emoji grafis (`🎬`, `▶`, `⏸`, `⏪`, `◀`, `⏩`, `🚩`, `🏁`, `➕`, `✓`, `📺`, `🔊`, `⌨`) dari semua tombol dan label. Menggantinya dengan teks tipografi studio profesional yang tegas dan bersih (`PLAY`, `PAUSE`, `-5s`, `SET IN [I]`, `SET OUT [O]`, `SAVE CLIP`, `APPLY TO DOWNLOAD`, dll).
  - **Perbaikan Glitch Glyphs Kotak Kosong `[ ] [ ]`**: Mengganti karakter simbol yang rentan rusak pada kartu klip di Windows dengan tombol teks mandiri `PLAY` dan `DEL`.
  - **Spektrum Kualitas Penuh (Max hingga 144p)**: Menyediakan pilihan resolusi pratinjau lengkap dari `2160p (4K)`, `1440p (2K)`, `1080p (FHD)`, `720p (HD)`, `480p (SD)`, `360p (Fast Scrub)`, `240p (Low)`, hingga `144p (Min)` dengan default 360p/480p untuk *instant scrubbing*.
  - **Timeline Track NLE Berstandar Studio**: Mengganti segitiga terbalik dengan *bracket notch markers* 2px presisi dan playhead berkepala pil minimalis.
  - **Perbaikan Format Estimasi**: Memperbaiki bug dobel tilde (`~~25.6 MB`) menjadi format rapi `Duration: 00:01:00  •  ~25.6 MB`.
- [x] **Perbaikan UI/UX Bug Jendela Melebar & Tombol Terpotong pada Unduhan Berjudul Panjang**:
  - Mengimplementasikan `ElidedLabel` khusus turunan `QLabel` pada kartu antrean unduhan (`TaskItemWidget`) dengan `minimumSizeHint()` terkontrol (50px) dan pemotongan teks otomatis via `QFontMetrics.elidedText()`.
  - Mengeliminasi lonjakan minimum width dari 1608px menjadi 505px, mengunci `scroll_content` tepat pada lebar viewport (1014px, 0px overflow).
  - Menyelamatkan badge status `[STATUS:COMPLETED_200]` dan seluruh tombol aksi (`[PLAY]`, `[DIR]`, `[DEL]`, `[PAUSE]`, `[ABORT]`) agar tetap berada 100% di dalam kartu tanpa terpotong ke luar batas kanan jendela.
  - Menambahkan tooltip interaktif otomatis untuk menampilkan judul penuh saat di-hover dan mengaktifkan `wordWrap=True` pada petunjuk klip.
- [x] **Solusi Pemantauan Ruang Penyimpanan & Penghentian Sementara (Conversion Guard & Auto-Resume)**:
  - **Pemantauan Real-Time Ruang Penyimpanan**: Memeriksa kapasitas ruang kosong secara presisi sebelum konversi dimulai (ProRes 422 transcode, TikTok audio/MKV remuxing, Generic Stream HLS remuxing) serta selama konversi FFmpeg berjalan aktif dengan interval pelacakan real-time setiap 0.8 detik.
  - **Sistem Peringatan Informatif**: Menampilkan kartu status khusus berbingkai merah menyala (`#f43f5e`), status badge `[STATUS:LOW DISK / PAUSED]`, telemetri drive dan sisa ruang aktif `[D: Sisa 142.0 MB / Butuh 4.2 GB]`, serta tooltip diagnostik detail yang menjelaskan status penghentian sementara dan tindakan yang diperlukan.
  - **Mekanisme Jeda Otomatis Lossless**: Menghentikan proses konversi FFmpeg di tingkat kernel Windows via `NtSuspendProcess` tanpa merusak buffer pipeline atau mengulang render dari awal, sembari menyimpan checkpoint progres frame dan durasi.
  - **Pemantauan Berkelanjutan & Auto-Resume**: Menjalankan daemon thread latar belakang (`DiskSpaceWatcher`) yang memindai kondisi partisi drive setiap 2.0 detik dan secara otomatis melanjutkan konversi via `NtResumeProcess` seketika saat ruang kosong mencukupi ambang batas aman (kebutuhan render + headroom darurat 300 MB).
  - **Opsi Pengecekan Manual**: Menghadirkan tombol aksi `[CEK DISK]` / `[CHECK DISK]` dan `[GANTI FOLDER]` / `[STORAGE]` pada kartu tugas sehingga pengguna dapat langsung memicu verifikasi ulang tanpa menunggu siklus timer otomatis.
  - **Pencatatan Audit Log Lengkap**: Seluruh kejadian (pre-check pause, in-flight suspension, auto-resume, manual recheck attempt, dan cancellation) dicatat secara kronologis dalam berkas audit `conversion_audit.log` lengkap dengan timestamp, Task ID, drive, dan metrik kapasitas.
  - **Pengujian Multi-Skenario Menyeluruh**: Divalidasi melalui rangkaian pengujian otomatis `test_conversion_guard.py` dengan 100% kelulusan mencakup skenario ruang kurang di awal, proses tersuspensi di tengah jalan, pelepasan ruang kembali, penolakan saat ruang masih kurang, dan pembatalan bersih.

## 📌 Rencana & Tugas Mendatang (Backlog)
- [ ] **Subtitle / CC Downloader**: Pilihan mengunduh subtitle otomatis (`.srt` / `.vtt`) terpisah atau di-embed ke dalam file MKV.
- [ ] **Bandwidth Graph Visualizer**: Grafik kecepatan unduhan real-time mini di bagian telemetri bawah.

