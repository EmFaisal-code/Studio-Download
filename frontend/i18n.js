// Studio Download - Internationalization (i18n) Engine (ID / EN)

const i18nData = {
  id: {
    // Brand & Header
    brand_title: 'Studio Download',
    brand_version: 'v1.0',
    made_by: 'Dibuat oleh',
    support_creator: 'Dukung di Sociabuzz',
    check_updates: 'Cek Update',
    engine_ready: 'Engine Siap',
    engine_connecting: 'Menghubungkan...',
    engine_offline: 'Engine Offline',
    nav_folder: 'Folder',
    nav_folder_title: 'Buka Folder Unduhan',
    nav_settings: 'Pengaturan',
    nav_settings_title: 'Pengaturan',
    nav_lang_title: 'Ganti Bahasa (ID / EN)',
    lang_badge: '🇮🇩 ID',

    // Hero Section
    hero_eyebrow: 'YouTube 4K 60fps Media Extractor',
    hero_title: 'Studio',
    hero_title_accent: 'Download',
    hero_desc: 'Engine ekstraksi media YouTube hingga <strong>4K 60fps</strong> (VP9 / H.264) dan audio <strong>AAC 44.1kHz / MP3 320kbps</strong>. Output format universal & kompatibel dengan berbagai software video editor (NLE) serta media player tanpa black screen.',
    pill_4k: '4K 60fps & HDR',
    pill_lossless: 'Audio Lossless 320kbps',
    pill_nle: 'Universal Video Editor Ready',
    pill_bot: 'Bypass Bot Shield',

    // Input Bar
    url_placeholder: 'Tempel tautan YouTube atau link streaming (HLS .m3u8, web video)...',
    paste_btn: 'Tempel',
    paste_btn_title: 'Tempel dari Clipboard',
    analyze_btn: 'Analisis Video',
    analyzing_btn: 'Menganalisis...',
    url_ready_text: 'YouTube & Web Stream Ready',
    header_referer_btn: '⚙ Header / Referer (Opsional) ▾',
    referer_placeholder: 'Referer URL (Opsional, gunakan jika website memblokir dengan 403 Forbidden)...',

    // Analysis / Format Card
    manifest_title: 'Pilihan Format Unduhan',
    status_ready_dl: '● Siap Diunduh',
    custom_title_placeholder: 'Nama file video...',
    custom_title_title: 'Klik untuk mengubah nama file sebelum mengunduh',
    filename_hint: '✏ Nama file dapat diedit langsung sebelum diunduh',
    channel_label: 'Kanal:',
    views_label: 'Penonton:',
    tab_video: 'Video (+ Audio)',
    tab_audio: 'Audio Saja',
    tab_video_sub: 'Unduh video full resolusi dengan audio stereo sinkron',
    tab_audio_sub: 'Ekstrak audio murni (MP3, AAC, M4A, FLAC, WAV, OPUS)',
    format_options_title: 'Format Kontainer & Codec NLE',
    container_label: 'Format Kontainer Video:',
    codec_label: 'Transcode Codec (Kompatibilitas NLE):',
    audio_container_label: 'Format Ekstrak Audio:',
    audio_bitrate_label: 'Preset Kualitas Bitrate:',
    start_download_btn: 'Mulai Unduh',
    start_download_audio_btn: 'Ekstrak & Unduh Audio',
    preparing_dl: 'Menyiapkan...',

    // Tasks Section
    active_tasks_title: 'TUGAS AKTIF',
    status_downloading: 'Mengunduh',
    status_merging: 'Memproses / Menggabungkan',
    status_completed: 'Selesai',
    status_failed: 'Gagal',
    speed_lbl: 'Kecepatan:',
    eta_lbl: 'Sisa Waktu:',
    pause_btn: 'Jeda',
    resume_btn: 'Lanjut',
    cancel_btn: 'Batal',

    // History Section
    history_title: 'Riwayat Unduhan',
    history_empty: 'Belum ada riwayat unduhan.',
    sort_by: 'Urutkan:',
    clear_history_btn: 'Bersihkan Riwayat',
    open_file: 'Buka File',
    open_folder: 'Buka Folder',
    delete_history: 'Hapus',
    sort_date_added: 'Tanggal Ditambahkan',
    sort_date_updated: 'Tanggal Diperbarui',
    sort_title: 'Judul',
    sort_duration: 'Durasi',
    sort_filesize: 'Ukuran File',
    sort_bitrate: 'Bitrate',

    // Settings Modal
    settings_title: 'Pengaturan Studio Download',
    tab_general: 'Umum & Unduhan',
    tab_auth: 'Autentikasi YouTube',
    tab_appearance: 'Tampilan & Bahasa',
    download_dir_label: 'Direktori Penyimpanan Unduhan:',
    open_dir_btn: 'Pilih',
    max_concurrent_label: 'Maksimal Unduhan Bersamaan:',
    speed_limit_label: 'Batas Kecepatan Bandwidth:',
    theme_label: 'Tema Tampilan Aplikasi:',
    language_label: 'Bahasa Antarmuka (Language):',
    save_settings_btn: 'Simpan Pengaturan',
    cancel_settings_btn: 'Batal',
    auth_cookies_label: 'Autentikasi YouTube (Anti Bot):',
    auth_guide_title: 'Sinkronisasi Otomatis Cookies YouTube (1-Klik):',
    cookie_guide_step1: 'Pasang ekstensi <strong>Studio Download Companion</strong> di browser Anda (buka tab Ekstensi Browser).',
    cookie_guide_step2: 'Buka tab <strong>YouTube</strong> di browser Anda, lalu klik ikon ekstensi Studio Download di toolbar (atau klik kanan &gt; <strong>"Sinkronkan Cookies YouTube"</strong>).',
    cookie_guide_step3: 'Cookies YouTube otomatis terpasang &amp; aktif di aplikasi. Tanpa perlu download file atau install ekstensi lain!',
    cookie_manual_hint: 'Atau tempel manual teks cookies.txt jika diperlukan:',
    cookies_placeholder: 'Tempel teks cookies di sini (# Netscape HTTP Cookie File...)',
    save_cookies_btn: 'Simpan File Cookies',
    delete_cookies_confirm: 'Yakin ingin menghapus file cookies.txt?',
    cookie_guide_info: 'Catatan: Chrome terbaru memproteksi database akun (DPAPI). Disarankan memakai opsi file cookies.txt di bawah.',

    // Browser Extension Tab in Settings
    tab_extension: 'Ekstensi Browser',
    ext_heading: 'Ekstensi Browser Companion (Chrome / Edge / Brave):',
    ext_subheading: 'Tangkap link video streaming langsung dari tab browser aktif dan kirimkan otomatis ke Studio Download.',
    open_ext_folder_btn: 'Buka Folder Ekstensi',
    copy_path_btn: 'Salin Path',
    ext_guide_title: 'Panduan Pemasangan Ekstensi di Chrome / Edge / Brave:',

    // Who Are You (User Onboarding) & Admin Dashboard
    who_are_you_title: 'Who are you?',
    who_are_you_subtitle: 'Selamat datang di Studio Download! Silakan masukkan nama Anda untuk memulai sesi.',
    username_label: 'Nama / Username:',
    username_placeholder: 'Contoh: Alex, @editor_pro, @em.n.ef...',
    role_label: 'Profesi / Kategori:',
    contact_label: 'Kontak / Sosial Media (Opsional):',
    contact_placeholder: 'TikTok / Instagram / Email (Opsional)...',
    start_app_btn: 'Mulai Menggunakan Studio Download',
    user_badge_title: 'Profil Pengguna & Statistik',
    admin_title: 'Admin Dashboard Pengguna',
    total_users_lbl: 'Total Pengguna Terdaftar:',
    user_id_lbl: 'ID Pengguna:',

    // Confirmation Modal
    confirm_title: 'Konfirmasi Hapus Unduhan',
    confirm_delete_both_label: 'Hapus juga file fisik dari penyimpanan komputer',
    confirm_delete_both_desc: 'File video/audio asli di hard disk akan ikut dihapus secara permanen.',
    confirm_file_missing: 'Catatan: File fisik di disk sudah tidak ditemukan.',
    confirm_btn_delete: 'Hapus',
    confirm_btn_cancel: 'Batal',

    // Toast Messages
    toast_url_empty: 'Silakan masukkan tautan video YouTube atau stream terlebih dahulu.',
    toast_analyzing: 'Menganalisis informasi media...',
    toast_stream_received: '⚡ Aliran stream diterima dari ekstensi!',
    toast_download_started: 'Tugas unduhan telah ditambahkan!',
    toast_download_completed: 'Unduhan selesai!',
    toast_download_failed: 'Unduhan gagal.',
    toast_settings_saved: 'Pengaturan berhasil disimpan!',
    toast_cookies_saved: 'File cookies berhasil disimpan!',
    toast_cookies_deleted: 'File cookies telah dihapus.',
    toast_history_cleared: 'Riwayat unduhan berhasil dibersihkan.',
    toast_clipboard_empty: 'Clipboard tidak berisi teks atau URL valid.',
    toast_folder_opened: 'Membuka folder unduhan...',

    // Announcement & Updates
    close_announcement_title: 'Tutup Pengumuman',
    update_modal_title: 'Pembaruan Studio Download',
    update_checking_text: 'Memeriksa status pembaruan ke server...',
    update_close_btn: 'Tutup',
    update_download_btn: 'Unduh Pembaruan →',
    update_available_title: 'Pembaruan Tersedia!',
    update_mandatory_title: 'Pembaruan Wajib Tersedia',
    update_latest_title: 'Aplikasi Sudah Versi Terbaru',
    update_latest_desc: 'Anda menggunakan versi paling mutakhir dari Studio Download.',
    update_default_notes: 'Peningkatan performa ekstraksi video & penyempurnaan UI.'
  },

  en: {
    // Brand & Header
    brand_title: 'Studio Download',
    brand_version: 'v1.0',
    made_by: 'Made by',
    support_creator: 'Support on Sociabuzz',
    check_updates: 'Check Updates',
    engine_ready: 'Engine Ready',
    engine_connecting: 'Connecting...',
    engine_offline: 'Engine Offline',
    nav_folder: 'Folder',
    nav_folder_title: 'Open Download Folder',
    nav_settings: 'Settings',
    nav_settings_title: 'Settings',
    nav_lang_title: 'Switch Language (EN / ID)',
    lang_badge: '🇺🇸 EN',

    // Hero Section
    hero_eyebrow: 'YouTube 4K 60fps Media Extractor',
    hero_title: 'Studio',
    hero_title_accent: 'Download',
    hero_desc: 'High-fidelity YouTube extraction engine supporting up to <strong>4K 60fps</strong> (VP9 / H.264) and audio <strong>AAC 44.1kHz / MP3 320kbps</strong>. Universal output compatible with all major video editors (NLE) and media players without black screen.',
    pill_4k: '4K 60fps & HDR',
    pill_lossless: 'Audio Lossless 320kbps',
    pill_nle: 'Universal Video Editor Ready',
    pill_bot: 'Bypass Bot Shield',

    // Input Bar
    url_placeholder: 'Paste YouTube link or streaming URL (HLS .m3u8, web video)...',
    paste_btn: 'Paste',
    paste_btn_title: 'Paste from Clipboard',
    analyze_btn: 'Analyze Video',
    analyzing_btn: 'Analyzing...',
    url_ready_text: 'YouTube & Web Stream Ready',
    header_referer_btn: '⚙ Header / Referer (Optional) ▾',
    referer_placeholder: 'Referer URL (Optional, use if website blocks with 403 Forbidden)...',

    // Analysis / Format Card
    manifest_title: 'Download Format Selection',
    status_ready_dl: '● Ready to Download',
    custom_title_placeholder: 'Video filename...',
    custom_title_title: 'Click to edit filename before downloading',
    filename_hint: '✏ Filename can be edited directly before download',
    channel_label: 'Channel:',
    views_label: 'Views:',
    tab_video: 'Video (+ Audio)',
    tab_audio: 'Audio Only',
    tab_video_sub: 'Download full resolution video with synced stereo audio',
    tab_audio_sub: 'Extract pure audio (MP3, AAC, M4A, FLAC, WAV, OPUS)',
    format_options_title: 'Container Format & NLE Codec',
    container_label: 'Video Container Format:',
    codec_label: 'Transcode Codec (NLE Compatibility):',
    audio_container_label: 'Audio Extract Format:',
    audio_bitrate_label: 'Bitrate Quality Preset:',
    start_download_btn: 'Start Download',
    start_download_audio_btn: 'Extract & Download Audio',
    preparing_dl: 'Preparing...',

    // Tasks Section
    active_tasks_title: 'ACTIVE TASKS',
    status_downloading: 'Downloading',
    status_merging: 'Processing / Merging',
    status_completed: 'Completed',
    status_failed: 'Failed',
    speed_lbl: 'Speed:',
    eta_lbl: 'ETA:',
    pause_btn: 'Pause',
    resume_btn: 'Resume',
    cancel_btn: 'Cancel',

    // History Section
    history_title: 'Download History',
    history_empty: 'No download history yet.',
    sort_by: 'Sort by:',
    clear_history_btn: 'Clear History',
    open_file: 'Open File',
    open_folder: 'Open Folder',
    delete_history: 'Delete',
    sort_date_added: 'Date Added',
    sort_date_updated: 'Date Updated',
    sort_title: 'Title',
    sort_duration: 'Duration',
    sort_filesize: 'File Size',
    sort_bitrate: 'Bitrate',

    // Settings Modal
    settings_title: 'Studio Download Settings',
    tab_general: 'General & Downloads',
    tab_auth: 'YouTube Authentication',
    tab_appearance: 'Appearance & Language',
    download_dir_label: 'Download Storage Directory:',
    open_dir_btn: 'Browse',
    max_concurrent_label: 'Max Concurrent Downloads:',
    speed_limit_label: 'Bandwidth Speed Limit:',
    theme_label: 'Application Theme:',
    language_label: 'Interface Language (Bahasa):',
    save_settings_btn: 'Save Settings',
    cancel_settings_btn: 'Cancel',
    auth_cookies_label: 'YouTube Authentication (Anti-Bot):',
    auth_guide_title: 'Automatic YouTube Cookie Sync (1-Click):',
    cookie_guide_step1: 'Install the <strong>Studio Download Companion</strong> extension in your browser (check Browser Extension tab).',
    cookie_guide_step2: 'Open any <strong>YouTube</strong> tab, then click the Studio Download icon in toolbar (or right-click &gt; <strong>"Sync YouTube Cookies"</strong>).',
    cookie_guide_step3: 'YouTube cookies will be automatically installed &amp; active in the app. No need to download files or install other extensions!',
    cookie_manual_hint: 'Or manually paste cookies.txt text if needed:',
    cookies_placeholder: 'Paste cookies text here (# Netscape HTTP Cookie File...)',
    save_cookies_btn: 'Save Cookies File',
    delete_cookies_confirm: 'Are you sure you want to delete the cookies.txt file?',
    cookie_guide_info: 'Note: Modern Chrome protects account DB (DPAPI). It is recommended to use the cookies.txt option below.',

    // Browser Extension Tab in Settings
    tab_extension: 'Browser Extension',
    ext_heading: 'Companion Browser Extension (Chrome / Edge / Brave):',
    ext_subheading: 'Capture live video stream links directly from active browser tabs and forward them automatically to Studio Download.',
    open_ext_folder_btn: 'Open Extension Folder',
    copy_path_btn: 'Copy Path',
    ext_guide_title: 'Installation Guide for Chrome / Edge / Brave:',

    // Who Are You (User Onboarding) & Admin Dashboard
    who_are_you_title: 'Who are you?',
    who_are_you_subtitle: 'Welcome to Studio Download! Please enter your name or handle to begin.',
    username_label: 'Name / Username:',
    username_placeholder: 'e.g. Alex, @editor_pro, @em.n.ef...',
    role_label: 'Profession / Category:',
    contact_label: 'Contact / Social (Optional):',
    contact_placeholder: 'TikTok / Instagram / Email (Optional)...',
    start_app_btn: 'Launch Studio Download',
    user_badge_title: 'User Profile & Statistics',
    admin_title: 'User Admin Dashboard',
    total_users_lbl: 'Total Registered Users:',
    user_id_lbl: 'User ID:',

    // Confirmation Modal
    confirm_title: 'Confirm Download Deletion',
    confirm_delete_both_label: 'Also delete physical file from computer storage',
    confirm_delete_both_desc: 'The original video/audio file on hard drive will be permanently removed.',
    confirm_file_missing: 'Note: Physical file on disk is already missing.',
    confirm_btn_delete: 'Delete',
    confirm_btn_cancel: 'Cancel',

    // Toast Messages
    toast_url_empty: 'Please enter a YouTube video or stream link first.',
    toast_analyzing: 'Analyzing media information...',
    toast_stream_received: '⚡ Stream received from browser extension!',
    toast_download_started: 'Download task has been queued!',
    toast_download_completed: 'Download completed!',
    toast_download_failed: 'Download failed.',
    toast_settings_saved: 'Settings saved successfully!',
    toast_cookies_saved: 'Cookies file saved successfully!',
    toast_cookies_deleted: 'Cookies file deleted.',
    toast_history_cleared: 'Download history cleared successfully.',
    toast_clipboard_empty: 'Clipboard does not contain valid text or URL.',
    toast_folder_opened: 'Opening download folder...',

    // Announcement & Updates
    close_announcement_title: 'Close Announcement',
    update_modal_title: 'Studio Download Updates',
    update_checking_text: 'Checking for updates on server...',
    update_close_btn: 'Close',
    update_download_btn: 'Download Update →',
    update_available_title: 'Update Available!',
    update_mandatory_title: 'Mandatory Update Available',
    update_latest_title: 'Software is Up to Date',
    update_latest_desc: 'You are running the latest version of Studio Download.',
    update_default_notes: 'Performance improvements and UI polish.'
  }
};

