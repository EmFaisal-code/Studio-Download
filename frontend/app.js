// Studio Download - Frontend Controller (Developer / IDE Edition)

let currentVideoData = null;
let selectedVideoFormat = null;
let selectedAudioFormat = null;
let activeMode = 'video'; // 'video' or 'audio'
let ws = null;
let activeTasksMap = {};

// DOM Elements
const videoUrlInput = document.getElementById('videoUrlInput');
const pasteBtn = document.getElementById('pasteBtn');
const analyzeBtn = document.getElementById('analyzeBtn');
const analyzeSpinner = document.getElementById('analyzeSpinner');
const analysisCard = document.getElementById('analysisCard');

const videoThumb = document.getElementById('videoThumb');
const videoDuration = document.getElementById('videoDuration');
const videoTitle = document.getElementById('videoTitle');
const channelName = document.getElementById('channelName');
const viewsCount = document.getElementById('viewsCount');

const tabVideo = document.getElementById('tabVideo');
const tabAudio = document.getElementById('tabAudio');
const videoFormatsContainer = document.getElementById('videoFormatsContainer');
const audioFormatsContainer = document.getElementById('audioFormatsContainer');
const resolutionGrid = document.getElementById('resolutionGrid');
const audioGrid = document.getElementById('audioGrid');
const videoContainerSelect = document.getElementById('videoContainerSelect');
const videoCodecSelect = document.getElementById('videoCodecSelect');

const startDownloadBtn = document.getElementById('startDownloadBtn');
const tasksSection = document.getElementById('tasksSection');
const tasksList = document.getElementById('tasksList');
const historyList = document.getElementById('historyList');
const emptyHistoryMsg = document.getElementById('emptyHistoryMsg');
const clearHistoryBtn = document.getElementById('clearHistoryBtn');
const openFolderBtn = document.getElementById('openFolderBtn');

const settingsBtn = document.getElementById('settingsBtn');
const settingsModal = document.getElementById('settingsModal');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const downloadDirInput = document.getElementById('downloadDirInput');
const defaultFormatSelect = document.getElementById('defaultFormatSelect');
const openSettingsDirBtn = document.getElementById('openSettingsDirBtn');

const cookieSourceSelect = document.getElementById('cookieSourceSelect');
const cookieBrowserSelect = document.getElementById('cookieBrowserSelect');
const browserSelectRow = document.getElementById('browserSelectRow');
const cookieStatusTag = document.getElementById('cookieStatusTag');
const cookiePasteInput = document.getElementById('cookiePasteInput');
const saveCookiePasteBtn = document.getElementById('saveCookiePasteBtn');
const deleteCookieBtn = document.getElementById('deleteCookieBtn');
const themeSelect = document.getElementById('themeSelect');

const historySortBtn = document.getElementById('historySortBtn');
const historySortLabel = document.getElementById('historySortLabel');
const historyOrderBtn = document.getElementById('historyOrderBtn');
const historyOrderIcon = document.getElementById('historyOrderIcon');
const historySortDropdown = document.getElementById('historySortDropdown');
const maxConcurrentSelect = document.getElementById('maxConcurrentSelect');
const speedLimitSelect = document.getElementById('speedLimitSelect');

// Confirmation Modal Elements
const confirmModal = document.getElementById('confirmModal');
const confirmModalCloseBtn = document.getElementById('confirmModalCloseBtn');
const confirmCancelBtn = document.getElementById('confirmCancelBtn');
const confirmActionBtn = document.getElementById('confirmActionBtn');
const confirmModalTitle = document.getElementById('confirmModalTitle');
const confirmMainPrompt = document.getElementById('confirmMainPrompt');
const confirmSubPrompt = document.getElementById('confirmSubPrompt');
const confirmItemPreview = document.getElementById('confirmItemPreview');
const confirmItemThumb = document.getElementById('confirmItemThumb');
const confirmItemTitle = document.getElementById('confirmItemTitle');
const confirmItemMeta = document.getElementById('confirmItemMeta');
const confirmItemPath = document.getElementById('confirmItemPath');
const confirmOptionBox = document.getElementById('confirmOptionBox');
const confirmDeleteFileCheckbox = document.getElementById('confirmDeleteFileCheckbox');
const confirmOptTitle = document.getElementById('confirmOptTitle');
const confirmOptSub = document.getElementById('confirmOptSub');
const confirmFileMissingNotice = document.getElementById('confirmFileMissingNotice');
const confirmActionBtnDev = document.getElementById('confirmActionBtnDev');
const confirmActionBtnNormal = document.getElementById('confirmActionBtnNormal');
let confirmModalResolver = null;

let currentHistoryData = [];
let currentSortCriteria = localStorage.getItem('studio_history_sort') || 'date_added';
let currentSortOrder = localStorage.getItem('studio_history_order') || 'desc';

const sortLabels = {
  date_added: 'Date Added',
  date_updated: 'Date Updated',
  title: 'Title',
  duration: 'Duration',
  filesize: 'File Size',
  bitrate: 'Bitrate'
};

// Immediate theme application from localStorage to prevent flash
let initialSavedTheme = localStorage.getItem('studio_download_theme');
if (!initialSavedTheme || initialSavedTheme === 'cyber-yellow') {
  initialSavedTheme = 'modern-yellow';
} else if (initialSavedTheme === 'zinc') {
  initialSavedTheme = 'developer-zinc';
}
document.documentElement.setAttribute('data-theme', initialSavedTheme);
document.body && document.body.setAttribute('data-theme', initialSavedTheme);

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  loadHistory();
  loadSettings();
  setupEventListeners();

  // Check URL query parameters for stream auto-fill from extension
  try {
    const params = new URLSearchParams(window.location.search);
    const qUrl = params.get('url');
    const qTitle = params.get('title');
    const qRef = params.get('referer');
    const qCookie = params.get('cookie');
    const qUA = params.get('ua');

    if (qUrl) {
      window._streamTitle = qTitle || '';
      window._streamCookie = qCookie || '';
      window._streamUA = qUA || '';

      videoUrlInput.value = qUrl;
      videoUrlInput.dispatchEvent(new Event('input'));
      if (qRef) {
        const refInput = document.getElementById('streamRefererInput');
        const refGroup = document.getElementById('refererInputGroup');
        const toggleBtn = document.getElementById('toggleRefererBtn');
        if (refInput) refInput.value = qRef;
        if (refGroup) refGroup.style.display = 'block';
        if (toggleBtn) {
          const sp = toggleBtn.querySelector('span');
          if (sp) sp.textContent = '⚙ Header / Referer (Aktif) ▴';
        }
      }
      // Auto-analyze stream after UI renders
      setTimeout(() => {
        analyzeVideo();
      }, 350);
    }
  } catch (e) {
    console.warn('Error parsing query params:', e);
  }
});

