import re
import time
from PySide6.QtCore import Qt, Signal, QUrl, QRect, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QFrame, QSlider, QComboBox,
    QMessageBox, QSizePolicy, QApplication
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygon, QKeyEvent, QMouseEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from backend.i18n import t
from backend.parser import parse_time_str, format_duration, format_duration_hms, format_time_label


class TrimmerTimelineTrack(QWidget):
    """
    Custom interactive timeline track for the Visual Trimmer.
    Displays:
    - Base track groove
    - Highlighted active selection range [In Point to Out Point] in glowing cyan
    - Mark In marker flag (inverted triangle at top)
    - Mark Out marker flag (inverted triangle at top)
    - Current playhead cursor (white/yellow line with handle)
    """
    seek_started = Signal()
    seek_requested = Signal(float)       # emits timestamp in seconds
    seek_finished = Signal(float)        # emits timestamp on mouse release
    range_changed = Signal(float, float) # emits (in_sec, out_sec)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        self.total_duration_sec = 0.0
        self.current_pos_sec = 0.0
        self.in_sec = 0.0
        self.out_sec = 0.0

        self._is_dragging_playhead = False
        self._last_seek_time = 0.0

    def set_duration(self, seconds: float):
        self.total_duration_sec = max(0.0, float(seconds or 0.0))
        if self.out_sec <= 0.0 and self.total_duration_sec > 0.0:
            self.out_sec = self.total_duration_sec
        self.update()

    def set_position(self, seconds: float):
        self.current_pos_sec = max(0.0, float(seconds or 0.0))
        self.update()

    def set_in_point(self, seconds: float):
        self.in_sec = max(0.0, min(float(seconds or 0.0), self.total_duration_sec if self.total_duration_sec > 0 else 999999))
        self.update()
        self.range_changed.emit(self.in_sec, self.out_sec)

    def set_out_point(self, seconds: float):
        self.out_sec = max(0.0, min(float(seconds or 0.0), self.total_duration_sec if self.total_duration_sec > 0 else 999999))
        self.update()
        self.range_changed.emit(self.in_sec, self.out_sec)

    def _sec_to_x(self, sec: float, track_w: int, margin: int) -> int:
        if self.total_duration_sec <= 0:
            return margin
        ratio = max(0.0, min(1.0, sec / self.total_duration_sec))
        return int(margin + ratio * track_w)

    def _x_to_sec(self, x: int, track_w: int, margin: int) -> float:
        if self.total_duration_sec <= 0 or track_w <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, (x - margin) / track_w))
        return ratio * self.total_duration_sec

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        margin = 12
        track_w = max(10, self.width() - (margin * 2))
        track_y = 13
        track_h = 12

        # 1. Base Groove Track
        painter.setPen(QPen(QColor("#27272a"), 1))
        painter.setBrush(QBrush(QColor("#18181b")))
        painter.drawRoundedRect(margin, track_y, track_w, track_h, 3, 3)

        if self.total_duration_sec > 0:
            in_x = self._sec_to_x(self.in_sec, track_w, margin)
            out_x = self._sec_to_x(self.out_sec, track_w, margin)

            # 2. Highlighted Selection Range (Soft Sky Accent)
            if out_x > in_x:
                rw = out_x - in_x
                # Fill
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(56, 189, 248, 45)))
                painter.drawRect(in_x, track_y, rw, track_h)

                # Crisp Top & Bottom Accent Lines
                painter.setPen(QPen(QColor("#38bdf8"), 1.5))
                painter.drawLine(in_x, track_y, out_x, track_y)
                painter.drawLine(in_x, track_y + track_h, out_x, track_y + track_h)

            # 3. Mark In Marker (Sleek 2px sky line with precision bracket notch)
            painter.setPen(QPen(QColor("#38bdf8"), 2))
            painter.drawLine(in_x, track_y - 4, in_x, track_y + track_h + 4)
            # In bracket top tab: [
            painter.fillRect(in_x, track_y - 5, 5, 3, QColor("#38bdf8"))
            painter.fillRect(in_x, track_y + track_h + 2, 5, 3, QColor("#38bdf8"))

            # 4. Mark Out Marker (Sleek 2px amber line with precision bracket notch)
            painter.setPen(QPen(QColor("#f59e0b"), 2))
            painter.drawLine(out_x, track_y - 4, out_x, track_y + track_h + 4)
            # Out bracket top tab: ]
            painter.fillRect(out_x - 5, track_y - 5, 5, 3, QColor("#f59e0b"))
            painter.fillRect(out_x - 5, track_y + track_h + 2, 5, 3, QColor("#f59e0b"))

            # 5. Current Playhead Cursor (White Line + Precision Pill Cap)
            curr_x = self._sec_to_x(self.current_pos_sec, track_w, margin)
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawLine(curr_x, 6, curr_x, self.height() - 6)

            # Playhead pill cap at top
            painter.setPen(QPen(QColor("#09090b"), 1))
            painter.setBrush(QBrush(QColor("#ffffff")))
            painter.drawRoundedRect(curr_x - 4, 3, 8, 8, 2, 2)

        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            margin = 12
            track_w = max(10, self.width() - (margin * 2))
            sec = self._x_to_sec(event.pos().x(), track_w, margin)
            self._is_dragging_playhead = True
            self.current_pos_sec = sec
            self._last_seek_time = time.time()
            self.seek_started.emit()
            self.seek_requested.emit(sec)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        margin = 12
        track_w = max(10, self.width() - (margin * 2))
        sec = self._x_to_sec(event.pos().x(), track_w, margin)
        if self._is_dragging_playhead and (event.buttons() & Qt.LeftButton):
            self.current_pos_sec = sec
            self.update() # Visual cursor updates at 60 FPS immediately!
            now = time.time()
            if (now - getattr(self, "_last_seek_time", 0.0)) >= 0.065: # Throttle decoder seeks to ~15 fps
                self._last_seek_time = now
                self.seek_requested.emit(sec)

        # Update hover tooltip
        self.setToolTip(f"Posisi: {format_duration_hms(int(sec))}")

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self._is_dragging_playhead:
            margin = 12
            track_w = max(10, self.width() - (margin * 2))
            sec = self._x_to_sec(event.pos().x(), track_w, margin)
            self._is_dragging_playhead = False
            self.current_pos_sec = sec
            self.seek_requested.emit(sec)
            self.seek_finished.emit(sec)
            self.update()


