import re
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QFrame, QCheckBox,
    QComboBox, QMessageBox, QSizePolicy, QApplication
)
from backend.i18n import t

class PlaylistItemCard(QFrame):
    """Individual item row inside playlist queue."""
    toggled = Signal()

    def __init__(self, index: int, item_data: dict, is_target: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self.item_data = item_data
        self.is_target = is_target

        self.setProperty("class", "playlistItemCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(54)

        if is_target:
            self.setStyleSheet("""
                QFrame.playlistItemCard {
                    background-color: #0c1a29;
                    border: 1px solid #0284c7;
                    border-left: 3px solid #38bdf8;
                }
            """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Checkbox
        self.chk = QCheckBox(self)
        self.chk.setChecked(True)
        self.chk.setCursor(Qt.PointingHandCursor)
        self.chk.stateChanged.connect(lambda: self.toggled.emit())
        layout.addWidget(self.chk)

        # Index Badge
        lbl_idx = QLabel(f"#{index + 1:02d}", self)
        lbl_idx.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; min-width: 32px;")
        layout.addWidget(lbl_idx)

        # Title & Meta Info
        v_meta = QVBoxLayout()
        v_meta.setSpacing(2)
        v_meta.setContentsMargins(0, 0, 0, 0)

        self.raw_title = item_data.get("title") or f"Item {index + 1}"
        self.lbl_title = QLabel(self.raw_title, self)
        self.lbl_title.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 12px; font-weight: 700;")
        self.lbl_title.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v_meta.addWidget(self.lbl_title)

        dur_str = item_data.get("duration") or "--:--"
        uploader = item_data.get("uploader") or ""
        meta_sub = f"DURATION: {dur_str}"
        if uploader:
            meta_sub += f" | CREATOR: {uploader}"

        lbl_sub = QLabel(meta_sub, self)
        lbl_sub.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        v_meta.addWidget(lbl_sub)

        layout.addLayout(v_meta, 1)

        if is_target:
            lbl_badge = QLabel(t("playlist_target_badge"), self)
            lbl_badge.setStyleSheet("color: #38bdf8; background-color: #0c2134; border: 1px solid #0284c7; border-radius: 4px; padding: 2px 6px; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;")
            layout.addWidget(lbl_badge)

    def is_selected(self) -> bool:
        return self.chk.isChecked()

    def set_selected(self, val: bool):
        self.chk.setChecked(val)

    def matches_query(self, query: str) -> bool:
        if not query:
            return True
        return query in self.raw_title.lower()


class PlaylistPromptDialog(QDialog):
    """Cyberpunk modal dialog asking user whether to download single video or entire playlist."""

    def __init__(self, url: str, video_title: str = "", parent=None):
        super().__init__(parent)
        self.url = url
        self.result_choice = None  # "single", "playlist", or None

        self.setWindowTitle(f"[PROMPT] {t('pl_prompt_title')}")
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())

        self.setFixedSize(560, 360)
        self.setStyleSheet("""
            QDialog {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QFrame#promptCard {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton#btnSingle {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 10px 14px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11.5px;
                font-weight: 800;
                text-align: left;
            }
            QPushButton#btnSingle:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton#btnSingle:pressed {
                background-color: #0284c7;
            }
            QPushButton#btnPlaylist {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 10px 14px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11.5px;
                font-weight: 700;
                text-align: left;
            }
            QPushButton#btnPlaylist:hover {
                background-color: #1c1d24;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton#btnCancel {
                background-color: transparent;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 6px 14px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#btnCancel:hover {
                background-color: #16171d;
                color: #f4f4f5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)

        v_head = QVBoxLayout()
        v_head.setSpacing(3)
        lbl_eyebrow = QLabel("// DETEKSI_PLAYLIST // OPSI_PENGUNDUHAN", self)
        lbl_eyebrow.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        v_head.addWidget(lbl_eyebrow)

        lbl_head = QLabel(t("pl_prompt_heading"), self)
        lbl_head.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 800;")
        v_head.addWidget(lbl_head)
        layout.addLayout(v_head)

        lbl_desc = QLabel(t("pl_prompt_desc"), self)
        lbl_desc.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.4;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)

        card = QFrame(self)
        card.setObjectName("promptCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.setSpacing(10)

        self.btn_single = QPushButton(f"{t('pl_prompt_btn_single')}\n▸ {t('pl_prompt_btn_single_desc')}", card)
        self.btn_single.setObjectName("btnSingle")
        self.btn_single.setCursor(Qt.PointingHandCursor)
        self.btn_single.clicked.connect(self._choose_single)
        c_layout.addWidget(self.btn_single)

        self.btn_playlist = QPushButton(f"{t('pl_prompt_btn_playlist')}\n▸ {t('pl_prompt_btn_playlist_desc')}", card)
        self.btn_playlist.setObjectName("btnPlaylist")
        self.btn_playlist.setCursor(Qt.PointingHandCursor)
        self.btn_playlist.clicked.connect(self._choose_playlist)
        c_layout.addWidget(self.btn_playlist)

        layout.addWidget(card)

        btn_cancel = QPushButton(t("pl_prompt_btn_cancel"), self)
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        layout.addWidget(btn_cancel, 0, Qt.AlignRight)

        self.btn_single.setFocus()

    def _choose_single(self):
        self.result_choice = "single"
        self.accept()

    def _choose_playlist(self):
        self.result_choice = "playlist"
        self.accept()


class PlaylistDialog(QDialog):
    """Cyberpunk modal dialog for selecting and batch downloading playlist videos."""
    batch_confirmed = Signal(list, dict)

    def __init__(self, playlist_data: dict, target_video_id: str = None, parent=None):
        super().__init__(parent)
        self.playlist_data = playlist_data
        self.target_video_id = target_video_id
        self.cards = []

        self.setWindowTitle(f"[BATCH] {t('playlist_dlg_title')}")
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())

        self.resize(800, 620)
        self.setMinimumSize(680, 520)

        self.setStyleSheet("""
            QDialog {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QFrame#topHeader {
                background-color: #111216;
                border-bottom: 1px solid #22232a;
            }
            QFrame#actionToolbar {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
            QFrame#footerFrame {
                background-color: #111216;
                border-top: 1px solid #22232a;
            }
            QFrame.playlistItemCard {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
            QFrame.playlistItemCard:hover {
                background-color: #16171d;
                border-color: #3f3f46;
            }
            QLineEdit, QComboBox {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38bdf8;
            }
            QCheckBox {
                color: #e4e4e7;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #3f3f46;
                background-color: #18181b;
            }
            QCheckBox::indicator:hover {
                border-color: #38bdf8;
            }
            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border-color: #38bdf8;
            }
            QPushButton.btnSub {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 5px 12px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.btnSub:hover {
                background-color: #1c1d24;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton.btnPrimary {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 8px 18px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11.5px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }
            QPushButton.btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton.btnPrimary:pressed {
                background-color: #0284c7;
            }
            QPushButton.btnSecondary {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 8px 16px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.btnSecondary:hover {
                background-color: #1c1d24;
                border-color: #3f3f46;
                color: #ffffff;
            }
            QScrollArea {
                border: 1px solid #22232a;
                border-radius: 6px;
                background-color: #0d0e12;
            }
        """)

        self._init_ui()
        self._populate_items()
        self._update_selection_state()

        if self.target_video_id:
            QTimer.singleShot(150, self._scroll_to_target)

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- 1. TOP HEADER ---
        header = QFrame(self)
        header.setObjectName("topHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 14, 20, 14)

        v_head = QVBoxLayout()
        v_head.setSpacing(3)

        lbl_eyebrow = QLabel(t("playlist_heading"), self)
        lbl_eyebrow.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        v_head.addWidget(lbl_eyebrow)

        pl_title = self.playlist_data.get("title") or "Playlist"
        self.lbl_head_title = QLabel(pl_title, self)
        self.lbl_head_title.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 800;")
        v_head.addWidget(self.lbl_head_title)

        pl_uploader = self.playlist_data.get("uploader") or "Unknown"
        self.lbl_head_creator = QLabel(f"CREATOR: {pl_uploader}", self)
        self.lbl_head_creator.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        v_head.addWidget(self.lbl_head_creator)

        h_layout.addLayout(v_head, 1)

        total_cnt = len(self.playlist_data.get("entries") or [])
        lbl_badge = QLabel(f"[ {total_cnt} MEDIA ]", self)
        lbl_badge.setStyleSheet("color: #38bdf8; background-color: #0c2134; border: 1px solid #0284c7; border-radius: 4px; padding: 4px 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;")
        h_layout.addWidget(lbl_badge, 0, Qt.AlignVCenter)

        root_layout.addWidget(header)

        # --- 2. BODY CONTENT ---
        body = QWidget(self)
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(20, 14, 20, 14)
        b_layout.setSpacing(12)

        # Toolbar: Filter + Select All/None + Quality Preset
        toolbar = QFrame(self)
        toolbar.setObjectName("actionToolbar")
        t_layout = QHBoxLayout(toolbar)
        t_layout.setContentsMargins(12, 10, 12, 10)
        t_layout.setSpacing(10)

        # Search Bar
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText(t("playlist_search_placeholder"))
        self.txt_search.textChanged.connect(self._filter_items)
        t_layout.addWidget(self.txt_search, 2)

        # Selection Buttons
        btn_select_all = QPushButton(f"[{t('playlist_select_all')}]", self)
        btn_select_all.setProperty("class", "btnSub")
        btn_select_all.setCursor(Qt.PointingHandCursor)
        btn_select_all.clicked.connect(lambda: self._set_all_selection(True))
        t_layout.addWidget(btn_select_all)

        btn_deselect_all = QPushButton(f"[{t('playlist_deselect_all')}]", self)
        btn_deselect_all.setProperty("class", "btnSub")
        btn_deselect_all.setCursor(Qt.PointingHandCursor)
        btn_deselect_all.clicked.connect(lambda: self._set_all_selection(False))
        t_layout.addWidget(btn_deselect_all)

        if self.target_video_id:
            btn_only_target = QPushButton(f"[{t('playlist_select_target')}]", self)
            btn_only_target.setProperty("class", "btnSub")
            btn_only_target.setStyleSheet("color: #38bdf8; border-color: #0284c7;")
            btn_only_target.setCursor(Qt.PointingHandCursor)
            btn_only_target.clicked.connect(self._select_target_only)
            t_layout.addWidget(btn_only_target)

        # Quality Preset Dropdown
        self.combo_quality = QComboBox(self)
        self.combo_quality.addItem("1080p | Full HD (MP4)", {"height": 1080, "mode": "video", "format": "mp4", "codec_preference": "compatible"})
        self.combo_quality.addItem("Best Resolution | Max (MKV)", {"height": None, "mode": "video", "format": "mkv", "codec_preference": "compatible"})
        self.combo_quality.addItem("720p | HD (MP4)", {"height": 720, "mode": "video", "format": "mp4", "codec_preference": "compatible"})
        self.combo_quality.addItem("Audio Only | MP3 320k", {"mode": "audio", "format": "mp3", "audio_quality": "320"})
        self.combo_quality.addItem("Audio Only | M4A Original", {"mode": "audio", "format": "m4a"})
        t_layout.addWidget(self.combo_quality, 1)

        b_layout.addWidget(toolbar)

        # Scroll Area for Video List
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(8, 8, 8, 8)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()

        self.scroll.setWidget(self.list_container)
        b_layout.addWidget(self.scroll, 1)

        root_layout.addWidget(body, 1)

        # --- 3. FOOTER FRAME ---
        footer = QFrame(self)
        footer.setObjectName("footerFrame")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(20, 12, 20, 12)

        self.lbl_selected_status = QLabel("// 0 / 0 media terpilih", self)
        self.lbl_selected_status.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        f_layout.addWidget(self.lbl_selected_status)

        f_layout.addStretch()

        btn_close = QPushButton(t("playlist_btn_close"), self)
        btn_close.setProperty("class", "btnSecondary")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        f_layout.addWidget(btn_close)

        self.btn_download = QPushButton(t("playlist_btn_download").format(count=0), self)
        self.btn_download.setProperty("class", "btnPrimary")
        self.btn_download.setCursor(Qt.PointingHandCursor)
        self.btn_download.clicked.connect(self._on_download_clicked)
        f_layout.addWidget(self.btn_download)

        root_layout.addWidget(footer)

    def _populate_items(self):
        entries = self.playlist_data.get("entries") or []
        for idx, item in enumerate(entries):
            is_tgt = bool(self.target_video_id and item.get("id") == self.target_video_id)
            card = PlaylistItemCard(idx, item, is_target=is_tgt, parent=self.list_container)
            card.toggled.connect(self._update_selection_state)
            self.cards.append(card)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _scroll_to_target(self):
        if not self.target_video_id:
            return
        for card in self.cards:
            if card.item_data.get("id") == self.target_video_id:
                self.scroll.ensureWidgetVisible(card)
                break

    def _select_target_only(self):
        for card in self.cards:
            is_it = (card.item_data.get("id") == self.target_video_id)
            card.set_selected(is_it)
        self._update_selection_state()

    def _filter_items(self, text: str):
        query = text.strip().lower()
        for card in self.cards:
            card.setVisible(card.matches_query(query))
        self._update_selection_state()

    def _set_all_selection(self, select: bool):
        for card in self.cards:
            if not card.isHidden():
                card.set_selected(select)
        self._update_selection_state()

    def _update_selection_state(self):
        selected_count = sum(1 for c in self.cards if c.is_selected())
        total_count = len(self.cards)

        self.lbl_selected_status.setText(f"// {selected_count} / {total_count} terpilih")
        self.btn_download.setText(t("playlist_btn_download").format(count=selected_count))
        self.btn_download.setEnabled(selected_count > 0)

    def _on_download_clicked(self):
        selected_items = [c.item_data for c in self.cards if c.is_selected()]
        if not selected_items:
            QMessageBox.warning(self, t("dialog_info"), t("playlist_err_no_selection"))
            return

        config = self.combo_quality.currentData()
        self.batch_confirmed.emit(selected_items, config)
        self.accept()