// --- Event Listeners ---
function setupEventListeners() {
  // Language Switcher Toggle (Header)
  const langToggleBtn = document.getElementById('langToggleBtn');
  if (langToggleBtn) {
    langToggleBtn.addEventListener('click', () => {
      if (window.i18n) {
        const nextLang = window.i18n.getLanguage() === 'id' ? 'en' : 'id';
        window.i18n.setLanguage(nextLang);
        showToast(nextLang === 'id' ? '🇮🇩 Bahasa diubah ke Bahasa Indonesia' : '🇺🇸 Language switched to English', 'info');
      }
    });
  }

  // Language Dropdown in Settings Modal
  const languageSelect = document.getElementById('languageSelect');
  if (languageSelect) {
    languageSelect.addEventListener('change', (e) => {
      if (window.i18n) {
        window.i18n.setLanguage(e.target.value);
        showToast(e.target.value === 'id' ? '🇮🇩 Bahasa diubah ke Bahasa Indonesia' : '🇺🇸 Language switched to English', 'info');
      }
    });
  }

  // Custom Event for Dynamic UI Re-translation
  window.addEventListener('studio_language_changed', () => {
    updateDynamicTranslations();
  });

  // Paste from clipboard
  pasteBtn.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        videoUrlInput.value = text.trim();
        showToast(window.i18n ? window.i18n.t('toast_stream_received', 'Tautan berhasil disalin dari clipboard.') : 'Tautan berhasil disalin dari clipboard.', 'success');
        analyzeVideo();
      }
    } catch (err) {
      showToast(window.i18n ? window.i18n.t('toast_clipboard_empty', 'Gagal membaca clipboard. Tempel manual dengan Ctrl+V.') : 'Gagal membaca clipboard. Tempel manual dengan Ctrl+V.', 'error');
    }
  });

  // Enter key in input
  videoUrlInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      analyzeVideo();
    }
  });

  // Dynamic stream & platform badge detection
  videoUrlInput.addEventListener('input', () => {
    const val = videoUrlInput.value.trim().toLowerCase();
    const urlTypeBadge = document.getElementById('urlTypeText');
    const urlTypeIcon = document.getElementById('urlTypeIcon');
    if (!urlTypeBadge) return;
    if (!val) {
      urlTypeBadge.textContent = 'YouTube & Web Stream Ready';
      urlTypeIcon.textContent = '▶';
    } else if (val.includes('youtube.com') || val.includes('youtu.be')) {
      urlTypeBadge.textContent = 'YouTube Platform Detected';
      urlTypeIcon.textContent = '🔴';
    } else if (val.includes('.m3u8') || val.includes('/hls/')) {
      urlTypeBadge.textContent = 'HLS M3U8 Stream Detected';
      urlTypeIcon.textContent = '⚡';
    } else if (val.includes('.mpd')) {
      urlTypeBadge.textContent = 'DASH MPD Stream Detected';
      urlTypeIcon.textContent = '⚡';
    } else {
      urlTypeBadge.textContent = 'Web Media / Generic Stream';
      urlTypeIcon.textContent = '🌐';
    }
  });

  // Toggle Referer / Custom Header input
  const toggleRefererBtn = document.getElementById('toggleRefererBtn');
  const refererInputGroup = document.getElementById('refererInputGroup');
  if (toggleRefererBtn && refererInputGroup) {
    toggleRefererBtn.addEventListener('click', () => {
      const isHidden = refererInputGroup.style.display === 'none';
      refererInputGroup.style.display = isHidden ? 'block' : 'none';
      toggleRefererBtn.querySelector('span').textContent = isHidden ? '⚙ Header / Referer (Aktif) ▴' : '⚙ Header / Referer (Opsional) ▾';
    });
  }

  // Analyze button
  analyzeBtn.addEventListener('click', analyzeVideo);

  // Mode Tabs
  tabVideo.addEventListener('click', () => setMode('video'));
  tabAudio.addEventListener('click', () => setMode('audio'));

  // Start Download
  startDownloadBtn.addEventListener('click', handleStartDownload);

  // Tasks Actions
  const clearTasksBtn = document.getElementById('clearTasksBtn');
  if (clearTasksBtn) {
    clearTasksBtn.addEventListener('click', clearTasks);
  }

  // History Actions
  clearHistoryBtn.addEventListener('click', handleClearHistory);
  openFolderBtn.addEventListener('click', () => openFolder());

  // History Sort Dropdown
  if (historySortBtn && historySortDropdown) {
    historySortBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const isVisible = historySortDropdown.style.display === 'flex';
      historySortDropdown.style.display = isVisible ? 'none' : 'flex';
      historySortBtn.classList.toggle('active', !isVisible);
      historySortBtn.setAttribute('aria-expanded', !isVisible);
    });

    document.addEventListener('click', (e) => {
      if (!e.target.closest('#historySortContainer')) {
        historySortDropdown.style.display = 'none';
        historySortBtn.classList.remove('active');
        historySortBtn.setAttribute('aria-expanded', 'false');
      }
    });

    const sortOptions = historySortDropdown.querySelectorAll('.sort-item');
    sortOptions.forEach(opt => {
      opt.addEventListener('click', (e) => {
        e.stopPropagation();
        const criteria = opt.getAttribute('data-sort');
        if (criteria) {
          setHistorySortCriteria(criteria);
        }
        historySortDropdown.style.display = 'none';
        historySortBtn.classList.remove('active');
        historySortBtn.setAttribute('aria-expanded', 'false');
      });
    });
  }

  // History Sort Order Toggle
  if (historyOrderBtn) {
    historyOrderBtn.addEventListener('click', () => {
      toggleHistoryOrder();
    });
  }

  // Settings Modal
  settingsBtn.addEventListener('click', () => openSettings('downloads'));
  closeSettingsBtn.addEventListener('click', closeSettings);
  cancelSettingsBtn.addEventListener('click', closeSettings);
  saveSettingsBtn.addEventListener('click', handleSaveSettings);
  openSettingsDirBtn.addEventListener('click', () => openFolder(downloadDirInput.value));

  // Settings Tab Navigation
  document.querySelectorAll('.settings-nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab');
      if (target) {
        switchSettingsTab(target);
      }
    });
  });

  // Cookie Settings
  if (cookieSourceSelect) {
    cookieSourceSelect.addEventListener('change', () => {
      if (browserSelectRow) {
        browserSelectRow.style.display = (cookieSourceSelect.value === 'browser') ? 'block' : 'none';
      }
    });
  }
  if (saveCookiePasteBtn) {
    saveCookiePasteBtn.addEventListener('click', handleSaveCookiePaste);
  }
  if (deleteCookieBtn) {
    deleteCookieBtn.addEventListener('click', handleDeleteCookies);
  }

  // Theme Switcher (Live Preview)
  if (themeSelect) {
    themeSelect.addEventListener('change', () => {
      applyTheme(themeSelect.value, true);
    });
  }

  // Confirmation Modal Listeners
  if (confirmModalCloseBtn) {
    confirmModalCloseBtn.addEventListener('click', () => closeConfirmModal(false));
  }
  if (confirmCancelBtn) {
    confirmCancelBtn.addEventListener('click', () => closeConfirmModal(false));
  }
  if (confirmActionBtn) {
    confirmActionBtn.addEventListener('click', () => closeConfirmModal(true));
  }
  if (confirmModal) {
    confirmModal.addEventListener('click', (e) => {
      if (e.target === confirmModal) {
        closeConfirmModal(false);
      }
    });
  }

  // Global ESC key listener for modals
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (confirmModal && confirmModal.style.display === 'flex') {
        closeConfirmModal(false);
      } else if (settingsModal && settingsModal.style.display === 'flex') {
        closeSettings();
      }
    }
  });
}

