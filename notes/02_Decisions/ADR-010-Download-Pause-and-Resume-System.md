---
title: ADR-010 Download Pause & Resume Control System
type: adr
tags:
  - project/studio-download
  - adr/architecture
  - feature/pause-resume
  - concurrency/threading
date: 2026-10-03
status: accepted
aliases:
  - ADR-010
---

# ADR-010 // Sistem Kontrol Jeda (Pause) & Lanjutkan (Resume) Unduhan

## 1. Konteks & Kebutuhan
Sebelumnya, antarmuka `Studio Download` hanya menyediakan dua siklus tugas: berjalan (`downloading` / `muxing`) atau membatalkan secara permanen (`[ABORT]`). Pengguna membutuhkan kemampuan untuk:
1. Menjeda proses unduhan kapan saja (misal ketika bandwidth internet dialihkan sementara untuk meeting atau browsing darurat).
2. Menghentikan konsumsi jaringan (bandwidth) dan siklus CPU seketika tanpa memutus koneksi secara fatal atau merusak berkas `.part` yang sedang diisi.
3. Melanjutkan kembali (*resume*) unduhan dari posisi byte terakhir tanpa mengulang dari 0%.
4. Membatalkan tugas secara bersih (`[ABORT]`) bahkan ketika tugas sedang dalam status dijeda tanpa menimbulkan thread menggantung (*thread leak* / *deadlock*).
5. Mendukung sistem jeda baik pada antarmuka GUI PySide6 maupun Web Frontend / REST API.

---

## 2. Analisis Masalah & Arsitektur Solusi

### A. Mekanisme Jeda Thread-Safe Tanpa Menghentikan Proses
- `yt-dlp` berjalan sebagai pustaka Python di dalam thread terisolasi (`_run_ytdlp`). yt-dlp tidak memiliki argumen CLI langsung untuk mem-pause proses yang sedang berjalan.
- **Solusi**: Memanfaatkan `threading.Event` (`pause_events[task_id]`), di mana:
  - `set()` = Berjalan normal.
  - `clear()` = Berhenti / Dijeda.
- Dalam setiap loop chunk (`ytdl_hook` pada yt-dlp, loop HTTP chunk di `_download_tiktok`, dan loop segmen di `_download_hls_fallback`), ditambahkan evaluasi `pause_events[task_id]`:
  ```python
  pause_ev = pause_events.get(task_id)
  if pause_ev and not pause_ev.is_set():
      while pause_ev and not pause_ev.is_set():
          if cancel_ev and cancel_ev.is_set():
              raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")
          time.sleep(0.25)
  ```
- **Responsivitas Cepat**: Mengatur `http_chunk_size` sebesar 2 MB (`2097152` bytes) pada `ydl_opts`. Dengan ukuran fragment/chunk 2 MB, siklus jeda bereaksi instan dalam hitungan milidetik setelah tombol ditekan.

### B. Mencegah Kebocoran Thread & Duplikasi Tugas
- Ketika tugas dijeda, statusnya berubah menjadi `"paused"`.
- Untuk mencegah pemanggilan `_start_next_queued_task()` atau `resume_download()` membuat thread kedua pada tugas yang sama:
  - Diterapkan kamus pelacak thread aktif: `active_threads = {task_id: threading.Thread}`.
  - Saat `resume_download(task_id)` dipanggil:
    1. Jika `task_id in active_threads`: Thread unduhan telah ada di memori dan sedang menunggu sinyal jeda; sistem cukup memanggil `pause_events[task_id].set()` dan mengubah status ke `"downloading"`.
    2. Jika `task_id not in active_threads` (misal tugas dijeda saat masih di antrean *queue*): Sistem membuat thread baru secara bersih.
  - Jika kuota unduhan bersamaan (`max_concurrent_downloads`) penuh saat tugas hendak dilanjutkan, tugas dialihkan ke `"queued"` secara tertib.

### C. Pembatalan Bersih Saat Berstatus Dijeda
- Jika pengguna menekan tombol `[ABORT]` saat status tugas sedang `[DIJEDA_PAUSE]`:
  - `cancel_download()` memanggil `cancel_events[task_id].set()` dan secara simultan memanggil `pause_events[task_id].set()`.
  - Loop tunggu jeda seketika terlepas (*unblocked*), mendeteksi sinyal pembatalan, memicu `DownloadCancelledException`, dan membersihkan direktori `.studio_temp_*`.

---

## 3. Komponen yang Diperbarui

1. **`backend/downloader.py`**:
   - Menambahkan dictionary `pause_events` dan `active_threads`.
   - Mengimplementasikan `pause_download(task_id)` dan `resume_download(task_id)`.
   - Memasukkan pemeriksaan `pause_ev` pada `ytdl_hook`, `_download_tiktok`, dan `_download_hls_fallback`.
   - Menyelaraskan unblock pada `cancel_download` dan pembersihan pada `dismiss_task`.
2. **`backend/i18n.py`**:
   - Menambahkan entri terjemahan Indonesia & Inggris: `status_paused`, `task_paused_desc`, `task_btn_pause`, `task_btn_resume`.
3. **`backend/app.py`**:
   - Menambahkan rute REST API:
     - `POST /api/tasks/{task_id}/pause`
     - `POST /api/tasks/{task_id}/resume`
4. **`ui/components/task_item.py`** (PySide6):
   - Menambahkan sinyal `pause_clicked = Signal(str)` dan `resume_clicked = Signal(str)`.
   - Mengatur styling tombol bertema JetBrains Mono:
     - `.cardPauseBtn`: Warna aksen amber `#fbbf24` (Jeda).
     - `.cardResumeBtn`: Warna aksen cyan `#38bdf8` (Lanjutkan).
   - Menampilkan badge status amber `[STATUS:DIJEDA_PAUSE 25.0%]` serta deskripsi "Unduhan dijeda oleh pengguna".
5. **`ui/main_window.py`**:
   - Menghubungkan sinyal `card.pause_clicked` ke `self._pause_task` dan `card.resume_clicked` ke `self._resume_task`.
6. **`frontend/app.js`**:
   - Menampilkan tombol dinamis `[PAUSE] / [JEDA]` saat proses mengunduh dan `[RESUME] / [LANJUTKAN]` saat dijeda.
   - Mengimplementasikan fungsi `pauseTask(taskId)` dan `resumeTask(taskId)`.

---

## 4. Hasil Verifikasi
- Pengujian unit otomatis di `scratch/test_pause_resume.py` memverifikasi seluruh skenario:
  - Transisi jeda (*Pause state transition*) berjalan sukses.
  - Melanjutkan tugas dengan thread aktif di memori (*Resume with active thread*) berjalan tanpa duplikasi thread.
  - Melanjutkan tugas dari antrean (*Resume queued task*) berjalan tertib.
  - Pembatalan saat dijeda (*Abort while paused*) segera melepas event jeda dan membersihkan memori tanpa hambatan.
  - Kompilasi Python `py_compile` sukses tanpa galat sintaks.
