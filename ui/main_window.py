import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

from PySide6.QtCore import (
    Qt, QObject, Signal, QRunnable, QThreadPool, Slot, QUrl
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame, QGridLayout,
    QComboBox, QMessageBox, QApplication, QSizePolicy,
    QSystemTrayIcon, QMenu
)
from PySide6.QtGui import QPixmap, QIcon, QDesktopServices

from backend.config import get_settings, save_settings, get_app_dir, get_active_session_profile
from backend.i18n import t, get_current_lang
from backend.parser import (
    parse_url, format_bytes, format_duration, format_duration_hms,
    format_time_label, is_playlist_url, is_pure_playlist_url,
    is_video_in_playlist_url, extract_video_id, parse_playlist,
    normalize_youtube_url
)
from backend.downloader import download_manager, active_tasks
from backend.history import get_history

from ui.styles import get_theme_qss
from ui.components.title_bar import CustomTitleBar
from ui.components.format_cards import FormatCardWidget
from ui.components.task_item import TaskItemWidget
from ui.components.clip_selector import ClipSelectorWidget
from ui.dialogs.settings_dialog import SettingsDialog
from ui.dialogs.history_dialog import HistoryDialog
from ui.dialogs.user_dialog import WhoAreYouDialog
from ui.dialogs.profile_dialog import UserProfileDialog
from ui.dialogs.playlist_dialog import PlaylistDialog, PlaylistPromptDialog



# --- Worker Signals for Asynchronous Parsing ---
class ParseSignals(QObject):
    finished = Signal(dict)
    error = Signal(str)

class ParseWorker(QRunnable):
    def __init__(self, url: str, stream_title: str = None, referer: str = None, is_playlist: bool = False):
        super().__init__()
        self.url = url
        self.stream_title = stream_title
        self.referer = referer
        self.is_playlist = is_playlist
        self.signals = ParseSignals()

    @Slot()
    def run(self):
        try:
            custom_headers = {"Referer": self.referer} if self.referer else None
            if self.is_playlist:
                data = parse_playlist(self.url, custom_headers=custom_headers)
            else:
                data = parse_url(self.url, custom_headers=custom_headers, stream_title=self.stream_title)
            self.signals.finished.emit(data)
        except Exception as e:
            self.signals.error.emit(str(e))


# --- Worker Signals for Asynchronous Thumbnail Download ---
class ImageSignals(QObject):
    loaded = Signal(bytes)

class ImageWorker(QRunnable):
    def __init__(self, img_urls):
        super().__init__()
        if isinstance(img_urls, str):
            self.img_urls = [img_urls]
        else:
            self.img_urls = list(img_urls) if img_urls else []
        self.signals = ImageSignals()

    @Slot()
    def run(self):
        import ssl
        import urllib.request
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for url in self.img_urls:
            if not url or not isinstance(url, str):
                continue
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
                )
                with urllib.request.urlopen(req, context=ctx, timeout=7) as resp:
                    if resp.status == 200:
                        data = resp.read()
                        if len(data) > 500:
                            self.signals.loaded.emit(data)
                            return
            except Exception:
                continue


