---
title: ADR-006 User Identity Onboarding, Guest Session, & Admin Dashboard
type: adr
tags:
  - project/studio-download
  - adr/identity
  - adr/admin-dashboard
  - adr/session
date: 2026-09-20
status: completed
aliases:
  - ADR-006
---

# ADR-006: User Identity Onboarding, Guest Session, & Pemisahan Ruang Publik vs Privat

## Status
**Completed** (Diimplementasikan di `backend/config.py`, `backend/i18n.py`, `ui/dialogs/user_dialog.py`, `ui/dialogs/profile_dialog.py`, `ui/components/title_bar.py`, dan `ui/main_window.py`)

## Konteks & Prinsip Privasi
Aplikasi Studio Download didistribusikan ke banyak pengguna publik. Terdapat perbedaan mendasar antara **Ruang Publik (Client Software)** dan **Ruang Privat (Developer/Admin)**:
1. **Ruang Publik (Aplikasi Klien)**:
   - Pengguna hanya boleh melihat dan mengelola identitas profil **milik mereka sendiri** (`UserProfileDialog`).
   - Software klien **DILARANG KERAS** menampilkan panel Admin Dashboard, metrik global pengguna lain, ataupun daftar seluruh pengguna dari database Supabase (`studio_users`). Hal tersebut melanggar privasi dan keamanan data pengguna.
2. **Ruang Privat (Pengembang/Admin)**:
   - Dashboard pengelolaan seluruh pengguna hanya boleh diakses melalui dashboard resmi Supabase di browser atau skrip CLI admin terpisah (`scratch/admin_cloud_users.py`), terisolasi sepenuhnya dari bundle distribusi klien.

## Keputusan Arsitektural
1. **Pemisahan Tegas Ruang Publik vs Privat**:
   - Menghapus komponen modal `AdminDashboardDialog` dari antarmuka aplikasi klien publik.
   - Menggantikannya dengan **`UserProfileDialog`** (`ui/dialogs/profile_dialog.py`), sebuah modal ringkas personal yang hanya menampilkan identitas pengguna aktif (atau status Tamu), tombol ganti akun (*Who Are You*), dan tombol beralih ke sesi tamu.
   - Mencegah software klien melakukan querying dan caching seluruh daftar pengguna dari Supabase.
2. **Onboarding & Registrasi Personal ("Who Are You")**:
   - `WhoAreYouDialog` (`ui/dialogs/user_dialog.py`): Mengisi nama dan pilihan peran (*Video Editor, Content Creator, Pelajar, Audio Engineer, Umum*) atau lewati ke mode Tamu.
   - Sinkronisasi ke Supabase hanya mengirim/memperbarui record milik pengguna itu sendiri, mengembalikan Supabase UUID resmi untuk sesi lokal.
3. **Sesi Tamu (Guest Session)**:
   - Pengguna yang tidak ingin mendaftar dapat langsung masuk sebagai "Tamu (Guest)".
   - Sesi tamu sepenuhnya *in-memory* dan tidak menyentuh database Supabase.
4. **Indikator Title Bar**:
   - Tombol badge di Title Bar (`self.btn_user`) menampilkan `[USR: @NAMA]` (cyan) atau `[TAMU: Sesi Tamu]` (amber).
   - Menekan tombol ini hanya membuka `UserProfileDialog` personal, bukan admin dashboard.

## Konsekuensi Positif
- Privasi seluruh pengguna Supabase terlindungi 100% tanpa adanya kebocoran data pengguna lain di software publik.
- Antarmuka software tetap profesional, bersih, dan fokus pada alur kerja pengguna masing-masing.
- Pengembang tetap memiliki kendali penuh atas database Supabase melalui portal resmi atau skrip CLI admin privat.