// --- WebSocket Setup ---
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/progress`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[IPC] WebSocket connected to Studio Download engine');
    const statusEl = document.getElementById('engineStatusText');
    if (statusEl) {
      statusEl.textContent = 'READY_200';
      statusEl.className = 'c-val c-val-ok';
    }
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'init') {
        activeTasksMap = msg.tasks || {};
        renderTasks();
      } else if (msg.type === 'progress') {
        activeTasksMap[msg.task_id] = msg.data;
        renderTasks();

        if (msg.data.status === 'completed') {
          showToast(`Unduhan selesai: ${msg.data.title}`, 'success');
          loadHistory();
        } else if (msg.data.status === 'error') {
          showToast(`Unduhan gagal: ${msg.data.error || 'Terjadi kesalahan'}`, 'error');
          loadHistory();
        }
      } else if (msg.type === 'remote_stream') {
        videoUrlInput.value = msg.url;
        videoUrlInput.dispatchEvent(new Event('input'));
        if (msg.referer) {
          const refInput = document.getElementById('streamRefererInput');
          const refGroup = document.getElementById('refererInputGroup');
          const toggleBtn = document.getElementById('toggleRefererBtn');
          if (refInput) refInput.value = msg.referer;
          if (refGroup) refGroup.style.display = 'block';
          if (toggleBtn) {
            const sp = toggleBtn.querySelector('span');
            if (sp) sp.textContent = '⚙ Header / Referer (Aktif) ▴';
          }
        }
        window._streamTitle = msg.title || '';
        window._streamCookie = msg.cookie || '';
        window._streamUA = msg.user_agent || '';
        showToast(`Menerima stream dari browser: ${msg.title || 'Video'}`, 'info');
        analyzeVideo();
      }
    } catch (e) {
      console.error('[IPC] Error parsing WS message:', e);
    }
  };

  ws.onclose = () => {
    console.warn('[IPC] WebSocket disconnected, retrying in 3s...');
    const statusEl = document.getElementById('engineStatusText');
    if (statusEl) {
      statusEl.textContent = 'RETRY_503';
      statusEl.className = 'c-val c-val-cyan';
    }
    setTimeout(initWebSocket, 3000);
  };

  ws.onerror = (err) => {
    console.error('[IPC] WebSocket error:', err);
  };
}

// --- Mode Switching ---
function setMode(mode) {
  activeMode = mode;
  if (mode === 'video') {
    tabVideo.classList.add('active');
    tabAudio.classList.remove('active');
    videoFormatsContainer.style.display = 'block';
    audioFormatsContainer.style.display = 'none';
  } else {
    tabAudio.classList.add('active');
    tabVideo.classList.remove('active');
    videoFormatsContainer.style.display = 'none';
    audioFormatsContainer.style.display = 'block';
  }
}

// --- Analyze Video URL ---
async function analyzeVideo() {
  const url = videoUrlInput.value.trim();
  if (!url) {
    showToast('Masukkan tautan video YouTube terlebih dahulu.', 'error');
    return;
  }

  // Loading state
  analyzeBtn.disabled = true;
  analyzeSpinner.style.display = 'block';
  const btnDev = analyzeBtn.querySelector('.lbl-dev');
  const btnNormal = analyzeBtn.querySelector('.lbl-normal');
  if (btnDev) btnDev.textContent = 'INGESTING...';
  if (btnNormal) btnNormal.textContent = 'Menganalisis...';

  try {
    const refererInput = document.getElementById('streamRefererInput');
    const parsePayload = { 
      url,
      title: window._streamTitle || undefined,
      cookie: window._streamCookie || undefined,
      user_agent: window._streamUA || undefined
    };
    if (refererInput && refererInput.value.trim()) {
      parsePayload.referer = refererInput.value.trim();
    }

    const res = await fetch('/api/parse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsePayload)
    });

    const data = await res.json();
    if (!res.ok) {
      if (res.status === 403 || (data.detail && data.detail.includes('BOT_CHECK_REQUIRED'))) {
        showToast('YouTube mewajibkan autentikasi (Bot Check). Buka menu CONFIG untuk menghubungkan cookies.', 'error');
        openSettings('auth');
        setTimeout(() => {
          const cg = document.getElementById('cookieSettingGroup');
          if (cg) {
            cg.scrollIntoView({ behavior: 'smooth' });
            cg.style.outline = '1px solid var(--accent-danger)';
            setTimeout(() => cg.style.outline = 'none', 3000);
          }
        }, 250);
        return;
      }
      throw new Error(data.detail || 'Gagal menganalisis link YouTube.');
    }

    currentVideoData = data;
    renderAnalysisResult(data);
    showToast('Manifest stream berhasil diekstrak!', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    analyzeBtn.disabled = false;
    analyzeSpinner.style.display = 'none';
    if (btnDev) btnDev.textContent = 'RUN_ANALYZE()';
    if (btnNormal) btnNormal.textContent = 'Analisis Video';
  }
}

// --- Render Analysis Result ---
function renderAnalysisResult(info) {
  videoThumb.src = info.thumbnail;
  videoDuration.textContent = info.duration;
  videoTitle.textContent = info.title;
  const customTitleInput = document.getElementById('customTitleInput');
  if (customTitleInput) {
    customTitleInput.value = info.title;
  }
  channelName.textContent = info.uploader;
  viewsCount.textContent = info.views;

  // Render Video Resolutions
  resolutionGrid.innerHTML = '';
  selectedVideoFormat = null;

  if (info.resolutions && info.resolutions.length > 0) {
    info.resolutions.forEach((res, idx) => {
      const card = document.createElement('div');
      card.className = `format-card ${idx === 0 ? 'selected' : ''}`;

      card.innerHTML = `
        <div class="format-header mono">
          <span class="format-num dev-only">#0${idx + 1}</span>
          <span class="format-res">${res.label}</span>
        </div>
        <div class="format-code-body mono">
          <div class="format-row">
            <span class="c-key"><span class="lbl-dev">FPS:</span><span class="lbl-normal">Kecepatan:</span></span>
            <span class="c-val">${res.fps} fps</span>
          </div>
          <div class="format-row">
            <span class="c-key"><span class="lbl-dev">CODEC:</span><span class="lbl-normal">Format:</span></span>
            <span class="c-val">${res.codec || 'VP9'}</span>
          </div>
        </div>
        <div class="format-footer mono">
          <span class="c-size">~${res.filesize_formatted}</span>
          <span class="c-tag">
            <span class="lbl-dev">[SELECT]</span>
            <span class="lbl-normal">Pilih</span>
          </span>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('#resolutionGrid .format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedVideoFormat = res;
      });

      if (idx === 0) selectedVideoFormat = res;
      resolutionGrid.appendChild(card);
    });
  } else {
    resolutionGrid.innerHTML = `
      <p class="mono" style="color:var(--text-muted); font-size:0.8rem;">
        <span class="lbl-dev">// Format otomatis akan diterapkan.</span>
        <span class="lbl-normal">Format terbaik akan dipilih secara otomatis.</span>
      </p>
    `;
  }

  // Render Audio Presets
  audioGrid.innerHTML = '';
  selectedAudioFormat = null;

  if (info.audio_presets && info.audio_presets.length > 0) {
    info.audio_presets.forEach((audio, idx) => {
      const card = document.createElement('div');
      card.className = `format-card ${idx === 0 ? 'selected' : ''}`;

      card.innerHTML = `
        <div class="format-header mono">
          <span class="format-num dev-only">#0${idx + 1}</span>
          <span class="format-res">${audio.label}</span>
        </div>
        <div class="format-code-body mono">
          <div class="format-row">
            <span class="c-key"><span class="lbl-dev">PROFILE:</span><span class="lbl-normal">Kualitas:</span></span>
            <span class="c-val">${audio.badge}</span>
          </div>
          <div class="format-row">
            <span class="c-key"><span class="lbl-dev">BITRATE:</span><span class="lbl-normal">Bitrate:</span></span>
            <span class="c-val">${audio.quality} kbps</span>
          </div>
        </div>
        <div class="format-footer mono">
          <span class="c-size">~${audio.filesize_formatted}</span>
          <span class="c-tag">
            <span class="lbl-dev">[AUDIO]</span>
            <span class="lbl-normal">Audio</span>
          </span>
        </div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('#audioGrid .format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        selectedAudioFormat = audio;
      });

      if (idx === 0) selectedAudioFormat = audio;
      audioGrid.appendChild(card);
    });
  }

  analysisCard.style.display = 'block';
  analysisCard.scrollIntoView({ behavior: 'smooth' });
}

// --- Start Download ---
async function handleStartDownload() {
  if (!currentVideoData) {
    showToast('Silakan analisis video terlebih dahulu.', 'error');
    return;
  }

  const customTitleInput = document.getElementById('customTitleInput');
  const finalTitle = (customTitleInput && customTitleInput.value.trim()) || currentVideoData.title;

  const payload = {
    url: currentVideoData.webpage_url || videoUrlInput.value.trim(),
    title: finalTitle,
    thumbnail: currentVideoData.thumbnail,
    duration: currentVideoData.duration || '--',
    duration_seconds: currentVideoData.duration_seconds || 0,
    mode: activeMode
  };

  if (activeMode === 'video') {
    payload.height = selectedVideoFormat ? selectedVideoFormat.height : null;
    payload.format = videoContainerSelect.value || 'mkv';
    payload.codec_preference = videoCodecSelect ? videoCodecSelect.value : 'compatible';
    payload.filesize_approx = selectedVideoFormat ? selectedVideoFormat.filesize_formatted : '';
    payload.bitrate = selectedVideoFormat ? (selectedVideoFormat.tbr ? `${Math.round(selectedVideoFormat.tbr)} kbps` : `${selectedVideoFormat.height}p`) : '';
    if (selectedVideoFormat && selectedVideoFormat.format_id) {
      payload.format_id = selectedVideoFormat.format_id;
    }
  } else {
    payload.format = selectedAudioFormat ? selectedAudioFormat.format : 'mp3';
    payload.audio_quality = selectedAudioFormat ? selectedAudioFormat.quality : '320';
    payload.filesize_approx = selectedAudioFormat ? selectedAudioFormat.filesize_formatted : '';
    payload.bitrate = selectedAudioFormat ? `${selectedAudioFormat.quality} kbps` : '320 kbps';
  }

  const refererInput = document.getElementById('streamRefererInput');
  if (refererInput && refererInput.value.trim()) {
    payload.referer = refererInput.value.trim();
  }
  if (window._streamCookie) {
    payload.cookie = window._streamCookie;
  }
  if (window._streamUA) {
    payload.user_agent = window._streamUA;
  }

  startDownloadBtn.disabled = true;

  try {
    const res = await fetch('/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Gagal memulai unduhan.');
    }

    showToast('Thread worker dimulai.', 'success');
    tasksSection.style.display = 'block';
    tasksSection.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    startDownloadBtn.disabled = false;
  }
}

// --- Render Tasks ---
function renderTasks() {
  const taskIds = Object.keys(activeTasksMap);
  if (taskIds.length === 0) {
    tasksSection.style.display = 'none';
    return;
  }

  tasksSection.style.display = 'block';
  tasksList.innerHTML = '';

  taskIds.forEach(id => {
    const task = activeTasksMap[id];
    const taskEl = document.createElement('div');
    taskEl.className = 'task-item';

    const isCompleted = task.status === 'completed';
    const isError = task.status === 'error';
    const isCancelled = task.status === 'cancelled';
    const isMuxing = task.status === 'muxing';
    const isQueued = task.status === 'queued';
    const isRunning = task.status === 'starting' || task.status === 'downloading' || isMuxing || isQueued;

    let statusText = `${task.progress}%`;
    let statusColor = 'var(--text-primary)';
    let progressFillBg = 'var(--accent-contrast)';

    if (isQueued) {
      statusText = '<span class="lbl-dev">QUEUED</span><span class="lbl-normal">Antrean</span>';
      statusColor = 'var(--syntax-num)';
      progressFillBg = 'var(--syntax-num)';
    } else if (isMuxing) {
      statusText = '<span class="lbl-dev">MUXING_FFMPEG</span><span class="lbl-normal">Menggabungkan Video...</span>';
      statusColor = 'var(--syntax-keyword)';
      progressFillBg = 'var(--syntax-keyword)';
    } else if (isCompleted) {
      statusText = '<span class="lbl-dev">COMPLETED</span><span class="lbl-normal">Selesai</span>';
      statusColor = 'var(--syntax-string)';
      progressFillBg = 'var(--syntax-string)';
    } else if (isCancelled) {
      statusText = '<span class="lbl-dev">ABORTED</span><span class="lbl-normal">Dibatalkan</span>';
      statusColor = 'var(--text-muted)';
      progressFillBg = 'var(--border-strong)';
    } else if (isError) {
      statusText = '<span class="lbl-dev">ERR_FAIL</span><span class="lbl-normal">Gagal</span>';
      statusColor = 'var(--accent-danger)';
      progressFillBg = 'var(--accent-danger)';
    }

    let actionButtons = '';
    if (isRunning) {
      actionButtons = `
        <button class="btn-action-small mono" style="color:var(--accent-danger); border-color: rgba(244,63,94,0.3)" onclick="cancelTask('${id}')">
          <span class="lbl-dev">ABORT</span>
          <span class="lbl-normal">Batal</span>
        </button>
      `;
    } else if (isCompleted && task.filepath) {
      actionButtons = `
        <button class="btn-action-small mono" onclick="openFile('${encodeURIComponent(task.filepath)}')">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          <span class="lbl-dev">PLAY</span>
          <span class="lbl-normal">Putar</span>
        </button>
        <button class="btn-action-small mono" onclick="openFolder('${encodeURIComponent(task.filepath)}')">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
          <span class="lbl-dev">DIR</span>
          <span class="lbl-normal">Folder</span>
        </button>
        <button class="btn-action-icon btn-action-delete" onclick="dismissTask('${id}')" title="Hapus dari antrean" aria-label="Tutup">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;
    } else {
      actionButtons = `
        <button class="btn-action-icon btn-action-delete" onclick="dismissTask('${id}')" title="Hapus" aria-label="Hapus">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;
    }

    taskEl.innerHTML = `
      <div class="task-top mono">
        <div class="task-title-wrapper">
          <span class="pid-badge">PID_${id.slice(-4).toUpperCase()}</span>
          <span class="task-badge">[${task.resolution || 'MEDIA'} • ${(task.format || '').toUpperCase()}]</span>
          <span class="task-title" title="${task.title}">${task.title}</span>
        </div>
        <div class="task-stats mono">
          <span class="c-speed">${task.speed || '0 KB/s'}</span>
          <span class="c-status" style="color: ${statusColor}">${statusText}</span>
        </div>
      </div>
      
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${task.progress || 0}%; background: ${progressFillBg}"></div>
      </div>

      <div class="task-bottom mono">
        <div>
          <span>${task.downloaded || '0 MB'} / ${task.total || '0 MB'}</span>
          <span style="margin-left: 12px; color: ${task.error ? 'var(--accent-danger)' : 'var(--text-muted)'}">
            ${task.error ? task.error : (task.eta ? ((task.eta.includes('YouTube') || task.eta.includes('FFmpeg') || task.eta.includes('antrean') || task.eta.includes('Dibatalkan') || task.eta.includes('Siap') || task.eta === '--') ? task.eta : 'ETA ' + task.eta) : '')}
          </span>
        </div>
        <div class="task-actions mono">
          ${actionButtons}
        </div>
      </div>
    `;

    tasksList.appendChild(taskEl);
  });
}

async function cancelTask(taskId) {
  try {
    await fetch(`/api/tasks/${taskId}/cancel`, { method: 'POST' });
    showToast('Mengirim sinyal SIGINT / Abort...', 'info');
  } catch (err) {
    showToast('Gagal membatalkan unduhan.', 'error');
  }
}

async function dismissTask(taskId) {
  try {
    await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
    delete activeTasksMap[taskId];
    renderTasks();
  } catch (err) {
    console.error(err);
  }
}

async function clearTasks() {
  try {
    await fetch('/api/tasks', { method: 'DELETE' });
    for (const tid in activeTasksMap) {
      if (['completed', 'error', 'cancelled'].includes(activeTasksMap[tid].status)) {
        delete activeTasksMap[tid];
      }
    }
    renderTasks();
    showToast('Thread yang selesai telah dibersihkan.', 'success');
  } catch (err) {
    console.error(err);
  }
}

// --- Download History Helpers & Sorting ---
function parseDurationSec(item) {
  if (item.duration_seconds && !isNaN(Number(item.duration_seconds))) {
    return Number(item.duration_seconds);
  }
  if (!item.duration || item.duration === '--') return 0;
  const parts = item.duration.split(':').map(Number);
  if (parts.length === 3) return (parts[0] || 0) * 3600 + (parts[1] || 0) * 60 + (parts[2] || 0);
  if (parts.length === 2) return (parts[0] || 0) * 60 + (parts[1] || 0);
  return 0;
}

function parseFilesizeBytes(item) {
  if (item.filesize_bytes && !isNaN(Number(item.filesize_bytes))) {
    return Number(item.filesize_bytes);
  }
  if (!item.total) return 0;
  const str = String(item.total).trim();
  const m = str.match(/([0-9.]+)\s*(B|KB|MB|GB|TB)/i);
  if (!m) return 0;
  const num = parseFloat(m[1]);
  const unit = m[2].toUpperCase();
  const mult = { B: 1, KB: 1024, MB: 1024 * 1024, GB: 1024 * 1024 * 1024, TB: 1024 * 1024 * 1024 * 1024 };
  return num * (mult[unit] || 1);
}

function parseBitrateNum(item) {
  const str = String(item.bitrate || item.resolution || '');
  const m = str.match(/([0-9.]+)/);
  return m ? parseFloat(m[1]) : 0;
}

function sortHistoryList(list, criteria, order) {
  const sorted = [...list];
  sorted.sort((a, b) => {
    let cmp = 0;
    if (criteria === 'date_added') {
      const timeA = a.created_at || a.id || '';
      const timeB = b.created_at || b.id || '';
      cmp = timeA.localeCompare(timeB);
    } else if (criteria === 'date_updated') {
      const timeA = a.updated_at || a.created_at || a.id || '';
      const timeB = b.updated_at || b.created_at || b.id || '';
      cmp = timeA.localeCompare(timeB);
    } else if (criteria === 'title') {
      const titleA = (a.title || '').toLowerCase();
      const titleB = (b.title || '').toLowerCase();
      cmp = titleA.localeCompare(titleB);
    } else if (criteria === 'duration') {
      cmp = parseDurationSec(a) - parseDurationSec(b);
    } else if (criteria === 'filesize') {
      cmp = parseFilesizeBytes(a) - parseFilesizeBytes(b);
    } else if (criteria === 'bitrate') {
      cmp = parseBitrateNum(a) - parseBitrateNum(b);
    }
    return order === 'asc' ? cmp : -cmp;
  });
  return sorted;
}

function updateSortDropdownUI() {
  if (historySortLabel) {
    const loc = window.i18n ? window.i18n.t('sort_' + currentSortCriteria) : null;
    historySortLabel.textContent = loc || sortLabels[currentSortCriteria] || 'Date Added';
  }
  if (historyOrderIcon) {
    historyOrderIcon.textContent = currentSortOrder === 'asc' ? '↑' : '↓';
    if (historyOrderBtn) {
      const isId = window.i18n ? window.i18n.getLanguage() === 'id' : true;
      historyOrderBtn.title = currentSortOrder === 'asc' 
        ? (isId ? 'Urutan: Menaik / A-Z / Terlama (Klik untuk Menurun)' : 'Order: Ascending / A-Z / Oldest (Click for Descending)')
        : (isId ? 'Urutan: Menurun / Z-A / Terbaru (Klik untuk Menaik)' : 'Order: Descending / Z-A / Newest (Click for Ascending)');
    }
  }
  if (historySortDropdown) {
    const items = historySortDropdown.querySelectorAll('.sort-item');
    items.forEach(el => {
      const criteria = el.getAttribute('data-sort');
      const match = criteria === currentSortCriteria;
      el.classList.toggle('active', match);
      const nameEl = el.querySelector('.sort-name');
      if (nameEl && criteria && window.i18n) {
        nameEl.textContent = window.i18n.t('sort_' + criteria);
      }
    });
  }
}

function updateDynamicTranslations() {
  updateSortDropdownUI();
  renderHistory();
  if (typeof renderTasks === 'function') {
    renderTasks();
  }
  const statusNormal = document.getElementById('engineStatusNormal');
  if (statusNormal && window.i18n) {
    statusNormal.innerHTML = `<span class="status-pulse-dot"></span>${window.i18n.t('engine_ready')}`;
  }
  const btnText = document.getElementById('startDownloadBtnText');
  if (btnText && window.i18n) {
    btnText.textContent = activeMode === 'video' ? window.i18n.t('start_download_btn') : window.i18n.t('start_download_audio_btn');
  }
}

function setHistorySortCriteria(criteria) {
  currentSortCriteria = criteria;
  localStorage.setItem('studio_history_sort', criteria);
  renderHistory();
}

function toggleHistoryOrder() {
  currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
  localStorage.setItem('studio_history_order', currentSortOrder);
  renderHistory();
}

function renderHistory() {
  updateSortDropdownUI();
  const historyCountBadge = document.getElementById('historyCountBadge');

  if (!currentHistoryData || currentHistoryData.length === 0) {
    emptyHistoryMsg.style.display = 'flex';
    historyList.innerHTML = '';
    historyList.appendChild(emptyHistoryMsg);
    if (historyCountBadge) historyCountBadge.style.display = 'none';
    return;
  }

  if (historyCountBadge) {
    historyCountBadge.textContent = `${currentHistoryData.length} File`;
    historyCountBadge.style.display = 'inline-flex';
  }

  emptyHistoryMsg.style.display = 'none';
  historyList.innerHTML = '';

  const sorted = sortHistoryList(currentHistoryData, currentSortCriteria, currentSortOrder);

  sorted.forEach((item) => {
    const el = document.createElement('div');
    el.className = 'history-item';

    const thumb = item.thumbnail || 'https://via.placeholder.com/160x90/18181b/ffffff?text=Video';

    const dateDisplay = (currentSortCriteria === 'date_updated' && item.updated_at)
      ? `Upd: ${item.updated_at}`
      : (item.created_at || '');

    const durDisplay = item.duration && item.duration !== '--' ? ` • ${item.duration}` : '';
    const bitrateDisplay = item.bitrate ? ` • ${item.bitrate}` : '';

    el.innerHTML = `
      <img class="history-thumb" src="${thumb}" alt="Thumbnail">
      <div class="history-details mono">
        <div class="history-title" title="${item.title}">${item.title}</div>
        <div class="history-meta">
          <span class="history-meta-tag">${item.resolution || 'MEDIA'} • ${(item.format || '').toUpperCase()}${bitrateDisplay}${durDisplay}</span>
          <span><span class="lbl-dev">//</span><span class="lbl-normal">•</span></span>
          <span class="c-num">${item.total || ''}</span>
          <span><span class="lbl-dev">//</span><span class="lbl-normal">•</span></span>
          <span>${dateDisplay}</span>
        </div>
      </div>
      <div class="history-actions mono">
        ${item.filepath ? `
          <button class="btn-action-small" onclick="openFile('${encodeURIComponent(item.filepath)}')">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
            <span class="lbl-dev">PLAY</span>
            <span class="lbl-normal">Putar</span>
          </button>
          <button class="btn-action-small" onclick="openFolder('${encodeURIComponent(item.filepath)}')">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>
            <span class="lbl-dev">DIR</span>
            <span class="lbl-normal">Folder</span>
          </button>
        ` : ''}
        <button class="btn-action-icon btn-action-delete" onclick="deleteHistory('${item.id}')" title="Hapus dari riwayat" aria-label="Hapus">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    `;

    historyList.appendChild(el);
  });
}

// --- Download History ---
async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const history = await res.json();
    currentHistoryData = history || [];
    renderHistory();
  } catch (err) {
    console.error('Failed to load history:', err);
  }
}

// --- Custom Studio Confirmation Dialog ---
function openConfirmModal({
  title = 'Konfirmasi Penghapusan',
  titleDev = 'confirm_action.sh',
  prompt = 'Hapus item dari riwayat unduhan?',
  subPrompt = 'Tindakan ini akan menghapus entri yang dipilih dari catatan riwayat aplikasi.',
  actionText = 'Hapus Entri',
  actionTextDev = 'CONFIRM_DELETE()',
  item = null,
  isBulk = false
}) {
  return new Promise((resolve) => {
    confirmModalResolver = resolve;

    if (confirmModalTitle) confirmModalTitle.textContent = title;
    if (confirmMainPrompt) confirmMainPrompt.textContent = prompt;
    if (confirmSubPrompt) confirmSubPrompt.textContent = subPrompt;
    if (confirmActionBtnNormal) confirmActionBtnNormal.textContent = actionText;
    if (confirmActionBtnDev) confirmActionBtnDev.textContent = actionTextDev;

    if (item) {
      // Single Item Mode
      confirmItemPreview.style.display = 'flex';
      confirmItemThumb.src = item.thumbnail || 'https://via.placeholder.com/160x90/18181b/ffffff?text=Video';
      confirmItemTitle.textContent = item.title || 'Media Video/Audio';
      
      const dur = item.duration && item.duration !== '--' ? ` • ${item.duration}` : '';
      confirmItemMeta.textContent = `${item.resolution || 'MEDIA'} • ${(item.format || '').toUpperCase()} • ${item.total || ''}${dur}`;
      confirmItemPath.textContent = item.filepath || '(Tidak ada path file tersimpan)';
      confirmItemPath.title = item.filepath || '';

      const hasFileOnDisk = Boolean(item.file_exists && item.filepath);
      if (hasFileOnDisk) {
        confirmOptionBox.style.display = 'block';
        confirmDeleteFileCheckbox.checked = true; // Checked by default so user can easily delete both
        confirmOptTitle.textContent = 'Hapus juga file fisik dari disk komputer';
        confirmOptSub.textContent = `File di "${item.filepath}" akan dihapus permanen dari penyimpanan.`;
        confirmFileMissingNotice.style.display = 'none';
      } else {
        confirmOptionBox.style.display = 'none';
        confirmDeleteFileCheckbox.checked = false;
        confirmFileMissingNotice.style.display = 'flex';
      }
    } else if (isBulk) {
      // Bulk Clear All Mode
      confirmItemPreview.style.display = 'none';
      confirmFileMissingNotice.style.display = 'none';
      confirmOptionBox.style.display = 'block';
      confirmDeleteFileCheckbox.checked = false; // Default unchecked for bulk to prevent accidental mass deletion
      confirmOptTitle.textContent = 'Hapus juga semua file fisik di folder unduhan';
      confirmOptSub.textContent = 'Semua file media dari daftar riwayat yang masih ada di disk akan ikut dihapus permanen.';
    } else {
      confirmItemPreview.style.display = 'none';
      confirmOptionBox.style.display = 'none';
      confirmFileMissingNotice.style.display = 'none';
      confirmDeleteFileCheckbox.checked = false;
    }

    confirmModal.style.display = 'flex';
  });
}

function closeConfirmModal(confirmed = false) {
  if (confirmModal) confirmModal.style.display = 'none';
  if (confirmModalResolver) {
    const deleteFile = Boolean(confirmDeleteFileCheckbox && confirmDeleteFileCheckbox.checked);
    confirmModalResolver({ confirmed, deleteFile });
    confirmModalResolver = null;
  }
}

async function deleteHistory(taskId) {
  const item = currentHistoryData.find(h => h.id === taskId);
  if (!item) return;

  const result = await openConfirmModal({
    title: 'Hapus Entri Riwayat',
    titleDev: 'delete_ledger_entry.sh',
    prompt: 'Hapus item ini dari riwayat unduhan?',
    subPrompt: 'Entri ini akan dihapus dari catatan riwayat aplikasi.',
    actionText: 'Hapus Entri',
    actionTextDev: 'CONFIRM_DELETE()',
    item: item,
    isBulk: false
  });

  if (!result || !result.confirmed) return;

  try {
    const query = result.deleteFile ? '?delete_file=true' : '';
    const res = await fetch(`/api/history/${taskId}${query}`, { method: 'DELETE' });
    const data = await res.json();
    loadHistory();
    if (data.file_deleted) {
      showToast('Entri riwayat dan file fisik di disk berhasil dihapus.', 'success');
    } else {
      showToast('Entri riwayat berhasil dihapus.', 'success');
    }
  } catch (err) {
    showToast('Gagal menghapus entri riwayat.', 'error');
  }
}

async function handleClearHistory() {
  if (!currentHistoryData || currentHistoryData.length === 0) {
    showToast('Riwayat unduhan sudah kosong.', 'info');
    return;
  }

  const result = await openConfirmModal({
    title: 'Bersihkan Semua Riwayat',
    titleDev: 'clear_all_ledger.sh',
    prompt: 'Hapus semua entri dalam ledger riwayat unduhan?',
    subPrompt: 'Pembersihan ini akan menghapus seluruh catatan riwayat unduhan di aplikasi.',
    actionText: 'Bersihkan Riwayat',
    actionTextDev: 'PURGE_ALL()',
    item: null,
    isBulk: true
  });

  if (!result || !result.confirmed) return;

  try {
    const query = result.deleteFile ? '?delete_files=true' : '';
    const res = await fetch(`/api/history${query}`, { method: 'DELETE' });
    const data = await res.json();
    loadHistory();
    if (data.deleted_files_count && data.deleted_files_count > 0) {
      showToast(`Seluruh riwayat & ${data.deleted_files_count} file fisik berhasil dibersihkan.`, 'success');
    } else {
      showToast('Seluruh entri riwayat berhasil dibersihkan.', 'success');
    }
  } catch (err) {
    showToast('Gagal membersihkan riwayat.', 'error');
  }
}

// --- File & Folder Operations ---
async function openFolder(path = null) {
  try {
    const payload = path ? { filepath: decodeURIComponent(path), directory: decodeURIComponent(path) } : {};
    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Gagal membuka folder.');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function openFile(encodedPath) {
  try {
    const filepath = decodeURIComponent(encodedPath);
    const res = await fetch('/api/open-file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filepath })
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Gagal memutar file.');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Settings & YouTube Auth Cookies ---
async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const settings = await res.json();
    if (settings.download_dir) {
      downloadDirInput.value = settings.download_dir;
    }
    if (settings.default_format) {
      defaultFormatSelect.value = settings.default_format;
    }
    if (cookieSourceSelect && settings.cookie_source) {
      cookieSourceSelect.value = settings.cookie_source;
      if (browserSelectRow) {
        browserSelectRow.style.display = (settings.cookie_source === 'browser') ? 'block' : 'none';
      }
    }
    if (cookieBrowserSelect && settings.cookie_browser) {
      cookieBrowserSelect.value = settings.cookie_browser;
    }
    if (settings.theme) {
      applyTheme(settings.theme, false);
    }
    if (maxConcurrentSelect && settings.max_concurrent_downloads !== undefined) {
      maxConcurrentSelect.value = String(settings.max_concurrent_downloads);
    }
    if (speedLimitSelect && settings.download_speed_limit !== undefined) {
      speedLimitSelect.value = String(settings.download_speed_limit);
    }
    if (settings.language && window.i18n) {
      window.i18n.applyLanguage(settings.language);
    }
    loadCookieStatus();
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

function switchSettingsTab(tabName) {
  const tabs = document.querySelectorAll('.settings-nav-tab');
  const contents = document.querySelectorAll('.settings-tab-content');

  tabs.forEach(t => {
    t.classList.toggle('active', t.getAttribute('data-tab') === tabName);
  });

  const tabIdMap = {
    downloads: 'tabContentDownloads',
    auth: 'tabContentAuth',
    appearance: 'tabContentAppearance'
  };

  contents.forEach(c => {
    const isTarget = c.id === tabIdMap[tabName];
    c.style.display = isTarget ? 'flex' : 'none';
  });
}

function openSettings(defaultTab = 'downloads') {
  loadSettings();
  loadCookieStatus();
  switchSettingsTab(defaultTab);
  settingsModal.style.display = 'flex';
}

function closeSettings() {
  settingsModal.style.display = 'none';
}

async function loadCookieStatus() {
  try {
    const res = await fetch('/api/cookies/status');
    if (!res.ok) return;
    const data = await res.json();
    if (cookieStatusTag) {
      if (data.has_cookie_file) {
        const sizeKb = (data.cookie_file_size / 1024).toFixed(1);
        cookieStatusTag.textContent = `[ACTIVE: cookies.txt (${sizeKb} KB)]`;
        cookieStatusTag.style.color = 'var(--syntax-string)';
        cookieStatusTag.style.borderColor = 'rgba(74, 222, 128, 0.4)';
      } else if (data.cookie_source === 'browser') {
        cookieStatusTag.textContent = `[BROWSER: ${data.cookie_browser.toUpperCase()}]`;
        cookieStatusTag.style.color = 'var(--syntax-func)';
        cookieStatusTag.style.borderColor = 'rgba(96, 165, 250, 0.4)';
      } else {
        cookieStatusTag.textContent = '[STATUS: UNLINKED / BOT DETECTABLE]';
        cookieStatusTag.style.color = 'var(--accent-danger)';
        cookieStatusTag.style.borderColor = 'rgba(244, 63, 94, 0.4)';
      }
    }
  } catch (err) {
    console.error('Failed to load cookie status:', err);
  }
}

async function handleSaveCookiePaste() {
  if (!cookiePasteInput) return;
  const content = cookiePasteInput.value.trim();
  if (!content) {
    showToast('Tempel isi cookies.txt terlebih dahulu ke dalam kolom teks.', 'error');
    return;
  }

  try {
    const res = await fetch('/api/cookies/paste', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content })
    });

    const data = await res.json();
    if (res.ok) {
      showToast('File cookies.txt berhasil disimpan! YouTube Bot Check berhasil diatasi.', 'success');
      cookiePasteInput.value = '';
      if (cookieSourceSelect) {
        cookieSourceSelect.value = 'auto';
        if (browserSelectRow) browserSelectRow.style.display = 'none';
      }
      loadCookieStatus();
    } else {
      showToast(data.detail || 'Gagal menyimpan cookies.', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDeleteCookies() {
  try {
    const res = await fetch('/api/cookies', { method: 'DELETE' });
    if (res.ok) {
      showToast('Cookies berhasil dihapus dari sistem.', 'info');
      if (cookieSourceSelect) {
        cookieSourceSelect.value = 'none';
        if (browserSelectRow) browserSelectRow.style.display = 'none';
      }
      loadCookieStatus();
    } else {
      showToast('Gagal menghapus cookies.', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleSaveSettings() {
  const dir = downloadDirInput.value.trim();
  const fmt = defaultFormatSelect.value;
  const cookieSource = cookieSourceSelect ? cookieSourceSelect.value : 'auto';
  const cookieBrowser = cookieBrowserSelect ? cookieBrowserSelect.value : 'chrome';
  const theme = themeSelect ? themeSelect.value : 'zinc';
  const languageSelect = document.getElementById('languageSelect');
  const selectedLang = languageSelect ? languageSelect.value : (window.i18n ? window.i18n.getLanguage() : 'id');
  const maxConcurrent = maxConcurrentSelect ? parseInt(maxConcurrentSelect.value, 10) : 2;
  const speedLimit = speedLimitSelect ? parseInt(speedLimitSelect.value, 10) : 0;

  try {
    const res = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        download_dir: dir,
        default_format: fmt,
        cookie_source: cookieSource,
        cookie_browser: cookieBrowser,
        theme: theme,
        language: selectedLang,
        max_concurrent_downloads: maxConcurrent,
        download_speed_limit: speedLimit
      })
    });

    if (res.ok) {
      applyTheme(theme, false);
      if (window.i18n) {
        window.i18n.setLanguage(selectedLang);
      }
      showToast(window.i18n ? window.i18n.t('toast_settings_saved', 'Konfigurasi engine berhasil disimpan.') : 'Konfigurasi engine berhasil disimpan.', 'success');
      closeSettings();
    } else {
      showToast('Gagal menyimpan pengaturan.', 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Theme Controller ---
function applyTheme(themeName, showToastFeedback = false) {
  let t = themeName || 'modern-yellow';
  if (t === 'cyber-yellow') t = 'modern-yellow';
  if (t === 'zinc') t = 'developer-zinc';

  document.documentElement.setAttribute('data-theme', t);
  if (document.body) {
    document.body.setAttribute('data-theme', t);
  }
  localStorage.setItem('studio_download_theme', t);
  if (themeSelect && themeSelect.value !== t) {
    themeSelect.value = t;
  }
  if (showToastFeedback) {
    const label = (t === 'modern-yellow') ? 'Studio Modern (Kuning)' : 'Developer Dark Zinc (Terminal)';
    showToast(`Tema aktif: ${label}`, 'info');
  }
}

// --- Toast Utility ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type} mono`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