# --- Main Application Window ---
class MainWindow(QMainWindow):
    progress_signal = Signal(str, dict)

    def __init__(self, app_icon=None, icon_path=None):
        super().__init__()
        self.setWindowTitle("Studio Download - Universal Media Engine")
        self.resize(1020, 720)
        self.setMinimumSize(980, 660)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        # Icon handling for solid taskbar and window binding
        self.icon_path = icon_path
        if not self.icon_path:
            for p in [
                get_app_dir() / "app_icon.png",
                get_app_dir() / "app_icon.ico",
                Path(__file__).resolve().parent.parent / "app_icon.png",
                Path(__file__).resolve().parent.parent / "app_icon.ico"
            ]:
                if p.exists():
                    self.icon_path = str(p)
                    break

        self.app_icon = app_icon
        if not self.app_icon and self.icon_path:
            self.app_icon = QIcon(self.icon_path)

        if self.app_icon:
            self.setWindowIcon(self.app_icon)

        self.thread_pool = QThreadPool.globalInstance()
        self.current_parse_data = None
        self.selected_format = None
        self.active_mode = "video"  # "video" or "audio"
        self.task_widgets = {}      # task_id -> TaskItemWidget
        self._current_grid_cols = 4

        # Setup GUI thread progress connection
        self.progress_signal.connect(self._on_progress_update)
        download_manager.subscribe_progress(lambda tid, data: self.progress_signal.emit(tid, data))

        # Apply user configured theme
        settings = get_settings()
        self.current_theme = settings.get("theme", "developer-zinc")
        self.setStyleSheet(get_theme_qss(self.current_theme))

        # Initialize system tray icon (Discord style background service)
        self._is_force_quitting = False
        self._has_shown_tray_hint = False
        self._init_tray_icon()

        self._init_ui()

        # Check initial user identity / session (deferred so window renders first)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(350, self._check_initial_user_profile)

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet("""
            QWidget#centralWidget {
                background-color: #09090b;
                border: 1px solid #27272a;
            }
        """)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Custom Title Bar with Developer Theme & Crisp Logo
        self.title_bar = CustomTitleBar(self, title="Studio Download", icon_path=self.icon_path)
        self.title_bar.open_history_requested.connect(self._open_history_dialog)
        self.title_bar.open_settings_requested.connect(self._open_settings_dialog)
        self.title_bar.open_user_profile_requested.connect(self._open_user_profile_dialog)
        self.title_bar.language_changed.connect(self._on_language_changed)
        root_layout.addWidget(self.title_bar)

        # Connect Extension IPC Bridge
        try:
            from backend.ipc_bridge import extension_bridge
            extension_bridge.remote_stream_received.connect(self._on_remote_stream_received)
            extension_bridge.cookies_updated.connect(self._on_cookies_updated)
        except Exception:
            pass

        # 2. Main Scrollable Container with Responsive Centered Content Wrapper
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #09090b;")

        # Outer Horizontal Layout to Center Content on Wide / Maximized Screens
        outer_h_layout = QHBoxLayout(scroll_content)
        outer_h_layout.setContentsMargins(28, 20, 28, 28)
        outer_h_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)

        # Centered Responsive Content Container (Modern desktop 1240px max width)
        self.content_wrapper = QWidget()
        self.content_wrapper.setMaximumWidth(1240)
        self.content_wrapper.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.main_layout = QVBoxLayout(self.content_wrapper)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(16)

        outer_h_layout.addWidget(self.content_wrapper)

        # A. Hero Header (Developer Console Aesthetic)
        hero_layout = QVBoxLayout()
        hero_layout.setSpacing(6)

        # Terminal Code Eyebrow: $ init media_engine("yt-dlp@2026.8", 4K_READY)
        lbl_eyebrow = QLabel(
            '<span style="color:#fbbf24; font-weight:700;">$</span> '
            '<span style="color:#818cf8; font-weight:700;">init</span> '
            '<span style="color:#38bdf8; font-weight:700;">media_engine</span>'
            '<span style="color:#52525b;">(&quot;</span><span style="color:#34d399;">yt-dlp@2026.8</span><span style="color:#52525b;">&quot;, </span>'
            '<span style="color:#fbbf24;">4K_READY</span><span style="color:#52525b;">)</span>',
            self
        )
        lbl_eyebrow.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        hero_layout.addWidget(lbl_eyebrow)

        lbl_title = QLabel(
            'Studio Download <span style="color:#71717a; font-family:\'JetBrains Mono\', monospace; font-size:14px; font-weight:400;">// ingest()</span>',
            self
        )
        lbl_title.setStyleSheet("color: #f4f4f5; font-size: 22px; font-weight: 800; letter-spacing: -0.4px;")
        hero_layout.addWidget(lbl_title)

        self.lbl_desc = QLabel(t("hero_desc"), self)
        self.lbl_desc.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.4;")
        self.lbl_desc.setWordWrap(True)
        hero_layout.addWidget(self.lbl_desc)

        self.main_layout.addLayout(hero_layout)

        # B. Unified Spotlight Input Bar (Single seamless card container)
        input_container = QFrame(self)
        input_container.setObjectName("spotlightBar")
        input_container.setStyleSheet("""
            QFrame#spotlightBar {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 4px 6px 4px 12px;
            }
            QFrame#spotlightBar:hover {
                border-color: #3f3f46;
            }
        """)

        input_box = QVBoxLayout(input_container)
        input_box.setContentsMargins(0, 0, 0, 0)
        input_box.setSpacing(0)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        # Terminal Prompt Prefix
        uri_prompt = QLabel('<span style="color:#38bdf8; font-weight:700;">&gt;_</span> <span style="color:#a1a1aa; font-weight:700;">URI:</span>', self)
        uri_prompt.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 12px; background: transparent;")
        input_row.addWidget(uri_prompt)

        # Inner borderless input
        self.txt_url = QLineEdit(self)
        self.txt_url.setPlaceholderText(t("url_placeholder"))
        self.txt_url.setFixedHeight(36)
        self.txt_url.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 0 4px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                selection-background-color: #38bdf8;
                selection-color: #09090b;
            }
        """)
        self.txt_url.returnPressed.connect(self._start_analysis)
        input_row.addWidget(self.txt_url, 1)

        # Ghost Clear Button (✕)
        self.btn_clear = QPushButton("✕", self)
        self.btn_clear.setFixedSize(28, 28)
        self.btn_clear.setToolTip(t("clear_btn_title"))
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #71717a;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #1c1d24;
                color: #f43f5e;
            }
        """)
        self.btn_clear.clicked.connect(lambda: self.txt_url.clear())
        input_row.addWidget(self.btn_clear)

        # Developer Paste Button
        self.btn_paste = QPushButton(t("paste_btn"), self)
        self.btn_paste.setFixedHeight(32)
        self.btn_paste.setMinimumWidth(76)
        self.btn_paste.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_paste.setToolTip(t("paste_btn_title"))
        self.btn_paste.setStyleSheet("""
            QPushButton {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
                font-size: 11px;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #22232c;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton:pressed {
                background-color: #111216;
            }
        """)
        self.btn_paste.clicked.connect(self._paste_clipboard)
        input_row.addWidget(self.btn_paste)

        # Primary Action CTA Button
        self.btn_analyze = QPushButton(t("analyze_btn"), self)
        self.btn_analyze.setObjectName("btnPrimary")
        self.btn_analyze.setFixedHeight(32)
        self.btn_analyze.setMinimumWidth(148)
        self.btn_analyze.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_analyze.setStyleSheet("""
            QPushButton#btnPrimary {
                background-color: #38bdf8;
                color: #09090b;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 11.5px;
                letter-spacing: 0.2px;
                padding: 0 14px;
            }
            QPushButton#btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton#btnPrimary:pressed {
                background-color: #0284c7;
                color: #ffffff;
            }
            QPushButton#btnPrimary:disabled {
                background-color: #27272a;
                border-color: #27272a;
                color: #71717a;
            }
        """)
        self.btn_analyze.clicked.connect(self._start_analysis)
        input_row.addWidget(self.btn_analyze)

        input_box.addLayout(input_row)

        self.main_layout.addWidget(input_container)

        # Stream Helper & Header Option Bar
        ref_row = QHBoxLayout()
        ref_row.setContentsMargins(6, 0, 6, 0)
        self.helper_lbl = QLabel(f'<span style="color: #71717a; font-family:\'JetBrains Mono\', monospace;">{t("stream_helper")}</span>', self)
        self.helper_lbl.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px; background: transparent;")
        ref_row.addWidget(self.helper_lbl)
        ref_row.addStretch()

        self.btn_ref_toggle = QPushButton(t("referer_toggle"), self)
        self.btn_ref_toggle.setStyleSheet("background: transparent; border: none; color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; padding: 0;")
        self.btn_ref_toggle.clicked.connect(self._toggle_referer)
        ref_row.addWidget(self.btn_ref_toggle)
        self.main_layout.addLayout(ref_row)

        self.txt_referer = QLineEdit(self)
        self.txt_referer.setPlaceholderText(t("referer_placeholder"))
        self.txt_referer.setFixedHeight(32)
        self.txt_referer.setStyleSheet("font-size: 11px; border-radius: 8px;")
        self.txt_referer.setVisible(False)
        self.main_layout.addWidget(self.txt_referer)

        # C. Analysis Result Box (Reveals on analysis)
        self.result_box = QFrame(self)
        self.result_box.setStyleSheet("""
            QFrame#resultBox {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 10px;
                padding: 14px;
            }
            QFrame#resultBox QLabel {
                background: transparent;
                background-color: transparent;
            }
        """)
        self.result_box.setObjectName("resultBox")
        self.result_box.setVisible(False)
        self._init_result_box()
        self.main_layout.addWidget(self.result_box)

        # D. Active Tasks Section
        tasks_header = QHBoxLayout()
        self.lbl_tasks_head = QLabel(f'<span style="color:#818cf8; font-family:\'JetBrains Mono\',monospace; font-weight:700;">{t("active_queue_header")}</span>', self)
        self.lbl_tasks_head.setStyleSheet("font-size: 11px;")
        tasks_header.addWidget(self.lbl_tasks_head)

        self.lbl_task_count = QLabel(f"[{t('count_label')}: 0]", self)
        self.lbl_task_count.setStyleSheet("background-color: #16171d; border: 1px solid #27272a; color: #38bdf8; border-radius: 4px; padding: 1px 6px; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;")
        tasks_header.addWidget(self.lbl_task_count)
        tasks_header.addStretch()
        self.main_layout.addLayout(tasks_header)

        # Task list container
        self.tasks_container = QVBoxLayout()
        self.tasks_container.setSpacing(8)

        # High-tech IDE Telemetry Standby Dashboard
        self.lbl_tasks_empty = self._build_telemetry_card()
        self.tasks_container.addWidget(self.lbl_tasks_empty)

        self.main_layout.addLayout(self.tasks_container)

        self.main_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        root_layout.addWidget(scroll_area, 1)

        self.retranslate_ui()

    def _build_telemetry_card(self) -> QFrame:
        card = QFrame(self)
        card.setObjectName("emptyQueueCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        card.setStyleSheet("""
            QFrame#emptyQueueCard {
                background-color: #111216;
                border: 1px dashed #27272a;
                border-radius: 8px;
            }
            QFrame#emptyQueueCard QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        t_layout = QVBoxLayout(card)
        t_layout.setContentsMargins(24, 36, 24, 36)
        t_layout.setSpacing(8)

        self.lbl_queue_head = QLabel(t("empty_queue_head"), card)
        self.lbl_queue_head.setAlignment(Qt.AlignCenter)
        self.lbl_queue_head.setStyleSheet("color: #e4e4e7; font-size: 13px; font-weight: 600;")
        t_layout.addWidget(self.lbl_queue_head)

        self.lbl_queue_sub = QLabel(t("empty_queue_sub"), card)
        self.lbl_queue_sub.setAlignment(Qt.AlignCenter)
        self.lbl_queue_sub.setStyleSheet("color: #71717a; font-size: 12px;")
        t_layout.addWidget(self.lbl_queue_sub)

        self.lbl_queue_shortcuts = QLabel(t("empty_queue_tip"), card)
        self.lbl_queue_shortcuts.setAlignment(Qt.AlignCenter)
        self.lbl_queue_shortcuts.setStyleSheet("color: #52525b; font-size: 11px; margin-top: 4px;")
        t_layout.addWidget(self.lbl_queue_shortcuts)

        return card



    def _init_result_box(self):
        res_layout = QVBoxLayout(self.result_box)
        res_layout.setContentsMargins(16, 16, 16, 16)
        res_layout.setSpacing(14)

        # Terminal Header Bar
        self.bar_header = QLabel(f'<span style="color: #818cf8; font-family: \'JetBrains Mono\', monospace; font-weight: 700;">{t("manifest_title")}</span>', self.result_box)
        self.bar_header.setStyleSheet("font-size: 11px;")
        res_layout.addWidget(self.bar_header)

        # Top Part: Thumbnail + Info (Left / Right)
        top_h = QHBoxLayout()
        top_h.setSpacing(16)

        # Thumbnail Label (Standard 16:9 ratio 208x117)
        self.lbl_thumb = QLabel(self.result_box)
        self.lbl_thumb.setFixedSize(208, 117)
        self.lbl_thumb.setStyleSheet("background-color: #121318; border-radius: 8px; border: 1px solid #27272a; color: #52525b; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;")
        self.lbl_thumb.setAlignment(Qt.AlignCenter)
        self.lbl_thumb.setText(t("thumbnail_loading"))
        top_h.addWidget(self.lbl_thumb, 0, Qt.AlignTop)

        # Info details
        info_v = QVBoxLayout()
        info_v.setSpacing(8)

        # Title Container with header
        title_v = QVBoxLayout()
        title_v.setSpacing(3)
        self.lbl_title_tag = QLabel(t("target_name_label"), self.result_box)
        self.lbl_title_tag.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; background: transparent;")
        title_v.addWidget(self.lbl_title_tag)

        self.txt_title = QLineEdit(self.result_box)
        self.txt_title.setFixedHeight(34)
        self.txt_title.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 12.5px; background: #14151b; border: 1px solid #27272a; border-radius: 6px; padding: 0 12px; color: #f4f4f5; selection-background-color: #38bdf8; selection-color: #09090b;")
        self.txt_title.setToolTip(t("target_name_tooltip"))
        title_v.addWidget(self.txt_title)
        info_v.addLayout(title_v)

        meta_h = QHBoxLayout()
        meta_h.setSpacing(8)
        self.lbl_uploader = QLabel(f"{t('meta_creator')} --", self.result_box)
        self.lbl_uploader.setStyleSheet("color: #38bdf8; background: #0e1926; border: 1px solid #1a3556; border-radius: 4px; padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600;")
        meta_h.addWidget(self.lbl_uploader)

        self.lbl_duration = QLabel(f"{t('meta_duration')} --", self.result_box)
        self.lbl_duration.setStyleSheet("color: #fbbf24; background: #1f1b10; border: 1px solid #3d3215; border-radius: 4px; padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600;")
        meta_h.addWidget(self.lbl_duration)

        self.lbl_views = QLabel(f"{t('meta_views')} --", self.result_box)
        self.lbl_views.setStyleSheet("color: #34d399; background: #0e1e17; border: 1px solid #1a3d2e; border-radius: 4px; padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 600;")
        meta_h.addWidget(self.lbl_views)
        meta_h.addStretch()
        info_v.addLayout(meta_h)

        # Mode Selector (Segmented Pill Switcher with compact fixed width)
        mode_row = QHBoxLayout()
        seg_container = QFrame(self.result_box)
        seg_container.setObjectName("modeSegment")
        seg_container.setFixedWidth(250)
        seg_container.setFixedHeight(30)
        seg_container.setStyleSheet("""
            QFrame#modeSegment {
                background-color: #0d0e12;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
        """)
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)

        self.btn_mode_video = QPushButton(t("tab_video"), seg_container)
        self.btn_mode_video.setFixedHeight(24)
        self.btn_mode_video.setCheckable(True)
        self.btn_mode_video.setChecked(True)
        self.btn_mode_video.clicked.connect(lambda: self._set_mode("video"))
        seg_layout.addWidget(self.btn_mode_video)

        self.btn_mode_audio = QPushButton(t("tab_audio"), seg_container)
        self.btn_mode_audio.setFixedHeight(24)
        self.btn_mode_audio.setCheckable(True)
        self.btn_mode_audio.clicked.connect(lambda: self._set_mode("audio"))
        seg_layout.addWidget(self.btn_mode_audio)

        mode_row.addWidget(seg_container)
        mode_row.addStretch()
        info_v.addLayout(mode_row)
        info_v.addStretch()

        top_h.addLayout(info_v, 1)
        res_layout.addLayout(top_h)

        # Middle Part: Format Cards Grid
        self.lbl_resolutions = QLabel(t("format_matrix_label"), self.result_box)
        self.lbl_resolutions.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; letter-spacing: 0.3px; margin-top: 4px; background: transparent;")
        res_layout.addWidget(self.lbl_resolutions)

        self.cards_grid = QGridLayout()
        self.cards_grid.setSpacing(8)
        res_layout.addLayout(self.cards_grid)

        # Multi-Clip Slicer Widget
        self.clip_selector = ClipSelectorWidget(self.result_box)
        self.clip_selector.clips_changed.connect(self._on_clips_changed)
        self.clip_selector.toggled.connect(self._on_clips_toggled)
        res_layout.addWidget(self.clip_selector)

        # Bottom Part: Container format & Download Button
        bottom_h = QHBoxLayout()
        bottom_h.setSpacing(10)

        self.lbl_format_label = QLabel(t("container_label"), self.result_box)
        self.lbl_format_label.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #a1a1aa; background: transparent;")
        bottom_h.addWidget(self.lbl_format_label)
        self.combo_container = QComboBox(self.result_box)
        self.combo_container.setFixedHeight(30)
        self.combo_container.addItems(["MP4", "MKV"])
        bottom_h.addWidget(self.combo_container)

        self.lbl_codec_label = QLabel(t("codec_label"), self.result_box)
        self.lbl_codec_label.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #a1a1aa; background: transparent;")
        bottom_h.addWidget(self.lbl_codec_label)
        self.combo_codec = QComboBox(self.result_box)
        self.combo_codec.setFixedHeight(30)
        self.combo_codec.addItems([t("codec_h264"), t("codec_prores"), t("codec_source")])
        self.combo_codec.currentIndexChanged.connect(self._on_codec_changed)
        bottom_h.addWidget(self.combo_codec)

        bottom_h.addStretch()

        self.btn_start_dl = QPushButton(t("start_download_btn"), self.result_box)
        self.btn_start_dl.setObjectName("btnPrimary")
        self.btn_start_dl.setMinimumWidth(180)
        self.btn_start_dl.setFixedHeight(34)
        self.btn_start_dl.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_start_dl.setStyleSheet("""
            QPushButton#btnPrimary {
                background-color: #38bdf8;
                color: #09090b;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 11.5px;
                letter-spacing: 0.2px;
                padding: 0 16px;
            }
            QPushButton#btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton#btnPrimary:pressed {
                background-color: #0284c7;
                color: #ffffff;
            }
            QPushButton#btnPrimary:disabled {
                background-color: #27272a;
                border-color: #27272a;
                color: #71717a;
            }
        """)
        self.btn_start_dl.clicked.connect(self._trigger_download)
        bottom_h.addWidget(self.btn_start_dl)

        res_layout.addLayout(bottom_h)

    def _toggle_referer(self):
        vis = not self.txt_referer.isVisible()
        self.txt_referer.setVisible(vis)
        self.btn_ref_toggle.setText(t("referer_toggle_open") if vis else t("referer_toggle_close"))

    def _paste_clipboard(self):
        clip = QApplication.clipboard().text()
        if clip:
            self.txt_url.setText(clip.strip())

    def _start_analysis(self):
        raw_url = self.txt_url.text().strip()
        if not raw_url:
            QMessageBox.warning(self, t("dialog_warning"), t("err_invalid_url"))
            return

        target_vid = extract_video_id(raw_url)

        # Check URL type:
        # Case A: Video inside a playlist (e.g. watch?v=...&list=...&index=...)
        if is_video_in_playlist_url(raw_url):
            prompt = PlaylistPromptDialog(raw_url, parent=self)
            prompt.exec()
            choice = prompt.result_choice
            if not choice:
                # User cancelled dialog
                return

            if choice == "single":
                clean_url = normalize_youtube_url(raw_url)
                self.txt_url.setText(clean_url)
                url = clean_url
                is_pl = False
            else:  # "playlist"
                url = raw_url
                is_pl = True
        elif is_pure_playlist_url(raw_url):
            # Case B: Pure playlist URL without single video ID
            url = raw_url
            is_pl = True
        else:
            # Case C: Regular single video or generic stream
            clean_url = normalize_youtube_url(raw_url)
            if clean_url != raw_url:
                self.txt_url.setText(clean_url)
            url = clean_url
            is_pl = False

        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText(t("analyzing_btn"))
        self.result_box.setVisible(False)

        ref = self.txt_referer.text().strip() if self.txt_referer.isVisible() else None
        worker = ParseWorker(url, referer=ref, is_playlist=is_pl)
        self._last_parsed_target_vid = target_vid if is_pl else None
        worker.signals.finished.connect(self._on_parse_success)
        worker.signals.error.connect(self._on_parse_error)
        self.thread_pool.start(worker)

    def _on_parse_success(self, data: dict):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText(t("analyze_btn"))

        if data.get("type") == "playlist":
            self._open_playlist_dialog(data)
            return

        self.current_parse_data = data
        self.result_box.setVisible(True)

        # Title & Meta
        title = data.get("title", "Video")
        self.txt_title.setText(title)
        uploader = data.get("uploader", "Unknown")
        if uploader and not uploader.startswith("@"):
            uploader = f"@{uploader}"
        self.lbl_uploader.setText(f"{t('meta_creator')} {uploader}")
        self.lbl_duration.setText(f"{t('meta_duration')} {data.get('duration', '--')}")
        self.lbl_views.setText(f"{t('meta_views')} {data.get('views', '--')}")

        # Async Thumbnail load with candidate fallback chain
        thumb_candidates = data.get("thumbnail_candidates") or []
        thumb_url = data.get("thumbnail")
        if thumb_url and thumb_url not in thumb_candidates:
            thumb_candidates.insert(0, thumb_url)

        self.lbl_thumb.setPixmap(QPixmap())
        self.lbl_thumb.setText(t("thumbnail_loading"))

        if thumb_candidates:
            img_worker = ImageWorker(thumb_candidates)
            img_worker.signals.loaded.connect(self._on_thumb_loaded)
            self.thread_pool.start(img_worker)
        else:
            self.lbl_thumb.setText(t("thumbnail_no_preview"))

        # Reset mode, clip selector & render cards
        self.selected_format = None
        duration_sec = data.get("duration_seconds", 0)
        duration_str = data.get("duration", "--")
        if hasattr(self, "clip_selector"):
            self.clip_selector.reset()
            self.clip_selector.set_max_duration(duration_sec, duration_str)

        self._set_mode("video")
        self._update_start_download_button_text()

    def _on_parse_error(self, err: str):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText(t("analyze_btn"))
        QMessageBox.critical(self, t("err_parse_failed_title"), t("err_parse_failed_msg").format(err=err))

    def _open_playlist_dialog(self, data: dict):
        target_vid = getattr(self, "_last_parsed_target_vid", None)
        dialog = PlaylistDialog(data, target_video_id=target_vid, parent=self)
        dialog.batch_confirmed.connect(self._on_playlist_batch_confirmed)
        dialog.exec()

    def _on_playlist_batch_confirmed(self, selected_items: list, config: dict):
        mode = config.get("mode", "video")
        chosen_format = config.get("format", "mp4" if mode == "video" else "mp3")
        height = config.get("height")
        codec_pref = config.get("codec_preference", "compatible")
        audio_quality = config.get("audio_quality", "320")

        ref = self.txt_referer.text().strip() if self.txt_referer.isVisible() and self.txt_referer.text().strip() else None

        queued_count = 0
        for item in selected_items:
            item_url = item.get("url")
            item_title = item.get("title") or "Media"

            options = {
                "title": item_title,
                "mode": mode,
                "format": chosen_format,
                "height": height,
                "codec_preference": codec_pref,
                "audio_quality": audio_quality,
                "duration": item.get("duration", "--"),
                "duration_seconds": item.get("duration_seconds", 0),
                "thumbnail": item.get("thumbnail", ""),
                "referer": ref
            }

            try:
                task_id = download_manager.start_download(item_url, options)
                self._add_task_to_ui(task_id, active_tasks.get(task_id, {}))
                queued_count += 1
            except Exception as e:
                print(f"[!] Error queuing playlist item {item_title}: {e}")

        if queued_count > 0:
            QMessageBox.information(
                self,
                t("dialog_success"),
                f"{queued_count} media dari playlist berhasil dimasukkan ke antrean unduhan."
            )

    def _on_thumb_loaded(self, img_bytes: bytes):
        pix = QPixmap()
        if not pix.loadFromData(img_bytes):
            self.lbl_thumb.setText(t("thumbnail_err"))
            return

        # Universal letterbox crop for YouTube 4:3 images (480x360, 640x480, etc.)
        w, h = pix.width(), pix.height()
        if h > 0 and abs((w / h) - (4.0 / 3.0)) < 0.08:
            ideal_h = int(w * 9 / 16)
            bar_h = max(0, (h - ideal_h) // 2)
            if bar_h > 0:
                pix = pix.copy(0, bar_h, w, ideal_h)

        target_size = self.lbl_thumb.size()
        target_w = target_size.width()
        target_h = target_size.height()

        scaled_pix = pix.scaled(target_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        crop_x = max(0, (scaled_pix.width() - target_w) // 2)
        crop_y = max(0, (scaled_pix.height() - target_h) // 2)
        final_cropped = scaled_pix.copy(crop_x, crop_y, target_w, target_h)

        rounded = QPixmap(target_size)
        rounded.fill(Qt.transparent)

        from PySide6.QtGui import QPainter, QPainterPath
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        path = QPainterPath()
        path.addRoundedRect(0, 0, target_w, target_h, 8, 8)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, final_cropped)
        painter.end()

        self.lbl_thumb.setText("")
        self.lbl_thumb.setPixmap(rounded)

    def _on_clips_changed(self, clips: list):
        self._update_start_download_button_text()

    def _on_clips_toggled(self, enabled: bool):
        self._update_start_download_button_text()

    def _estimate_clip_size_str(self, duration_sec: int) -> str:
        if not hasattr(self, "selected_format") or not self.selected_format or duration_sec <= 0:
            return ""
        full_dur = (self.current_parse_data and self.current_parse_data.get("duration_seconds")) or 0
        full_sz = self.selected_format.get("filesize", 0)
        if full_dur > 0 and full_sz > 0:
            c_bytes = int(full_sz * min(1.0, max(0.001, duration_sec / full_dur)))
            return f"~{format_bytes(c_bytes)}"
        else:
            if self.active_mode == "audio":
                bps = 320_000
            else:
                h = self.selected_format.get("height") or 1080
                bps = 20_000_000 if h >= 2160 else (12_000_000 if h >= 1440 else 5_000_000)
            c_bytes = int(duration_sec * bps / 8)
            return f"~{format_bytes(c_bytes)}"

    def _update_start_download_button_text(self):
        if not hasattr(self, "btn_start_dl") or not hasattr(self, "clip_selector"):
            return

        qual_tag = ""
        if self.active_mode == "video" and hasattr(self, "selected_format") and self.selected_format:
            h = self.selected_format.get("height")
            lbl = self.selected_format.get("label") or (f"{h}p" if h else "")
            if lbl:
                clean_lbl = lbl.split("/")[0].split("(")[0].strip()
                if not clean_lbl:
                    clean_lbl = lbl[:14].strip()
                qual_tag = f" [{clean_lbl}]"
        elif self.active_mode == "audio" and hasattr(self, "selected_format") and self.selected_format:
            qual_tag = f" [{self.selected_format.get('format', 'MP3').upper()}]"

        base_raw = t("start_download_btn") if self.active_mode == "video" else t("start_download_audio_btn")
        base_clean = base_raw.rstrip("()")

        if self.clip_selector.is_enabled():
            clips = self.clip_selector.get_clips()
            est_size_str = ""
            if clips:
                clip_dur = clips[0].get("duration", 0) if len(clips) == 1 else sum(c.get("duration", 0) for c in clips)
                raw_est = self._estimate_clip_size_str(clip_dur)
                if raw_est:
                    est_size_str = f" ({raw_est})"

            if len(clips) > 1:
                self.btn_start_dl.setText(f"UNDUH {len(clips)} KLIP{qual_tag}{est_size_str}")
            elif len(clips) == 1:
                dur_str = format_duration(clips[0].get("duration", 0))
                self.btn_start_dl.setText(f"UNDUH 1 KLIP ({dur_str}){qual_tag}{est_size_str}")
            else:
                self.btn_start_dl.setText(f"{base_clean}{qual_tag}")
        else:
            size_tag = ""
            if hasattr(self, "selected_format") and self.selected_format and self.selected_format.get("filesize_formatted"):
                size_tag = f" (~{self.selected_format['filesize_formatted']})"
            self.btn_start_dl.setText(f"{base_clean}{qual_tag}{size_tag}")

    def _set_mode(self, mode: str):
        if self.active_mode != mode:
            self.selected_format = None
        self.active_mode = mode
        if mode == "video":
            self.btn_mode_video.setChecked(True)
            self.btn_mode_audio.setChecked(False)
            self.btn_mode_video.setStyleSheet("background: #1c2234; color: #38bdf8; border: none; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 11px;")
            self.btn_mode_audio.setStyleSheet("background: transparent; color: #71717a; border: none; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-weight: 500; font-size: 11px;")
            self._update_start_download_button_text()
            self.combo_container.setVisible(True)
            self.combo_codec.setVisible(True)
            if hasattr(self, "lbl_format_label"):
                self.lbl_format_label.setVisible(True)
            if hasattr(self, "lbl_codec_label"):
                self.lbl_codec_label.setVisible(True)
        else:
            self.btn_mode_video.setChecked(False)
            self.btn_mode_audio.setChecked(True)
            self.btn_mode_audio.setStyleSheet("background: #1c2234; color: #38bdf8; border: none; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 11px;")
            self.btn_mode_video.setStyleSheet("background: transparent; color: #71717a; border: none; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-weight: 500; font-size: 11px;")
            self._update_start_download_button_text()
            self.combo_container.setVisible(False)
            self.combo_codec.setVisible(False)
            if hasattr(self, "lbl_format_label"):
                self.lbl_format_label.setVisible(False)
            if hasattr(self, "lbl_codec_label"):
                self.lbl_codec_label.setVisible(False)

        self._render_format_cards()

    def _calc_format_columns(self, total_items: int = 0) -> int:
        wrap_w = self.content_wrapper.width() if hasattr(self, "content_wrapper") else self.width()
        if total_items <= 2:
            return max(1, total_items)
        if wrap_w >= 1050:
            return 4 if total_items > 6 else 3
        elif wrap_w >= 880:
            return 3
        else:
            return 2

    def _render_format_cards(self):
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_parse_data:
            return

        formats = self.current_parse_data.get("resolutions" if self.active_mode == "video" else "audio_presets", [])
        self.format_card_widgets = []

        if self.active_mode == "video":
            codec_map = {0: "compatible", 1: "prores", 2: "original"}
            codec_key = codec_map.get(self.combo_codec.currentIndex(), "compatible")
            for fmt in formats:
                if isinstance(fmt, dict) and "codecs" in fmt and codec_key in fmt["codecs"]:
                    var = fmt["codecs"][codec_key]
                    fmt["codec"] = var.get("codec", fmt.get("codec"))
                    fmt["format_id"] = var.get("format_id", fmt.get("format_id"))
                    fmt["filesize"] = var.get("filesize", fmt.get("filesize"))
                    fmt["filesize_formatted"] = var.get("filesize_formatted", fmt.get("filesize_formatted"))
                    if "fps" in var:
                        fmt["fps"] = var["fps"]

        if not hasattr(self, "selected_format") or not self.selected_format:
            if self.active_mode == "video":
                # Default to 1080p if available, else first format
                fav_1080 = next((f for f in formats if f.get("height") == 1080), None)
                self.selected_format = fav_1080 or (formats[0] if formats else None)
            else:
                self.selected_format = formats[0] if formats else None

        cols = self._calc_format_columns(len(formats))
        self._current_grid_cols = cols

        for idx, fmt in enumerate(formats):
            is_sel = self._is_format_match(fmt, self.selected_format)
            card = FormatCardWidget(fmt, index=idx + 1, is_selected=is_sel)
            card.card_selected.connect(self._on_format_card_clicked)
            self.cards_grid.addWidget(card, idx // cols, idx % cols)
            self.format_card_widgets.append(card)

        if hasattr(self, "clip_selector"):
            self.clip_selector.set_size_estimator(self._estimate_clip_size_str)
        self._update_start_download_button_text()

    def _is_format_match(self, fmt_a: dict, fmt_b: dict) -> bool:
        if not fmt_a or not fmt_b:
            return False
        if fmt_a is fmt_b:
            return True
        if self.active_mode == "audio":
            q_a = fmt_a.get("quality")
            q_b = fmt_b.get("quality")
            f_a = fmt_a.get("format")
            f_b = fmt_b.get("format")
            if q_a is not None and q_b is not None:
                return str(q_a) == str(q_b) and str(f_a).lower() == str(f_b).lower()
            lbl_a = fmt_a.get("label")
            lbl_b = fmt_b.get("label")
            return lbl_a == lbl_b if lbl_a else False

        # Video mode: match by height and format_id
        h_a = fmt_a.get("height")
        h_b = fmt_b.get("height")
        fid_a = fmt_a.get("format_id")
        fid_b = fmt_b.get("format_id")
        if h_a is not None and h_b is not None:
            if fid_a and fid_b:
                return h_a == h_b and fid_a == fid_b
            return h_a == h_b
        if fid_a and fid_b:
            return fid_a == fid_b
        return False

    def _on_codec_changed(self, index: int):
        if self.active_mode != "video":
            return
        codec_map = {0: "compatible", 1: "prores", 2: "original"}
        codec_key = codec_map.get(index, "compatible")

        for card in self.format_card_widgets:
            fmt = card.format_data
            if isinstance(fmt, dict) and "codecs" in fmt and codec_key in fmt["codecs"]:
                var = fmt["codecs"][codec_key]
                fmt["codec"] = var.get("codec", fmt.get("codec"))
                fmt["format_id"] = var.get("format_id", fmt.get("format_id"))
                fmt["filesize"] = var.get("filesize", fmt.get("filesize"))
                fmt["filesize_formatted"] = var.get("filesize_formatted", fmt.get("filesize_formatted"))
                if "fps" in var:
                    fmt["fps"] = var["fps"]
                card.update_format_data(fmt)

        if self.selected_format and isinstance(self.selected_format, dict) and "codecs" in self.selected_format and codec_key in self.selected_format["codecs"]:
            var = self.selected_format["codecs"][codec_key]
            self.selected_format["codec"] = var.get("codec", self.selected_format.get("codec"))
            self.selected_format["format_id"] = var.get("format_id", self.selected_format.get("format_id"))
            self.selected_format["filesize"] = var.get("filesize", self.selected_format.get("filesize"))
            self.selected_format["filesize_formatted"] = var.get("filesize_formatted", self.selected_format.get("filesize_formatted"))
            if "fps" in var:
                self.selected_format["fps"] = var["fps"]

        if hasattr(self, "clip_selector"):
            self.clip_selector.set_size_estimator(self._estimate_clip_size_str)
        self._update_start_download_button_text()

    def _on_format_card_clicked(self, format_data: dict):
        self.selected_format = format_data
        for card in self.format_card_widgets:
            card.set_selected(self._is_format_match(card.format_data, format_data))
        if hasattr(self, "clip_selector"):
            self.clip_selector.set_size_estimator(self._estimate_clip_size_str)
        self._update_start_download_button_text()

    def _trigger_download(self):
        if not self.current_parse_data:
            return

        url = self.current_parse_data.get("webpage_url") or self.txt_url.text().strip()
        final_title = self.txt_title.text().strip() or self.current_parse_data.get("title", "Unduhan")

        codec_map = {
            0: "compatible",
            1: "prores",
            2: "original"
        }

        options = {
            "title": final_title,
            "thumbnail": self.current_parse_data.get("thumbnail", ""),
            "duration": self.current_parse_data.get("duration", "--"),
            "duration_seconds": self.current_parse_data.get("duration_seconds", 0),
            "full_duration_seconds": self.current_parse_data.get("duration_seconds", 0),
            "mode": self.active_mode,
            "format": self.combo_container.currentText().lower() if self.active_mode == "video" else (self.selected_format.get("format", "mp3") if self.selected_format else "mp3"),
            "codec_preference": codec_map.get(self.combo_codec.currentIndex(), "compatible"),
            "referer": self.txt_referer.text().strip() if self.txt_referer.isVisible() else None
        }

        if self.selected_format:
            options["format_id"] = self.selected_format.get("format_id")
            options["height"] = self.selected_format.get("height")
            options["filesize_approx"] = self.selected_format.get("filesize_formatted", "")
            options["filesize_bytes"] = self.selected_format.get("filesize", 0)
            if self.selected_format.get("direct_url"):
                options["direct_url"] = self.selected_format.get("direct_url")
            if self.active_mode == "audio":
                options["audio_quality"] = self.selected_format.get("quality", "320")

        if hasattr(self, "clip_selector") and self.clip_selector.is_enabled():
            valid, err = self.clip_selector.validate_clips()
            if not valid:
                QMessageBox.warning(self, "Rentang Waktu Tidak Valid", err)
                return

            clips = self.clip_selector.get_clips()
            if not clips:
                QMessageBox.warning(self, "Rentang Waktu Kosong", "Silakan tentukan setidaknya satu rentang durasi klip.")
                return

            try:
                full_dur = options.get("full_duration_seconds") or options.get("duration_seconds", 0)
                full_bytes = options.get("filesize_bytes", 0)
                for c in clips:
                    clip_options = options.copy()
                    clip_options["full_duration_seconds"] = full_dur
                    clip_options["section_start"] = c["start"]
                    clip_options["section_end"] = c["end"]
                    s_lbl = format_time_label(c["start"])
                    e_lbl = format_time_label(c["end"])
                    tag = f"[{s_lbl}-{e_lbl}]"
                    if c.get("label"):
                        tag = f"[{c['label']} {s_lbl}-{e_lbl}]"
                    clip_options["title"] = f"{final_title} {tag}"
                    clip_dur = c["duration"]
                    clip_options["duration_seconds"] = clip_dur
                    clip_options["duration"] = format_duration_hms(clip_dur)

                    # Compute accurate clip size based on duration and bitrate
                    if full_dur > 0 and full_bytes > 0:
                        ratio = min(1.0, max(0.001, clip_dur / full_dur))
                        clip_bytes = int(full_bytes * ratio)
                    else:
                        if clip_options.get("mode") == "audio":
                            bitrate_bps = 320_000
                        else:
                            h = clip_options.get("height") or 1080
                            bitrate_bps = 20_000_000 if h >= 2160 else (12_000_000 if h >= 1440 else 5_000_000)
                        clip_bytes = int(clip_dur * bitrate_bps / 8)

                    clip_options["filesize_bytes"] = clip_bytes
                    clip_options["filesize_approx"] = format_bytes(clip_bytes)

                    task_id = download_manager.start_download(url, clip_options)
                    self._add_task_to_ui(task_id, active_tasks.get(task_id, {}))
            except Exception as e:
                QMessageBox.critical(self, t("err_download_failed_title"), t("err_download_failed_msg").format(err=e))
            return

        try:
            task_id = download_manager.start_download(url, options)
            self._add_task_to_ui(task_id, active_tasks.get(task_id, {}))
        except Exception as e:
            QMessageBox.critical(self, t("err_download_failed_title"), t("err_download_failed_msg").format(err=e))

    def _add_task_to_ui(self, task_id: str, task_data: dict):
        self.lbl_tasks_empty.setVisible(False)
        if task_id in self.task_widgets:
            return

        card = TaskItemWidget(task_data, self)
        card.pause_clicked.connect(self._pause_task)
        card.resume_clicked.connect(self._resume_task)
        card.cancel_clicked.connect(self._cancel_task)
        card.retry_clicked.connect(self._retry_task)
        card.delete_clicked.connect(self._delete_task)
        card.config_clicked.connect(self._open_settings_dialog)

        self.tasks_container.insertWidget(0, card)
        self.task_widgets[task_id] = card
        self._update_task_count()

    def _on_progress_update(self, task_id: str, task_data: dict):
        if task_id not in self.task_widgets:
            self._add_task_to_ui(task_id, task_data)
        else:
            self.task_widgets[task_id].update_data(task_data)
        self._update_task_count()

        # Update dynamic tray tooltip and menu
        now = time.time()
        last_t = getattr(self, "_last_tray_update", 0)
        st = task_data.get("status")
        if now - last_t >= 0.4 or st in ("completed", "error", "starting", "muxing", "paused"):
            self._last_tray_update = now
            self._update_tray_status()

        # Trigger desktop balloon notification if window is hidden in background
        if not self.isVisible() and hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            if st == "completed" and not task_data.get("_tray_notified"):
                task_data["_tray_notified"] = True
                self.tray_icon.showMessage(
                    f"Studio Download - {t('tray_dl_finished')}",
                    f"✓ {task_data.get('title', 'Video')} ({task_data.get('total', '')})",
                    QSystemTrayIcon.Information,
                    4000
                )
            elif st == "error" and not task_data.get("_tray_notified"):
                task_data["_tray_notified"] = True
                err_snippet = (task_data.get("error") or "")[:60]
                self.tray_icon.showMessage(
                    f"Studio Download - {t('tray_dl_failed')}",
                    f"✕ {task_data.get('title', 'Video')}\n{err_snippet}",
                    QSystemTrayIcon.Warning,
                    4000
                )

    def _pause_task(self, task_id: str):
        download_manager.pause_download(task_id)

    def _resume_task(self, task_id: str):
        download_manager.resume_download(task_id)

    def _cancel_task(self, task_id: str):
        confirm = QMessageBox.question(
            self, t("confirm_cancel_title"), t("confirm_cancel_msg"),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            download_manager.cancel_download(task_id)

    def _retry_task(self, task_id: str):
        if task_id in self.task_widgets:
            w = self.task_widgets.pop(task_id)
            w.deleteLater()
            self._update_task_count()
        new_id = download_manager.retry_download(task_id)
        if new_id and new_id in active_tasks:
            self._add_task_to_ui(new_id, active_tasks[new_id])

    def _delete_task(self, task_id: str):
        if task_id in self.task_widgets:
            w = self.task_widgets.pop(task_id)
            w.deleteLater()
        download_manager.delete_task(task_id)
        self._update_task_count()

    def _update_task_count(self):
        count = len(self.task_widgets)
        self.lbl_task_count.setText(f"[{t('count_label')}: {count}]")
        self.lbl_tasks_empty.setVisible(count == 0)

    def _open_download_dir(self):
        settings = get_settings()
        out_dir = settings.get("download_dir") or str(Path.home() / "Downloads" / "StudioDownload")
        os.makedirs(out_dir, exist_ok=True)
        try:
            os.startfile(out_dir)
        except Exception:
            subprocess.Popen(f'explorer "{os.path.normpath(out_dir)}"')

    def _open_history_dialog(self):
        dlg = HistoryDialog(self)
        dlg.redownload_requested.connect(self._on_redownload_from_history)
        dlg.exec()

    def _on_redownload_from_history(self, url: str):
        if not url:
            return
        self.txt_url.setText(url)
        self._start_analysis()
        self._restore_from_tray()

    def _open_user_profile_dialog(self):
        dlg = UserProfileDialog(self)
        dlg.profile_switched.connect(self._on_user_logged_in)
        dlg.guest_mode_activated.connect(self._on_guest_session_started)
        dlg.exec()

    def _open_who_are_you_modal(self, is_first_run: bool = False):
        try:
            dlg = WhoAreYouDialog(self, is_editing=not is_first_run)
            dlg.user_logged_in.connect(self._on_user_logged_in)
            dlg.guest_session_started.connect(self._on_guest_session_started)
            dlg.exec()
        except Exception as e:
            print(f"[!] Warning opening who are you dialog: {e}")
        finally:
            if is_first_run:
                try:
                    save_settings({"onboarding_completed": True})
                except Exception:
                    pass

    def _check_initial_user_profile(self):
        try:
            settings = get_settings()
            if settings.get("onboarding_completed", False):
                return
            user_profile = settings.get("user_profile")
            if not user_profile or not isinstance(user_profile, dict) or not user_profile.get("username"):
                self._open_who_are_you_modal(is_first_run=True)
        except Exception as e:
            print(f"[!] Warning checking user profile: {e}")

    def _on_user_logged_in(self, profile: dict):
        if hasattr(self, "title_bar"):
            self.title_bar.update_user_badge(profile)

    def _on_guest_session_started(self):
        if hasattr(self, "title_bar"):
            self.title_bar.update_user_badge()


    def _open_extension_dialog(self):
        from ui.dialogs.extension_dialog import ExtensionDialog
        dlg = ExtensionDialog(self)
        dlg.exec()

    def _on_remote_stream_received(self, data: dict):
        url = (data.get("url") or "").strip()
        if not url:
            return
        from backend.parser import normalize_youtube_url
        url = normalize_youtube_url(url)
        self.txt_url.setText(url)
        referer = (data.get("referer") or "").strip()
        if referer:
            self.txt_referer.setText(referer)
            self.txt_referer.setVisible(True)
            self.btn_ref_toggle.setText(t("referer_toggle_open"))
        # Restore/Bring window to front
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.raise_()
        self.activateWindow()
        # Automatically trigger parsing
        self._start_analysis()

    def _on_cookies_updated(self, cookie_path: str):
        if hasattr(self, "status_tag"):
            self.status_tag.setText("[COOKIES_SYNCED]")
            self.status_tag.setStyleSheet("color: #34d399; font-weight: 700;")
            QTimer.singleShot(3000, lambda: self.status_tag.setText("// ENGINE_READY"))

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.exec()

    def _open_settings(self):
        self._open_settings_dialog()

    def _on_settings_saved(self, new_settings: dict):
        theme_name = new_settings.get("theme", "developer-zinc")
        app = QApplication.instance()
        if app:
            app.setStyleSheet(get_theme_qss(theme_name))
        new_lang = new_settings.get("language", "en")
        self._on_language_changed(new_lang)
        if hasattr(self, "title_bar"):
            self.title_bar.retranslate_ui()

    def _on_language_changed(self, new_lang: str):
        from backend.i18n import set_current_lang
        set_current_lang(new_lang)
        self.retranslate_ui()

    def retranslate_ui(self):
        if hasattr(self, "title_bar"):
            self.title_bar.retranslate_ui()
        if hasattr(self, "lbl_desc"):
            self.lbl_desc.setText(t("hero_desc"))
        if hasattr(self, "txt_url"):
            self.txt_url.setPlaceholderText(t("url_placeholder"))
        if hasattr(self, "btn_clear"):
            self.btn_clear.setToolTip(t("clear_btn_title"))
        if hasattr(self, "btn_paste"):
            self.btn_paste.setText(t("paste_btn"))
            self.btn_paste.setToolTip(t("paste_btn_title"))
        if hasattr(self, "btn_analyze"):
            if not self.btn_analyze.text().startswith("INSPECT") and not self.btn_analyze.text().startswith("MEMERIK"):
                self.btn_analyze.setText(t("analyze_btn"))
        if hasattr(self, "helper_lbl"):
            self.helper_lbl.setText(f'<span style="color: #71717a; font-family:\'JetBrains Mono\', monospace;">{t("stream_helper")}</span>')
        if hasattr(self, "btn_ref_toggle") and hasattr(self, "txt_referer"):
            self.btn_ref_toggle.setText(t("referer_toggle_open") if self.txt_referer.isVisible() else t("referer_toggle_close"))
            self.txt_referer.setPlaceholderText(t("referer_placeholder"))
        if hasattr(self, "lbl_tasks_head"):
            self.lbl_tasks_head.setText(f'<span style="color:#818cf8; font-family:\'JetBrains Mono\',monospace; font-weight:700;">{t("active_queue_header")}</span>')
        if hasattr(self, "lbl_task_count"):
            count = len(self.task_widgets)
            self.lbl_task_count.setText(f"[{t('count_label')}: {count}]")
        if hasattr(self, "lbl_queue_head"):
            self.lbl_queue_head.setText(t("empty_queue_head"))
        if hasattr(self, "lbl_queue_sub"):
            self.lbl_queue_sub.setText(t("empty_queue_sub"))
        if hasattr(self, "lbl_queue_shortcuts"):
            self.lbl_queue_shortcuts.setText(t("empty_queue_tip"))
        if hasattr(self, "bar_header"):
            self.bar_header.setText(f'<span style="color: #818cf8; font-family: \'JetBrains Mono\', monospace; font-weight: 700;">{t("manifest_title")}</span>')
        if hasattr(self, "lbl_title_tag"):
            self.lbl_title_tag.setText(t("target_name_label"))
        if hasattr(self, "txt_title"):
            self.txt_title.setToolTip(t("target_name_tooltip"))
        if hasattr(self, "btn_mode_video"):
            self.btn_mode_video.setText(t("tab_video"))
        if hasattr(self, "btn_mode_audio"):
            self.btn_mode_audio.setText(t("tab_audio"))
        if hasattr(self, "lbl_resolutions"):
            self.lbl_resolutions.setText(t("format_matrix_label"))
        if hasattr(self, "lbl_format_label"):
            self.lbl_format_label.setText(t("container_label"))
        if hasattr(self, "lbl_codec_label"):
            self.lbl_codec_label.setText(t("codec_label"))
        if hasattr(self, "combo_codec"):
            cur_idx = self.combo_codec.currentIndex()
            self.combo_codec.blockSignals(True)
            self.combo_codec.clear()
            self.combo_codec.addItems([t("codec_h264"), t("codec_prores"), t("codec_source")])
            if cur_idx >= 0:
                self.combo_codec.setCurrentIndex(cur_idx)
            self.combo_codec.blockSignals(False)
        if hasattr(self, "btn_start_dl"):
            self._update_start_download_button_text()
        if self.current_parse_data:
            uploader = self.current_parse_data.get("uploader", "Unknown")
            if uploader and not uploader.startswith("@"):
                uploader = f"@{uploader}"
            if hasattr(self, "lbl_uploader"):
                self.lbl_uploader.setText(f"{t('meta_creator')} {uploader}")
            if hasattr(self, "lbl_duration"):
                self.lbl_duration.setText(f"{t('meta_duration')} {self.current_parse_data.get('duration', '--')}")
            if hasattr(self, "lbl_views"):
                self.lbl_views.setText(f"{t('meta_views')} {self.current_parse_data.get('views', '--')}")
            self._render_format_cards()

    def _init_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)
        elif self.icon_path and os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        self.tray_icon.setToolTip("Studio Download")
        self.tray_icon.activated.connect(self._on_tray_activated)
        self._update_tray_status()
        self.tray_icon.show()

    def _update_tray_status(self):
        if not hasattr(self, "tray_icon") or not self.tray_icon:
            return

        active_dls = [
            t for t in active_tasks.values()
            if t.get("status") in ("starting", "downloading", "muxing")
        ]

        # 1. Update Tooltip (hover over tray icon in taskbar)
        if not active_dls:
            self.tray_icon.setToolTip(t("tray_idle"))
        elif len(active_dls) == 1:
            dl = active_dls[0]
            title = dl.get("title", "Video")
            if len(title) > 28:
                title = title[:25] + "..."
            pct = dl.get("progress", 0)
            spd = dl.get("speed", "--")
            eta = dl.get("eta", "--")
            st = dl.get("status", "")
            if st == "muxing":
                tip = f"Studio Download\n[MENGGABUNGKAN] {title}\nFFmpeg: 99% | {eta}"
            else:
                tip = f"Studio Download\n[MENGUNDUH] {title}\n{pct:.1f}% | {spd} | ETA: {eta}"
            self.tray_icon.setToolTip(tip[:127])
        else:
            total_pct = sum(dl.get("progress", 0) for dl in active_dls) / len(active_dls)
            tip = f"Studio Download [{len(active_dls)} Unduhan Aktif]\nProgres: {total_pct:.1f}%\n"
            for dl in active_dls[:2]:
                short_t = dl.get("title", "")[:18]
                tip += f"• {short_t} ({dl.get('progress', 0):.0f}%)\n"
            self.tray_icon.setToolTip(tip.strip()[:127])

        # 2. Rebuild context menu with active task entries
        self._rebuild_tray_menu(active_dls)

    def _rebuild_tray_menu(self, active_dls=None):
        if not hasattr(self, "tray_icon") or not self.tray_icon:
            return

        if active_dls is None:
            active_dls = [
                t for t in active_tasks.values()
                if t.get("status") in ("starting", "downloading", "muxing")
            ]

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #111216;
                color: #f4f4f5;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 6px;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 18px 6px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1f2028;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background-color: #27272a;
                margin: 4px 6px;
            }
        """)

        # Active downloads header & item rows
        if active_dls:
            lbl_act = tray_menu.addAction(f"// {t('tray_active_header')}")
            lbl_act.setEnabled(False)
            for dl in active_dls[:4]:
                t_title = dl.get("title", "Video")
                if len(t_title) > 26:
                    t_title = t_title[:23] + "..."
                pct = dl.get("progress", 0)
                spd = dl.get("speed", "--")
                action_text = f"  [{pct:.1f}%] {t_title} ({spd})"
                task_action = tray_menu.addAction(action_text)
                task_action.triggered.connect(self._restore_from_tray)
            tray_menu.addSeparator()
        else:
            idle_act = tray_menu.addAction(f"  // {t('tray_no_active')}")
            idle_act.setEnabled(False)
            tray_menu.addSeparator()

        # Standard navigation
        act_open = tray_menu.addAction(t("tray_open"))
        if self.app_icon:
            act_open.setIcon(self.app_icon)
        act_open.triggered.connect(self._restore_from_tray)

        act_update = tray_menu.addAction(t("tray_check_updates"))
        act_update.triggered.connect(self._check_for_updates)

        tray_menu.addSeparator()

        act_quit = tray_menu.addAction(t("tray_quit"))
        act_quit.triggered.connect(self._force_quit)

        self.tray_icon.setContextMenu(tray_menu)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.show()
        if self.width() < 980 or self.height() < 660:
            self.resize(1020, 720)
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()

    def _check_for_updates(self):
        self._restore_from_tray()
        QMessageBox.information(
            self,
            "Studio Download",
            f"Studio Download v1.0\n\n{t('dialog_info')}: Anda menggunakan versi terbaru (Up to date)."
        )

    def _force_quit(self):
        running = any(
            t.get("status") in ("starting", "downloading", "muxing")
            for t in active_tasks.values()
        )
        if running:
            self._restore_from_tray()
            ans = QMessageBox.question(
                self, t("confirm_exit_title"), t("confirm_exit_msg"),
                QMessageBox.Yes | QMessageBox.No
            )
            if ans != QMessageBox.Yes:
                return

        for tid in list(active_tasks.keys()):
            if active_tasks[tid].get("status") in ("starting", "downloading", "muxing"):
                download_manager.cancel_download(tid)

        self._is_force_quitting = True
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        if getattr(self, "_is_force_quitting", False):
            event.accept()
            return

        # Background mode: hide window to system tray
        event.ignore()
        self.hide()
        if hasattr(self, "tray_icon") and self.tray_icon and self.tray_icon.isVisible():
            if not getattr(self, "_has_shown_tray_hint", False):
                self._has_shown_tray_hint = True
                self.tray_icon.showMessage(
                    "Studio Download",
                    t("tray_bg_tip"),
                    QSystemTrayIcon.Information,
                    2500
                )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "result_box") and self.result_box.isVisible() and self.current_parse_data:
            formats = self.current_parse_data.get("resolutions" if self.active_mode == "video" else "audio_presets", [])
            new_cols = self._calc_format_columns(len(formats))
            if getattr(self, "_current_grid_cols", None) != new_cols:
                self._render_format_cards()

    def changeEvent(self, event):
        super().changeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if hasattr(self, "txt_url") and self.txt_url.text():
                self.txt_url.clear()
        super().keyPressEvent(event)