class I18nManager {
  constructor() {
    this.currentLang = localStorage.getItem('studio_download_lang') || 'id';
  }

  init() {
    this.applyLanguage(this.currentLang);
  }

  getLanguage() {
    return this.currentLang;
  }

  setLanguage(lang) {
    if (lang !== 'id' && lang !== 'en') return;
    this.currentLang = lang;
    localStorage.setItem('studio_download_lang', lang);
    this.applyLanguage(lang);

    // Sync to backend settings silently if available
    if (window.fetch) {
      fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: lang })
      }).catch(() => {});
    }
  }

  t(key, fallback = '') {
    const langDict = i18nData[this.currentLang] || i18nData['id'];
    return langDict[key] || fallback || key;
  }

  applyLanguage(lang) {
    this.currentLang = lang;
    localStorage.setItem('studio_download_lang', lang);
    const dict = i18nData[lang] || i18nData['id'];

    // 1. Text content / innerHTML via data-i18n
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (dict[key]) {
        el.innerHTML = dict[key];
      }
    });

    // 2. Titles via data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (dict[key]) {
        el.setAttribute('title', dict[key]);
      }
    });

    // 3. Placeholders via data-i18n-placeholder
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (dict[key]) {
        el.setAttribute('placeholder', dict[key]);
      }
    });

    // 4. Update Header Toggle Badge
    const langBadgeNormal = document.getElementById('langBadgeNormal');
    const langBadgeDev = document.getElementById('langBadgeDev');
    if (langBadgeNormal) {
      langBadgeNormal.textContent = lang === 'id' ? '🇮🇩 ID' : '🇺🇸 EN';
    }
    if (langBadgeDev) {
      langBadgeDev.textContent = `LANG:${lang.toUpperCase()}`;
    }

    // 5. Update settings select if present
    const langSelect = document.getElementById('languageSelect');
    if (langSelect && langSelect.value !== lang) {
      langSelect.value = lang;
    }

    // 6. Update document html lang attribute
    document.documentElement.lang = lang;

    // 7. Dispatch custom event for dynamic components (app.js)
    window.dispatchEvent(new CustomEvent('studio_language_changed', { detail: { language: lang } }));
  }
}

// Instantiate global singleton
window.i18n = new I18nManager();