class VisualTrimmerDialog(QDialog):
    """
    Studio Visual Trimmer // Widescreen Modal (Hybrid Option A & B).
    Embedded Qt Multimedia Player with real-time video preview,
    timeline scrubbing, Mark In/Out, and instant synchronization to download queue.
    """
    clips_applied = Signal(list)

    def __init__(self, video_data: dict, existing_clips: list = None, size_estimator=None, parent=None):
        super().__init__(parent)
        self.video_data = video_data or {}
        self.size_estimator = size_estimator
        self.clips = []

        self.setWindowTitle(t("trimmer_dlg_title"))
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(1120, 700)
        self.setMinimumSize(880, 580)

        self._drag_pos = None
        self._is_previewing_clip = False
        self._clip_preview_end = 0.0
        self._was_playing_before_scrub = False

        # Duration & Stream Info
        self.duration_sec = float(self.video_data.get("duration_seconds") or 0.0)
        self.preview_options = self.video_data.get("preview_options") or []
        self.preview_url = self.video_data.get("preview_url") or self.video_data.get("webpage_url") or ""

        # If preview_options is empty or only 1 item, try building from raw formats if present
        raw_fmt = self.video_data.get("raw_formats") or self.video_data.get("formats")
        if (not self.preview_options or len(self.preview_options) <= 1) and raw_fmt:
            dyn_opts = self._build_preview_options_from_formats(raw_fmt)
            if dyn_opts:
                self.preview_options = dyn_opts

        if not self.preview_options and self.preview_url:
            self.preview_options = [{"label": "Direct Stream", "url": self.preview_url, "height": 360}]

        # Player setup
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.in_sec = 0.0
        self.out_sec = self.duration_sec if self.duration_sec > 0 else 0.0

        self._init_ui()
        self._apply_styles()
        self._setup_player_events()

        # Populate existing clips if provided
        if existing_clips:
            for c in existing_clips:
                self._add_clip_to_list(c.get("start", 0), c.get("end", int(self.duration_sec or 60)), c.get("label", ""))
        else:
            self.lbl_sidebar_title.setText(f"{t('trimmer_clips_title')} (0)")

        # Start loading stream
        if self.preview_url:
            self._load_stream(self.preview_url)
        else:
            self.lbl_stream_status.setText(t("trimmer_stream_err"))

    def _build_preview_options_from_formats(self, formats: list) -> list:
        opts = []
        video_direct = [f for f in formats if f.get("url") and f.get("vcodec") != "none" and f.get("height")]
        tag_map = {4320: "8K", 2160: "4K", 1440: "2K", 1080: "FHD", 720: "HD", 480: "SD", 360: "Fast Scrub", 240: "Low", 144: "Min"}
        standard_heights = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
        found_heights = set(f.get("height") for f in video_direct if f.get("height"))
        all_heights = sorted(list(set(standard_heights) | found_heights), reverse=True)

        for h in all_heights:
            matches = [f for f in video_direct if f.get("height") == h and f.get("url")]
            if matches:
                def _fmt_prio(fmt):
                    has_aud = 1 if fmt.get("acodec") != "none" else 0
                    is_mp4 = 1 if fmt.get("ext") == "mp4" else 0
                    vc = (fmt.get("vcodec") or "").lower()
                    is_h264 = 1 if ("avc" in vc or "h264" in vc) else 0
                    br = fmt.get("tbr") or fmt.get("vbr") or 0
                    return (has_aud, is_mp4, is_h264, br)
                matches.sort(key=_fmt_prio, reverse=True)
                best = matches[0]
                tag = tag_map.get(h, "")
                lbl = f"{h}p ({tag})" if tag else f"{h}p"
                opts.append({
                    "height": h,
                    "label": lbl,
                    "url": best.get("url"),
                    "format_id": best.get("format_id"),
                    "has_audio": best.get("acodec") != "none"
                })
        return opts

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)

        # Central container Frame (with border)
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("trimmerMainFrame")
        frame_layout = QVBoxLayout(self.main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        root_layout.addWidget(self.main_frame)

        # 1. Custom Top Title Bar
        title_bar = QFrame(self.main_frame)
        title_bar.setObjectName("trimmerTitleBar")
        title_bar.setFixedHeight(44)
        t_layout = QHBoxLayout(title_bar)
        t_layout.setContentsMargins(16, 0, 14, 0)
        t_layout.setSpacing(10)

        lbl_title = QLabel("TRIM", title_bar)
        lbl_title.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 800; letter-spacing: 0.5px;")
        t_layout.addWidget(lbl_title)

        video_title = self.video_data.get("title", "")
        if video_title:
            lbl_vid = QLabel(f"// {video_title[:55]}{'...' if len(video_title) > 55 else ''}", title_bar)
            lbl_vid.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
            t_layout.addWidget(lbl_vid)

        t_layout.addStretch()

        # Window controls: Maximize & Close (Clean text buttons, 100% reliable)
        self.btn_maximize = QPushButton("MAX", title_bar)
        self.btn_maximize.setObjectName("winCtrlBtn")
        self.btn_maximize.setFixedSize(58, 26)
        self.btn_maximize.setToolTip("Perbesar Layar Penuh (Widescreen)")
        self.btn_maximize.clicked.connect(self._toggle_maximize)
        t_layout.addWidget(self.btn_maximize)

        btn_close = QPushButton("CLOSE", title_bar)
        btn_close.setObjectName("winCloseBtn")
        btn_close.setFixedSize(58, 26)
        btn_close.setToolTip("Tutup Dialog (Esc)")
        btn_close.clicked.connect(self.reject)
        t_layout.addWidget(btn_close)

        frame_layout.addWidget(title_bar)

        # 2. Main Content Split (Left: Player & Controls, Right: Saved Clips Panel)
        content_h = QHBoxLayout()
        content_h.setContentsMargins(14, 12, 14, 10)
        content_h.setSpacing(14)

        # --- LEFT COLUMN: Video Player & Timeline Controls ---
        left_v = QVBoxLayout()
        left_v.setSpacing(8)

        # Video Viewport Container
        self.video_container = QFrame(self.main_frame)
        self.video_container.setObjectName("videoContainer")
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vc_layout = QVBoxLayout(self.video_container)
        vc_layout.setContentsMargins(0, 0, 0, 0)
        vc_layout.setSpacing(0)

        self.video_widget = QVideoWidget(self.video_container)
        self.player.setVideoOutput(self.video_widget)
        vc_layout.addWidget(self.video_widget)

        # Status text overlay (for buffering / loading notice)
        self.lbl_stream_status = QLabel(t("trimmer_stream_loading"), self.video_container)
        self.lbl_stream_status.setObjectName("streamStatusOverlay")
        self.lbl_stream_status.setAlignment(Qt.AlignCenter)
        self.lbl_stream_status.setFixedHeight(22)
        vc_layout.addWidget(self.lbl_stream_status)

        left_v.addWidget(self.video_container, 1)

        # Timeline Track
        self.timeline_track = TrimmerTimelineTrack(self.main_frame)
        self.timeline_track.set_duration(self.duration_sec)
        self.timeline_track.set_in_point(self.in_sec)
        self.timeline_track.set_out_point(self.out_sec)
        self.timeline_track.seek_started.connect(self._on_scrub_started)
        self.timeline_track.seek_requested.connect(self._on_seek_requested)
        self.timeline_track.seek_finished.connect(self._on_scrub_finished)
        self.timeline_track.range_changed.connect(self._on_timeline_range_changed)
        left_v.addWidget(self.timeline_track)

        # Transport & Volume Toolbar
        transport_h = QHBoxLayout()
        transport_h.setSpacing(6)

        self.btn_jump_back_5 = QPushButton("-5s", self.main_frame)
        self.btn_jump_back_5.setObjectName("btnTransport")
        self.btn_jump_back_5.setToolTip("Mundur 5 detik (Panah Kiri)")
        self.btn_jump_back_5.clicked.connect(lambda: self._seek_relative(-5.0))
        transport_h.addWidget(self.btn_jump_back_5)

        self.btn_jump_back_1 = QPushButton("-1s", self.main_frame)
        self.btn_jump_back_1.setObjectName("btnTransport")
        self.btn_jump_back_1.setToolTip("Mundur 1 detik")
        self.btn_jump_back_1.clicked.connect(lambda: self._seek_relative(-1.0))
        transport_h.addWidget(self.btn_jump_back_1)

        self.btn_play_pause = QPushButton("PLAY", self.main_frame)
        self.btn_play_pause.setObjectName("btnPlayPause")
        self.btn_play_pause.setMinimumWidth(80)
        self.btn_play_pause.setToolTip("Putar / Jeda Video (Spasi)")
        self.btn_play_pause.clicked.connect(self._toggle_play_pause)
        transport_h.addWidget(self.btn_play_pause)

        self.btn_jump_fwd_1 = QPushButton("+1s", self.main_frame)
        self.btn_jump_fwd_1.setObjectName("btnTransport")
        self.btn_jump_fwd_1.setToolTip("Maju 1 detik")
        self.btn_jump_fwd_1.clicked.connect(lambda: self._seek_relative(1.0))
        transport_h.addWidget(self.btn_jump_fwd_1)

        self.btn_jump_fwd_5 = QPushButton("+5s", self.main_frame)
        self.btn_jump_fwd_5.setObjectName("btnTransport")
        self.btn_jump_fwd_5.setToolTip("Maju 5 detik (Panah Kanan)")
        self.btn_jump_fwd_5.clicked.connect(lambda: self._seek_relative(5.0))
        transport_h.addWidget(self.btn_jump_fwd_5)

        # Current Time / Total Time Display
        self.lbl_timecode = QLabel("00:00:00 / 00:00:00", self.main_frame)
        self.lbl_timecode.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700; padding: 0 10px;")
        transport_h.addWidget(self.lbl_timecode)

        transport_h.addStretch()

        # Stream Quality Label & Dropdown (Clean text, no icons!)
        lbl_qual = QLabel("QUALITY:", self.main_frame)
        lbl_qual.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; margin-left: 8px;")
        transport_h.addWidget(lbl_qual)

        self.combo_quality = QComboBox(self.main_frame)
        self.combo_quality.setObjectName("comboQuality")
        self.combo_quality.setFixedHeight(26)
        self.combo_quality.setToolTip("Pilih resolusi pratinjau (Max hingga 144p)")
        self.combo_quality.setStyleSheet("""
            QComboBox#comboQuality {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 2px 8px;
            }
            QComboBox#comboQuality:hover {
                border-color: #38bdf8;
            }
            QComboBox#comboQuality QAbstractItemView {
                background-color: #14151b;
                border: 1px solid #27272a;
                color: #f4f4f5;
                selection-background-color: #38bdf8;
                selection-color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
            }
        """)
        for opt in self.preview_options:
            self.combo_quality.addItem(opt.get("label", "Stream"), opt.get("url"))

        def_q_idx = 0
        for i, opt in enumerate(self.preview_options):
            if opt.get("height") == 360 or "Fast Scrub" in opt.get("label", ""):
                def_q_idx = i
                break
            elif opt.get("height") == 480 and def_q_idx == 0:
                def_q_idx = i
        if self.combo_quality.count() > def_q_idx:
            self.combo_quality.setCurrentIndex(def_q_idx)

        self.combo_quality.currentIndexChanged.connect(self._on_quality_changed)
        transport_h.addWidget(self.combo_quality)

        # Volume Label & Slider (Clean text, no icons!)
        lbl_vol = QLabel("VOL:", self.main_frame)
        lbl_vol.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; margin-left: 10px;")
        transport_h.addWidget(lbl_vol)

        self.slider_vol = QSlider(Qt.Horizontal, self.main_frame)
        self.slider_vol.setFixedWidth(68)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.valueChanged.connect(self._on_volume_changed)
        self.audio_output.setVolume(0.8)
        transport_h.addWidget(self.slider_vol)

        left_v.addLayout(transport_h)

        # In & Out Slicing Control Bar
        trim_h = QHBoxLayout()
        trim_h.setSpacing(8)

        self.btn_set_in = QPushButton(t("trimmer_mark_in"), self.main_frame)
        self.btn_set_in.setObjectName("btnMarkIn")
        self.btn_set_in.setToolTip("Tandai Titik Mulai di Posisi Saat Ini (Shortcut: I)")
        self.btn_set_in.clicked.connect(self._mark_current_in)
        trim_h.addWidget(self.btn_set_in)

        self.txt_in = QLineEdit(self.main_frame)
        self.txt_in.setObjectName("txtTimeCode")
        self.txt_in.setFixedWidth(85)
        self.txt_in.setAlignment(Qt.AlignCenter)
        self.txt_in.setText(format_duration_hms(int(self.in_sec)))
        self.txt_in.textChanged.connect(self._on_txt_in_changed)
        trim_h.addWidget(self.txt_in)

        lbl_sep = QLabel("TO", self.main_frame)
        lbl_sep.setStyleSheet("color: #52525b; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;")
        trim_h.addWidget(lbl_sep)

        self.btn_set_out = QPushButton(t("trimmer_mark_out"), self.main_frame)
        self.btn_set_out.setObjectName("btnMarkOut")
        self.btn_set_out.setToolTip("Tandai Titik Selesai di Posisi Saat Ini (Shortcut: O)")
        self.btn_set_out.clicked.connect(self._mark_current_out)
        trim_h.addWidget(self.btn_set_out)

        self.txt_out = QLineEdit(self.main_frame)
        self.txt_out.setObjectName("txtTimeCode")
        self.txt_out.setFixedWidth(85)
        self.txt_out.setAlignment(Qt.AlignCenter)
        self.txt_out.setText(format_duration_hms(int(self.out_sec)))
        self.txt_out.textChanged.connect(self._on_txt_out_changed)
        trim_h.addWidget(self.txt_out)

        self.lbl_cur_range_info = QLabel("", self.main_frame)
        self.lbl_cur_range_info.setObjectName("lblCurRangeInfo")
        trim_h.addWidget(self.lbl_cur_range_info)

        trim_h.addStretch()

        self.btn_add_clip = QPushButton(t("trimmer_btn_add_clip"), self.main_frame)
        self.btn_add_clip.setObjectName("btnAddClipPrimary")
        self.btn_add_clip.setToolTip("Simpan Rentang [In - Out] ke Daftar Klip (Shortcut: Enter)")
        self.btn_add_clip.clicked.connect(self._on_add_current_clip)
        trim_h.addWidget(self.btn_add_clip)

        left_v.addLayout(trim_h)

        content_h.addLayout(left_v, 1)

        # --- RIGHT COLUMN: Saved Clips Ledger Panel ---
        right_panel = QFrame(self.main_frame)
        right_panel.setObjectName("clipsSidebar")
        right_panel.setFixedWidth(310)
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(12, 12, 12, 12)
        rp_layout.setSpacing(8)

        # Sidebar Title
        self.lbl_sidebar_title = QLabel(t("trimmer_clips_title"), right_panel)
        self.lbl_sidebar_title.setStyleSheet("color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        rp_layout.addWidget(self.lbl_sidebar_title)

        # Scroll Area for Clips
        self.scroll_clips = QScrollArea(right_panel)
        self.scroll_clips.setWidgetResizable(True)
        self.scroll_clips.setStyleSheet("background: transparent; border: none;")

        self.clips_container = QWidget()
        self.clips_container.setStyleSheet("background: transparent;")
        self.clips_layout = QVBoxLayout(self.clips_container)
        self.clips_layout.setContentsMargins(0, 0, 0, 0)
        self.clips_layout.setSpacing(6)

        # Empty state label when no clips exist
        self.lbl_no_clips = QLabel(t("trimmer_no_clips"), self.clips_container)
        self.lbl_no_clips.setStyleSheet("color: #52525b; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; padding: 24px 8px;")
        self.lbl_no_clips.setAlignment(Qt.AlignCenter)
        self.clips_layout.addWidget(self.lbl_no_clips)

        self.clips_layout.addStretch()

        self.scroll_clips.setWidget(self.clips_container)
        rp_layout.addWidget(self.scroll_clips, 1)

        content_h.addWidget(right_panel)

        frame_layout.addLayout(content_h, 1)

        # 3. Bottom Action Footer
        footer = QFrame(self.main_frame)
        footer.setObjectName("trimmerFooter")
        footer.setFixedHeight(50)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(16, 0, 16, 0)
        f_layout.setSpacing(10)

        lbl_tips = QLabel("SHORTCUTS: Space = Play/Pause | I = Set In | O = Set Out | Enter = Save Clip | Left/Right = Seek 5s", footer)
        lbl_tips.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        f_layout.addWidget(lbl_tips)

        f_layout.addStretch()

        btn_cancel = QPushButton(t("trimmer_btn_cancel"), footer)
        btn_cancel.setObjectName("btnFooterCancel")
        btn_cancel.clicked.connect(self.reject)
        f_layout.addWidget(btn_cancel)

        self.btn_apply = QPushButton(t("trimmer_btn_apply"), footer)
        self.btn_apply.setObjectName("btnFooterApply")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        f_layout.addWidget(self.btn_apply)

        frame_layout.addWidget(footer)

        self._update_range_info()

    def _apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
            QFrame#trimmerMainFrame {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QFrame#trimmerTitleBar {
                background-color: #111216;
                border-bottom: 1px solid #1f2028;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QFrame#videoContainer {
                background-color: #000000;
                border: 1px solid #1f2028;
                border-radius: 6px;
            }
            QFrame#clipsSidebar {
                background-color: #111216;
                border: 1px solid #1f2028;
                border-radius: 6px;
            }
            QFrame#trimmerFooter {
                background-color: #111216;
                border-top: 1px solid #1f2028;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QLabel#streamStatusOverlay {
                background-color: rgba(9, 9, 11, 0.85);
                color: #71717a;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                border-top: 1px solid #1f2028;
            }
            QPushButton#winCtrlBtn {
                background-color: transparent;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton#winCtrlBtn:hover {
                background-color: #27272a;
                color: #f4f4f5;
                border-color: #38bdf8;
            }
            QPushButton#winCloseBtn {
                background-color: transparent;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton#winCloseBtn:hover {
                background-color: #e11d48;
                color: #ffffff;
                border-color: #e11d48;
            }
            QPushButton#btnTransport {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #d4d4d8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
            }
            QPushButton#btnTransport:hover {
                background-color: #1f2028;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton#btnPlayPause {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 800;
                padding: 4px 16px;
            }
            QPushButton#btnPlayPause:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton#btnMarkIn {
                background-color: #14151b;
                border: 1px solid #0284c7;
                border-radius: 4px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 5px 12px;
            }
            QPushButton#btnMarkIn:hover {
                background-color: #0284c7;
                color: #ffffff;
            }
            QPushButton#btnMarkOut {
                background-color: #14151b;
                border: 1px solid #d97706;
                border-radius: 4px;
                color: #fbbf24;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 5px 12px;
            }
            QPushButton#btnMarkOut:hover {
                background-color: #d97706;
                color: #ffffff;
            }
            QLineEdit#txtTimeCode {
                background-color: #0c0d11;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11.5px;
                font-weight: 700;
                padding: 4px;
            }
            QLineEdit#txtTimeCode:focus {
                border-color: #38bdf8;
            }
            QPushButton#btnAddClipPrimary {
                background-color: #14151b;
                border: 1px solid #38bdf8;
                border-radius: 4px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 5px 14px;
            }
            QPushButton#btnAddClipPrimary:hover {
                background-color: #38bdf8;
                color: #09090b;
            }
            QPushButton#btnFooterCancel {
                background-color: transparent;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
                padding: 6px 16px;
            }
            QPushButton#btnFooterCancel:hover {
                background-color: #1f2028;
                color: #f4f4f5;
            }
            QPushButton#btnFooterApply {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11.5px;
                font-weight: 800;
                padding: 6px 20px;
            }
            QPushButton#btnFooterApply:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #27272a;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                margin-top: -3px;
                margin-bottom: -3px;
                border-radius: 5px;
                background: #f4f4f5;
            }
        """)

    def _setup_player_events(self):
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.durationChanged.connect(self._on_player_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

    def _load_stream(self, stream_url: str):
        if not stream_url:
            return
        try:
            self.lbl_stream_status.setText(f"{t('trimmer_stream_loading')} ({stream_url[:45]}...)")
            self.player.setSource(QUrl(stream_url))
            self.player.play()  # Start playback & decoding pipeline so frames render immediately!
        except Exception as e:
            self.lbl_stream_status.setText(f"Galat muat stream: {e}")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.BufferingMedia:
            self.lbl_stream_status.setText(t("trimmer_stream_loading"))
        elif status in (QMediaPlayer.MediaStatus.BufferedMedia, QMediaPlayer.MediaStatus.LoadedMedia):
            self.lbl_stream_status.setText(t("trimmer_stream_ready"))

    def _toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self._is_previewing_clip = False
            self.player.play()

    def _seek_relative(self, delta_sec: float):
        cur_ms = self.player.position()
        target_ms = max(0, int(cur_ms + delta_sec * 1000))
        self.player.setPosition(target_ms)

    def _on_scrub_started(self):
        self._was_playing_before_scrub = (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)
        if self._was_playing_before_scrub:
            self.player.pause()

    def _on_scrub_finished(self, sec: float):
        if getattr(self, "_was_playing_before_scrub", False):
            self.player.play()
            self._was_playing_before_scrub = False

    def _on_seek_requested(self, sec: float):
        self._is_previewing_clip = False
        target_ms = int(sec * 1000)
        # If player is in StoppedState, prime the pipeline so frames decode on seeking
        if self.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState:
            self.player.play()
            self.player.pause()
        self.player.setPosition(target_ms)

    def _on_quality_changed(self, index: int):
        if index < 0 or not getattr(self, "preview_options", None) or index >= len(self.preview_options):
            return
        selected_opt = self.preview_options[index]
        new_url = selected_opt.get("url")
        if not new_url:
            return

        cur_ms = self.player.position()
        was_playing = (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState)

        self._load_stream(new_url)

        from PySide6.QtCore import QTimer
        def restore():
            if cur_ms > 0:
                self.player.setPosition(cur_ms)
            if was_playing:
                self.player.play()
        QTimer.singleShot(300, restore)
        self.lbl_stream_status.setText(f"Kualitas stream diubah: {selected_opt.get('label')}")

    def _on_player_position_changed(self, pos_ms: int):
        pos_sec = pos_ms / 1000.0
        self.timeline_track.set_position(pos_sec)

        dur_sec = max(int(self.duration_sec), int(self.player.duration() / 1000))
        cur_str = format_duration_hms(int(pos_sec))
        dur_str = format_duration_hms(dur_sec)
        self.lbl_timecode.setText(f"{cur_str} / {dur_str}")

        # Check if playing clip preview
        if self._is_previewing_clip and pos_sec >= self._clip_preview_end:
            self.player.pause()
            self._is_previewing_clip = False

    def _on_player_duration_changed(self, dur_ms: int):
        if dur_ms > 0:
            actual_sec = dur_ms / 1000.0
            old_dur = self.duration_sec
            if actual_sec > self.duration_sec or self.duration_sec <= 0:
                self.duration_sec = actual_sec
                self.timeline_track.set_duration(self.duration_sec)
                # Keep OUT marker at the end if it was at old_dur or <= 0
                if self.out_sec <= 0 or self.out_sec == old_dur:
                    self.out_sec = actual_sec
                    self.txt_out.setText(format_duration_hms(int(actual_sec)))
                    self.timeline_track.set_out_point(actual_sec)
                    self._update_range_info()
            self.lbl_stream_status.setText(t("trimmer_stream_ready"))

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play_pause.setText("PAUSE")
        else:
            self.btn_play_pause.setText("PLAY")

    def _on_player_error(self, error, error_string):
        self.lbl_stream_status.setText(f"{t('trimmer_stream_err')} ({error_string})")

    def _on_volume_changed(self, val: int):
        self.audio_output.setVolume(val / 100.0)

    # --- In & Out Markers ---
    def _mark_current_in(self):
        curr_sec = int(self.player.position() / 1000.0)
        self.in_sec = curr_sec
        self.txt_in.setText(format_duration_hms(curr_sec))
        self.timeline_track.set_in_point(curr_sec)
        self._update_range_info()

    def _mark_current_out(self):
        curr_sec = int(self.player.position() / 1000.0)
        self.out_sec = curr_sec
        self.txt_out.setText(format_duration_hms(curr_sec))
        self.timeline_track.set_out_point(curr_sec)
        self._update_range_info()

    def _on_txt_in_changed(self, text: str):
        sec = parse_time_str(text)
        self.in_sec = sec
        self.timeline_track.set_in_point(sec)
        self._update_range_info()

    def _on_txt_out_changed(self, text: str):
        sec = parse_time_str(text)
        self.out_sec = sec
        self.timeline_track.set_out_point(sec)
        self._update_range_info()

    def _on_timeline_range_changed(self, in_sec: float, out_sec: float):
        self.in_sec = in_sec
        self.out_sec = out_sec
        self.txt_in.setText(format_duration_hms(int(in_sec)))
        self.txt_out.setText(format_duration_hms(int(out_sec)))
        self._update_range_info()

    def _update_range_info(self):
        diff = max(0, int(self.out_sec - self.in_sec))
        if self.out_sec > self.in_sec:
            dur_str = format_duration_hms(diff)
            est_str = ""
            if callable(self.size_estimator):
                try:
                    est_str = self.size_estimator(diff)
                except Exception:
                    pass
            clean_est = est_str.lstrip("~").strip() if est_str else ""
            txt = f"DURATION: {dur_str}  •  EST: ~{clean_est}" if clean_est else f"DURATION: {dur_str}"
            self.lbl_cur_range_info.setText(txt)
            self.lbl_cur_range_info.setStyleSheet("color: #fbbf24; background: #16171d; border: 1px solid #27272a; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; padding: 4px 8px;")
        else:
            self.lbl_cur_range_info.setText("INVALID RANGE: OUT <= IN")
            self.lbl_cur_range_info.setStyleSheet("color: #f43f5e; background: #16171d; border: 1px solid rgba(244,63,94,0.4); border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; padding: 4px 8px;")

    # --- Clips Sidebar Management ---
    def _on_add_current_clip(self):
        if self.out_sec <= self.in_sec:
            QMessageBox.warning(self, "Peringatan", "Titik selesai (OUT) harus lebih besar daripada titik mulai (IN)!")
            return
        self._add_clip_to_list(int(self.in_sec), int(self.out_sec))

    def _add_clip_to_list(self, start_sec: int, end_sec: int, label: str = ""):
        idx = len(self.clips) + 1
        clip_card = QFrame(self.clips_container)
        clip_card.setObjectName("clipCardItem")
        clip_card.setStyleSheet("""
            QFrame#clipCardItem {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-left: 3px solid #38bdf8;
                border-radius: 4px;
                padding: 4px;
            }
            QFrame#clipCardItem:hover {
                border-color: #3f3f46;
                border-left-color: #38bdf8;
                background-color: #1a1c24;
            }
        """)

        card_layout = QVBoxLayout(clip_card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)

        top_h = QHBoxLayout()
        top_h.setSpacing(6)
        lbl_num = QLabel(f"CLIP #{idx}", clip_card)
        lbl_num.setStyleSheet("color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 800;")
        top_h.addWidget(lbl_num)

        dur_sec = max(0, end_sec - start_sec)
        lbl_range = QLabel(f"{format_duration_hms(start_sec)} — {format_duration_hms(end_sec)}", clip_card)
        lbl_range.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;")
        top_h.addWidget(lbl_range)

        top_h.addStretch()

        # Clean typographic buttons - NO MORE EMPTY SQUARE GLYPHS OR CLIPPED TEXT!
        btn_play = QPushButton("PLAY", clip_card)
        btn_play.setFixedSize(48, 24)
        btn_play.setToolTip("Pratinjau Putar Klip Ini")
        btn_play.setStyleSheet("""
            QPushButton {
                background-color: #1f2028;
                border: 1px solid #27272a;
                border-radius: 4px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #27272a;
                border-color: #38bdf8;
                color: #7dd3fc;
            }
        """)
        btn_play.clicked.connect(lambda: self._preview_clip(start_sec, end_sec))
        top_h.addWidget(btn_play)

        btn_del = QPushButton("DEL", clip_card)
        btn_del.setFixedSize(42, 24)
        btn_del.setToolTip("Hapus Klip")
        btn_del.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid rgba(244, 63, 94, 0.35);
                border-radius: 4px;
                color: #f43f5e;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 700;
                padding: 0px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #e11d48;
                border-color: #e11d48;
                color: #ffffff;
            }
        """)
        btn_del.clicked.connect(lambda: self._remove_clip(clip_card))
        top_h.addWidget(btn_del)

        card_layout.addLayout(top_h)

        # Bottom meta
        bot_h = QHBoxLayout()
        est_str = ""
        if callable(self.size_estimator):
            try:
                est_str = self.size_estimator(dur_sec)
            except Exception:
                pass
        clean_est = est_str.lstrip("~").strip() if est_str else ""
        dur_txt = f"Duration: {format_duration_hms(dur_sec)}" + (f"  •  ~{clean_est}" if clean_est else "")
        lbl_dur = QLabel(dur_txt, clip_card)
        lbl_dur.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        bot_h.addWidget(lbl_dur)

        bot_h.addStretch()
        card_layout.addLayout(bot_h)

        clip_data = {
            "widget": clip_card,
            "start": start_sec,
            "end": end_sec,
            "duration": dur_sec,
            "label": label or f"Klip #{idx}",
            "time_tag": f"[{format_time_label(start_sec)}-{format_time_label(end_sec)}]",
            "start_str": format_duration_hms(start_sec),
            "end_str": format_duration_hms(end_sec),
            "is_valid": True
        }
        clip_card.clip_data = clip_data

        # Hide empty state label if present
        if hasattr(self, "lbl_no_clips"):
            self.lbl_no_clips.hide()

        # Insert before the stretch item
        self.clips_layout.insertWidget(self.clips_layout.count() - 1, clip_card)
        self.clips.append(clip_data)

        self.lbl_sidebar_title.setText(f"{t('trimmer_clips_title')} ({len(self.clips)})")

    def _preview_clip(self, start_sec: int, end_sec: int):
        self.in_sec = start_sec
        self.out_sec = end_sec
        self.txt_in.setText(format_duration_hms(start_sec))
        self.txt_out.setText(format_duration_hms(end_sec))
        self.timeline_track.set_in_point(start_sec)
        self.timeline_track.set_out_point(end_sec)

        # Seek and play
        self._is_previewing_clip = True
        self._clip_preview_end = float(end_sec)
        self.player.setPosition(start_sec * 1000)
        self.player.play()

    def _remove_clip(self, clip_card):
        clip_obj = getattr(clip_card, "clip_data", None)
        if clip_obj in self.clips:
            self.clips.remove(clip_obj)
        self.clips_layout.removeWidget(clip_card)
        clip_card.deleteLater()
        if not self.clips and hasattr(self, "lbl_no_clips"):
            self.lbl_no_clips.show()
        self.lbl_sidebar_title.setText(f"{t('trimmer_clips_title')} ({len(self.clips)})")

    def _on_apply_clicked(self):
        if not self.clips:
            # If no clip in list, but current range is valid, add current range
            if self.out_sec > self.in_sec:
                self._on_add_current_clip()
            else:
                QMessageBox.warning(self, "Peringatan", "Belum ada klip yang ditandai untuk diterapkan.")
                return

        # Prepare clean return list
        result_clips = []
        for c in self.clips:
            result_clips.append({
                "start": c["start"],
                "end": c["end"],
                "start_str": c["start_str"],
                "end_str": c["end_str"],
                "duration": c["duration"],
                "label": c["label"],
                "time_tag": c["time_tag"],
                "is_valid": True
            })

        self.clips_applied.emit(result_clips)
        self.player.stop()
        self.accept()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.btn_maximize.setText("MAX")
        else:
            self.showMaximized()
            self.btn_maximize.setText("RESTORE")

    # --- Keyboard Shortcuts ---
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key == Qt.Key_Space:
            self._toggle_play_pause()
            event.accept()
        elif key in (Qt.Key_I, Qt.Key_BracketLeft):
            self._mark_current_in()
            event.accept()
        elif key in (Qt.Key_O, Qt.Key_BracketRight):
            self._mark_current_out()
            event.accept()
        elif key == Qt.Key_Left:
            self._seek_relative(-5.0)
            event.accept()
        elif key == Qt.Key_Right:
            self._seek_relative(5.0)
            event.accept()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self._on_add_current_clip()
            event.accept()
        elif key == Qt.Key_Escape:
            self.reject()
            event.accept()
        else:
            super().keyPressEvent(event)

    # --- Frameless Drag Move ---
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and event.pos().y() <= 44:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos and (event.buttons() & Qt.LeftButton) and not self.isMaximized():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None

    def closeEvent(self, event):
        if hasattr(self, "player") and self.player:
            self.player.stop()
        super().closeEvent(event)
