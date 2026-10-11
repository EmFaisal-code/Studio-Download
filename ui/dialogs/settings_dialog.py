import os
import subprocess
from PySide6.QtCore import Qt, Signal, QTimer, QUrl
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QComboBox, QFileDialog, QFrame,
    QMessageBox, QStackedWidget, QButtonGroup, QWidget,
    QScrollArea, QApplication, QCheckBox
)
from PySide6.QtGui import QDesktopServices
from backend.config import get_settings, save_settings, get_app_dir
from backend.app import resolve_extension_dir
from backend.i18n import t, get_current_lang, set_current_lang

class SettingsDialog(QDialog):
    settings_saved = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"[CONFIG] {t('settings_title')}")
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())
        self.setFixedSize(830, 580)
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
            QFrame#sidebarFrame {
                background-color: #0d0e12;
                border-right: 1px solid #22232a;
            }
            QStackedWidget#settingsStack {
                background-color: #09090b;
            }
            QFrame#footerFrame {
                background-color: #111216;
                border-top: 1px solid #22232a;
            }
            QScrollArea#extScrollArea, QWidget#extScrollAreaViewport, QWidget#extScrollContent {
                background-color: transparent;
                border: none;
            }
            QPushButton[class="sideTab"] {
                background-color: transparent;
                color: #a1a1aa;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 10px 14px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10.5px;
                font-weight: 600;
                text-align: left;
            }
            QPushButton[class="sideTab"]:hover {
                background-color: #16171d;
                color: #f4f4f5;
                border-color: #27272a;
            }
            QPushButton[class="sideTab"]:checked {
                background-color: #161822;
                color: #38bdf8;
                border: 1px solid #2563eb;
                border-left: 3px solid #38bdf8;
                font-weight: 700;
            }
            QLabel[class="groupTitle"] {
                color: #818cf8;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 0.5px;
            }
            QLabel[class="fieldLabel"] {
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 600;
                font-size: 11px;
            }
            QFrame[class="settingCard"] {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
            QPushButton[class="btnPrimary"], QPushButton#btnPrimary {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 6px 14px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton[class="btnPrimary"]:hover, QPushButton#btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
                color: #09090b;
            }
            QPushButton[class="btnPrimary"]:pressed, QPushButton#btnPrimary:pressed {
                background-color: #0284c7;
                color: #ffffff;
            }
            QPushButton[class="btnSecondary"], QPushButton#btnSecondary {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 6px 14px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton[class="btnSecondary"]:hover, QPushButton#btnSecondary:hover {
                background-color: #1c1d24;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton[class="btnSecondary"]:pressed, QPushButton#btnSecondary:pressed {
                background-color: #111216;
            }
            QPushButton#btnDonateDialog {
                background-color: #231219;
                border: 1px solid #be185d;
                border-radius: 6px;
                padding: 6px 14px;
                color: #f472b6;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton#btnDonateDialog:hover {
                background-color: #3b1424;
                border-color: #f472b6;
                color: #fce7f3;
            }
            QPushButton#btnDonateDialog:pressed {
                background-color: #170b10;
            }
            QSpinBox, QComboBox, QLineEdit {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 6px 10px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
            }
            QSpinBox:focus, QComboBox:focus, QLineEdit:focus {
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
        """)
        self._init_ui()
        self._load_values()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top Header Bar
        top_header = QFrame(self)
        top_header.setObjectName("topHeader")
        top_h_layout = QHBoxLayout(top_header)
        top_h_layout.setContentsMargins(20, 12, 20, 12)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)
        self.lbl_head = QLabel(t("settings_header"), self)
        self.lbl_head.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 800;")
        v_head.addWidget(self.lbl_head)

        self.lbl_sub = QLabel(t("settings_subtitle"), self)
        self.lbl_sub.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        v_head.addWidget(self.lbl_sub)
        top_h_layout.addLayout(v_head, 1)

        tag_sys = QLabel("[READY_200]", self)
        tag_sys.setStyleSheet("color: #34d399; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; border: 1px solid #059669; border-radius: 4px; padding: 3px 8px; background: #062316;")
        top_h_layout.addWidget(tag_sys)
        root_layout.addWidget(top_header)

        # Middle Content: Sidebar + Stacked Widget
        middle_widget = QWidget(self)
        middle_layout = QHBoxLayout(middle_widget)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        # Left Sidebar Navigation
        sidebar_frame = QFrame(self)
        sidebar_frame.setObjectName("sidebarFrame")
        sidebar_frame.setFixedWidth(230)
        sb_layout = QVBoxLayout(sidebar_frame)
        sb_layout.setContentsMargins(12, 14, 12, 14)
        sb_layout.setSpacing(6)

        self.lbl_nav_title = QLabel(t("settings_sections"), self)
        self.lbl_nav_title.setStyleSheet("color: #52525b; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; margin-bottom: 4px;")
        sb_layout.addWidget(self.lbl_nav_title)

        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)

        tabs_info = [
            (f"{t('tab_pref_title')} {t('tab_pref_desc')}", 0),
            (f"{t('tab_dir_title')} {t('tab_dir_desc')}", 1),
            (f"{t('tab_auth_title')} {t('tab_auth_desc')}", 2),
            (f"{t('tab_ext_title')} {t('tab_ext_desc')}", 3),
            (f"{t('tab_info_title')} {t('tab_info_desc')}", 4),
        ]

        self.tab_buttons = []
        for text, idx in tabs_info:
            btn = QPushButton(text, self)
            btn.setProperty("class", "sideTab")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, i=idx: self._switch_tab(i))
            self.tab_group.addButton(btn, idx)
            sb_layout.addWidget(btn)
            self.tab_buttons.append(btn)

        sb_layout.addStretch()
        middle_layout.addWidget(sidebar_frame)

        # Right Stacked Widget
        self.stack = QStackedWidget(self)
        self.stack.setObjectName("settingsStack")

        # Page 1: General Preferences
        page_pref = self._build_page_preferences()
        self.stack.addWidget(page_pref)

        # Page 2: Storage Directory
        page_dir = self._build_page_directory()
        self.stack.addWidget(page_dir)

        # Page 3: Authentication Cookies
        page_cookie = self._build_page_cookies()
        self.stack.addWidget(page_cookie)

        # Page 4: Companion Browser Extension
        page_ext = self._build_page_extension()
        self.stack.addWidget(page_ext)

        # Page 5: Releases & System Info
        page_releases = self._build_page_releases()
        self.stack.addWidget(page_releases)

        middle_layout.addWidget(self.stack, 1)
        root_layout.addWidget(middle_widget, 1)

        # Bottom Dock (Footer)
        footer_frame = QFrame(self)
        footer_frame.setObjectName("footerFrame")
        f_layout = QHBoxLayout(footer_frame)
        f_layout.setContentsMargins(20, 10, 20, 10)

        # Support / Donate Button (Always accessible in settings)
        self.btn_donate = QPushButton(f"[{t('btn_donate_full')}]", self)
        self.btn_donate.setObjectName("btnDonateDialog")
        self.btn_donate.setToolTip("https://sociabuzz.com/emef/tribe")
        self.btn_donate.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://sociabuzz.com/emef/tribe")))
        f_layout.addWidget(self.btn_donate)

        f_layout.addStretch()

        self.btn_close = QPushButton(t("btn_close_dialog"), self)
        self.btn_close.setProperty("class", "btnSecondary")
        self.btn_close.clicked.connect(self.reject)
        f_layout.addWidget(self.btn_close)

        self.btn_save = QPushButton(t("btn_save_dialog"), self)
        self.btn_save.setProperty("class", "btnPrimary")
        self.btn_save.clicked.connect(self._save)
        f_layout.addWidget(self.btn_save)

        root_layout.addWidget(footer_frame)

    def _switch_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)

    # --- PAGE 1: PREFERENCES ---
    def _build_page_preferences(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.lbl_pref_title = QLabel(f"// {t('tab_pref_title')} {t('tab_pref_desc')}".replace("// //", "//"), self)
        self.lbl_pref_title.setProperty("class", "groupTitle")
        layout.addWidget(self.lbl_pref_title)

        card = QFrame(self)
        card.setProperty("class", "settingCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(12)

        # Language Selection
        self.lbl_pref_lang = QLabel(t("pref_lang_label"), self)
        c_layout.addWidget(self.lbl_pref_lang)
        self.combo_lang = QComboBox(self)
        self.combo_lang.addItem("Bahasa Indonesia (ID)", "id")
        self.combo_lang.addItem("English (EN)", "en")
        self.combo_lang.currentIndexChanged.connect(self._on_combo_lang_changed)
        c_layout.addWidget(self.combo_lang)

        # Theme Engine Selection
        self.lbl_pref_theme = QLabel(t("pref_theme_label"), self)
        c_layout.addWidget(self.lbl_pref_theme)
        self.combo_theme = QComboBox(self)
        self.combo_theme.addItem("Developer Zinc (IDE Craft)", "developer-zinc")
        self.combo_theme.addItem("Studio Amber (Modern Yellow)", "modern-yellow")
        c_layout.addWidget(self.combo_theme)

        # Concurrency & Speed Limit
        row_num = QHBoxLayout()
        v1 = QVBoxLayout()
        self.lbl_pref_concurrent = QLabel(t("pref_concurrent_label"), self)
        v1.addWidget(self.lbl_pref_concurrent)
        self.spin_concurrent = QSpinBox(self)
        self.spin_concurrent.setRange(1, 10)
        v1.addWidget(self.spin_concurrent)
        row_num.addLayout(v1)

        v2 = QVBoxLayout()
        self.lbl_pref_speed = QLabel(t("pref_speed_label"), self)
        v2.addWidget(self.lbl_pref_speed)
        self.spin_speed = QSpinBox(self)
        self.spin_speed.setRange(0, 1000000)
        self.spin_speed.setSingleStep(500)
        self.spin_speed.setSuffix(" KB/s")
        v2.addWidget(self.spin_speed)
        row_num.addLayout(v2)

        c_layout.addLayout(row_num)
        layout.addWidget(card)
        layout.addStretch()
        return w

    # --- PAGE 2: STORAGE DIRECTORY ---
    def _build_page_directory(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.lbl_dir_title = QLabel(f"// {t('tab_dir_title')} {t('tab_dir_desc')}".replace("// //", "//"), self)
        self.lbl_dir_title.setProperty("class", "groupTitle")
        layout.addWidget(self.lbl_dir_title)

        card = QFrame(self)
        card.setProperty("class", "settingCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(10)

        self.lbl_dir_desc = QLabel(t("dir_desc"), self)
        self.lbl_dir_desc.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        c_layout.addWidget(self.lbl_dir_desc)

        self.txt_dir = QLineEdit(self)
        c_layout.addWidget(self.txt_dir)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_browse_dir = QPushButton(t("btn_browse_dir"), self)
        self.btn_browse_dir.setProperty("class", "btnSecondary")
        self.btn_browse_dir.clicked.connect(self._browse_dir)
        action_row.addWidget(self.btn_browse_dir)

        self.btn_open_dir = QPushButton(t("btn_open_dir"), self)
        self.btn_open_dir.setProperty("class", "btnPrimary")
        self.btn_open_dir.clicked.connect(self._open_download_dir)
        action_row.addWidget(self.btn_open_dir)

        action_row.addStretch()
        c_layout.addLayout(action_row)

        layout.addWidget(card)
        layout.addStretch()
        return w

    # --- PAGE 3: AUTHENTICATION COOKIES ---
    def _build_page_cookies(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.lbl_auth_title = QLabel(f"// {t('tab_auth_title')} {t('tab_auth_desc')}".replace("// //", "//"), self)
        self.lbl_auth_title.setProperty("class", "groupTitle")
        layout.addWidget(self.lbl_auth_title)

        card = QFrame(self)
        card.setProperty("class", "settingCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(12)

        cookie_row = QHBoxLayout()
        cookie_row.setSpacing(10)
        self.lbl_cookie_status = QLabel(self)
        self.lbl_cookie_status.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 11.5px; background: transparent; border: none;")
        cookie_row.addWidget(self.lbl_cookie_status, 1)

        self.btn_import_cookie = QPushButton(t("btn_import_cookies"), self)
        self.btn_import_cookie.setProperty("class", "btnSecondary")
        self.btn_import_cookie.clicked.connect(self._import_cookie)
        cookie_row.addWidget(self.btn_import_cookie)

        self.btn_del_cookie = QPushButton(t("btn_delete_cookies"), self)
        self.btn_del_cookie.setProperty("class", "btnSecondary")
        self.btn_del_cookie.setStyleSheet("""
            QPushButton {
                background-color: rgba(244, 63, 94, 0.08);
                border: 1px solid rgba(244, 63, 94, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                color: #f43f5e;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f43f5e;
                color: #ffffff;
            }
        """)
        self.btn_del_cookie.clicked.connect(self._delete_cookie)
        cookie_row.addWidget(self.btn_del_cookie)

        c_layout.addLayout(cookie_row)

        # Info Box (Protected from selector cascading)
        self.auth_info_box = QFrame(self)
        self.auth_info_box.setObjectName("authInfoBox")
        self.auth_info_box.setStyleSheet("""
            QFrame#authInfoBox {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-left: 3px solid #818cf8;
                border-radius: 6px;
            }
            QFrame#authInfoBox QLabel {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        i_layout = QVBoxLayout(self.auth_info_box)
        i_layout.setContentsMargins(14, 12, 14, 12)
        i_layout.setSpacing(6)

        self.lbl_auth_guide_title = QLabel(t("auth_instructions_title"), self.auth_info_box)
        self.lbl_auth_guide_title.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; background: transparent; border: none;")
        i_layout.addWidget(self.lbl_auth_guide_title)

        self.lbl_auth_desc = QLabel(t("auth_desc"), self.auth_info_box)
        self.lbl_auth_desc.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.4; background: transparent; border: none;")
        self.lbl_auth_desc.setWordWrap(True)
        i_layout.addWidget(self.lbl_auth_desc)

        self.lbl_auth_ext_tip = QLabel(
            f'<span style="color:#fbbf24; font-weight:700;">{t("auth_tip_badge")}</span> '
            f'<span style="color:#71717a;">{t("auth_ext_tip")}</span>',
            self.auth_info_box
        )
        self.lbl_auth_ext_tip.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10px; line-height: 1.3; background: transparent; border: none;")
        self.lbl_auth_ext_tip.setWordWrap(True)
        i_layout.addWidget(self.lbl_auth_ext_tip)

        c_layout.addWidget(self.auth_info_box)
        layout.addWidget(card)
        layout.addStretch()
        return w

    # --- PAGE 4: BROWSER EXTENSION ---
    def _build_page_extension(self) -> QWidget:
        scroll = QScrollArea(self)
        scroll.setObjectName("extScrollArea")
        scroll.viewport().setObjectName("extScrollAreaViewport")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        w = QWidget()
        w.setObjectName("extScrollContent")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self.lbl_ext_title = QLabel(f"// {t('tab_ext_title')} {t('tab_ext_desc')}".replace("// //", "//"), self)
        self.lbl_ext_title.setProperty("class", "groupTitle")
        layout.addWidget(self.lbl_ext_title)

        ext_dir = resolve_extension_dir()
        self.ext_path_str = os.path.normpath(str(ext_dir))

        # Card 1: Folder Path
        card1 = QFrame(self)
        card1.setProperty("class", "settingCard")
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(14, 14, 14, 14)
        c1_layout.setSpacing(8)

        self.lbl_ext_path_label = QLabel(t("ext_path_label"), self)
        self.lbl_ext_path_label.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;")
        c1_layout.addWidget(self.lbl_ext_path_label)

        path_row = QHBoxLayout()
        self.txt_ext_path = QLineEdit(self.ext_path_str, self)
        self.txt_ext_path.setReadOnly(True)
        self.txt_ext_path.setStyleSheet("QLineEdit { color: #38bdf8; }")
        path_row.addWidget(self.txt_ext_path, 1)

        self.btn_open_ext = QPushButton(t("btn_open_ext"), self)
        self.btn_open_ext.setProperty("class", "btnPrimary")
        self.btn_open_ext.clicked.connect(self._open_ext_folder)
        path_row.addWidget(self.btn_open_ext)

        self.btn_copy_ext_path = QPushButton(t("btn_copy_ext_path"), self)
        self.btn_copy_ext_path.setProperty("class", "btnSecondary")
        self.btn_copy_ext_path.clicked.connect(self._copy_ext_path)
        path_row.addWidget(self.btn_copy_ext_path)

        c1_layout.addLayout(path_row)
        layout.addWidget(card1)

        # Card 2: 3-Step Guide (NO EMOJI LOGOS)
        card2 = QFrame(self)
        card2.setProperty("class", "settingCard")
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(14, 14, 14, 14)
        c2_layout.setSpacing(6)

        self.lbl_ext_guide_title = QLabel(t("ext_guide_title"), self)
        self.lbl_ext_guide_title.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;")
        c2_layout.addWidget(self.lbl_ext_guide_title)

        s1_row = QHBoxLayout()
        self.lbl_ext_step1 = QLabel(t("ext_step1"), self)
        self.lbl_ext_step1.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        self.lbl_ext_step1.setWordWrap(True)
        s1_row.addWidget(self.lbl_ext_step1, 1)

        self.btn_copy_ext_url = QPushButton(t("btn_copy_ext_url"), self)
        self.btn_copy_ext_url.setProperty("class", "btnSecondary")
        self.btn_copy_ext_url.setStyleSheet("QPushButton { padding: 2px 8px; font-size: 10px; }")
        self.btn_copy_ext_url.clicked.connect(lambda: self._copy_text("chrome://extensions", self.btn_copy_ext_url))
        s1_row.addWidget(self.btn_copy_ext_url)
        c2_layout.addLayout(s1_row)

        self.lbl_ext_step2 = QLabel(t("ext_step2"), self)
        self.lbl_ext_step2.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        self.lbl_ext_step2.setWordWrap(True)
        c2_layout.addWidget(self.lbl_ext_step2)

        self.lbl_ext_step3 = QLabel(t("ext_step3"), self)
        self.lbl_ext_step3.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
        self.lbl_ext_step3.setWordWrap(True)
        c2_layout.addWidget(self.lbl_ext_step3)

        layout.addWidget(card2)

        # Card 3: Features (NO EMOJI LOGOS)
        card3 = QFrame(self)
        card3.setProperty("class", "settingCard")
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(14, 14, 14, 14)
        c3_layout.setSpacing(4)

        self.lbl_ext_features_title = QLabel(t("ext_features_title"), self)
        self.lbl_ext_features_title.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;")
        c3_layout.addWidget(self.lbl_ext_features_title)

        self.lbl_ext_feat1 = QLabel(t("ext_feat_cookie"), self)
        self.lbl_ext_feat1.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 10px; line-height: 1.3;")
        self.lbl_ext_feat1.setWordWrap(True)
        c3_layout.addWidget(self.lbl_ext_feat1)

        self.lbl_ext_feat2 = QLabel(t("ext_feat_stream"), self)
        self.lbl_ext_feat2.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 10px; line-height: 1.3;")
        self.lbl_ext_feat2.setWordWrap(True)
        c3_layout.addWidget(self.lbl_ext_feat2)

        layout.addWidget(card3)
        layout.addStretch()
        scroll.setWidget(w)
        return scroll

    # --- PAGE 5: RELEASES & SYSTEM INFO ---
    def _build_page_releases(self) -> QWidget:
        w = QWidget(self)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        self.lbl_info_title = QLabel(f"// {t('tab_info_title')} {t('tab_info_desc')}".replace("// //", "//"), self)
        self.lbl_info_title.setProperty("class", "groupTitle")
        layout.addWidget(self.lbl_info_title)

        card = QFrame(self)
        card.setProperty("class", "settingCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(14, 14, 14, 14)
        c_layout.setSpacing(10)

        info_items = [
            ("SOFTWARE_NAME", "Studio Download"),
            ("CURRENT_VERSION", "v1.0 (Stable Release)"),
            ("GUI_FRAMEWORK", "PySide6 (Qt 6 Native Framework)"),
            ("MEDIA_INGESTION", "yt-dlp Core Engine"),
            ("MEDIA_PROCESSOR", "FFmpeg Universal Multiplexer"),
            ("REPOSITORY", "https://github.com/EmFaisal-code/Studio-Download"),
            ("DONATION_SUPPORT", "https://sociabuzz.com/emef/tribe"),
        ]

        for k, v in info_items:
            row = QHBoxLayout()
            lbl_k = QLabel(f"{k}:", self)
            lbl_k.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; width: 140px;")
            lbl_k.setFixedWidth(140)
            row.addWidget(lbl_k)

            lbl_v = QLabel(v, self)
            lbl_v.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 10.5px;")
            row.addWidget(lbl_v, 1)
            c_layout.addLayout(row)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.btn_releases = QPushButton(t("btn_open_releases"), self)
        self.btn_releases.setProperty("class", "btnPrimary")
        self.btn_releases.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/EmFaisal-code/Studio-Download/releases")))
        action_row.addWidget(self.btn_releases)

        self.btn_repo = QPushButton(t("btn_visit_repo"), self)
        self.btn_repo.setProperty("class", "btnSecondary")
        self.btn_repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/EmFaisal-code/Studio-Download")))
        action_row.addWidget(self.btn_repo)

        self.btn_donate_page = QPushButton(f"[{t('btn_donate_full')}]", self)
        self.btn_donate_page.setProperty("class", "btnSecondary")
        self.btn_donate_page.setStyleSheet("QPushButton { border-color: #be185d; color: #f472b6; font-weight: 700; } QPushButton:hover { background-color: #3b1424; border-color: #f472b6; color: #fce7f3; }")
        self.btn_donate_page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://sociabuzz.com/emef/tribe")))
        action_row.addWidget(self.btn_donate_page)

        action_row.addStretch()
        c_layout.addLayout(action_row)

        layout.addWidget(card)
        layout.addStretch()
        return w

    # --- LIVE RETRANSLATE ---
    def retranslate_ui(self):
        self.setWindowTitle(f"[CONFIG] {t('settings_title')}")
        self.lbl_head.setText(t("settings_header"))
        self.lbl_sub.setText(t("settings_subtitle"))
        self.lbl_nav_title.setText(t("settings_sections"))

        tabs_info = [
            f"{t('tab_pref_title')} {t('tab_pref_desc')}",
            f"{t('tab_dir_title')} {t('tab_dir_desc')}",
            f"{t('tab_auth_title')} {t('tab_auth_desc')}",
            f"{t('tab_ext_title')} {t('tab_ext_desc')}",
            f"{t('tab_info_title')} {t('tab_info_desc')}",
        ]
        for i, text in enumerate(tabs_info):
            if i < len(self.tab_buttons):
                self.tab_buttons[i].setText(text)

        # Page 1
        self.lbl_pref_title.setText(f"// {t('tab_pref_title')} {t('tab_pref_desc')}".replace("// //", "//"))
        self.lbl_pref_lang.setText(t("pref_lang_label"))
        self.lbl_pref_theme.setText(t("pref_theme_label"))
        self.lbl_pref_concurrent.setText(t("pref_concurrent_label"))
        self.lbl_pref_speed.setText(t("pref_speed_label"))

        # Page 2
        self.lbl_dir_title.setText(f"// {t('tab_dir_title')} {t('tab_dir_desc')}".replace("// //", "//"))
        self.lbl_dir_desc.setText(t("dir_desc"))
        self.btn_browse_dir.setText(t("btn_browse_dir"))
        self.btn_open_dir.setText(t("btn_open_dir"))

        # Page 3
        self.lbl_auth_title.setText(f"// {t('tab_auth_title')} {t('tab_auth_desc')}".replace("// //", "//"))
        self.btn_import_cookie.setText(t("btn_import_cookies"))
        self.btn_del_cookie.setText(t("btn_delete_cookies"))
        self.lbl_auth_guide_title.setText(t("auth_instructions_title"))
        self.lbl_auth_desc.setText(t("auth_desc"))
        self.lbl_auth_ext_tip.setText(
            f'<span style="color:#fbbf24; font-weight:700;">{t("auth_tip_badge")}</span> '
            f'<span style="color:#71717a;">{t("auth_ext_tip")}</span>'
        )
        self._check_cookie_status()

        # Page 4
        self.lbl_ext_title.setText(f"// {t('tab_ext_title')} {t('tab_ext_desc')}".replace("// //", "//"))
        self.lbl_ext_path_label.setText(t("ext_path_label"))
        self.btn_open_ext.setText(t("btn_open_ext"))
        self.btn_copy_ext_path.setText(t("btn_copy_ext_path"))
        self.lbl_ext_guide_title.setText(t("ext_guide_title"))
        self.lbl_ext_step1.setText(t("ext_step1"))
        self.btn_copy_ext_url.setText(t("btn_copy_ext_url"))
        self.lbl_ext_step2.setText(t("ext_step2"))
        self.lbl_ext_step3.setText(t("ext_step3"))
        self.lbl_ext_features_title.setText(t("ext_features_title"))
        self.lbl_ext_feat1.setText(t("ext_feat_cookie"))
        self.lbl_ext_feat2.setText(t("ext_feat_stream"))

        # Page 5
        self.lbl_info_title.setText(f"// {t('tab_info_title')} {t('tab_info_desc')}".replace("// //", "//"))
        self.btn_releases.setText(t("btn_open_releases"))
        self.btn_repo.setText(t("btn_visit_repo"))
        if hasattr(self, "btn_donate_page"):
            self.btn_donate_page.setText(f"[{t('btn_donate_full')}]")

        # Footer
        if hasattr(self, "btn_donate"):
            self.btn_donate.setText(f"[{t('btn_donate_full')}]")
        self.btn_close.setText(t("btn_close_dialog"))
        self.btn_save.setText(t("btn_save_dialog"))

    def _on_combo_lang_changed(self, idx: int):
        new_lang = self.combo_lang.currentData()
        if new_lang:
            set_current_lang(new_lang)
            self.retranslate_ui()

    # --- VALUES & ACTIONS ---
    def _load_values(self):
        settings = get_settings()
        self.txt_dir.setText(settings.get("download_dir", ""))
        self.spin_concurrent.setValue(settings.get("max_concurrent_downloads", 2))
        self.spin_speed.setValue(settings.get("download_speed_limit", 0))

        cur_theme = settings.get("theme", "developer-zinc")
        idx_t = 1 if cur_theme in ("modern-yellow", "cyber-yellow") else 0
        self.combo_theme.setCurrentIndex(idx_t)

        cur_lang = settings.get("language", "en")
        idx_l = 1 if cur_lang == "en" else 0
        self.combo_lang.blockSignals(True)
        self.combo_lang.setCurrentIndex(idx_l)
        self.combo_lang.blockSignals(False)

        self._check_cookie_status()

    def _get_active_cookie_file(self):
        app_cookie = get_app_dir() / "cookies.txt"
        if app_cookie.exists() and app_cookie.stat().st_size > 0:
            return app_cookie
        from backend.config import DEFAULT_COOKIE_FILE
        if DEFAULT_COOKIE_FILE.exists() and DEFAULT_COOKIE_FILE.stat().st_size > 0:
            return DEFAULT_COOKIE_FILE
        return None

    def _check_cookie_status(self):
        cookie_file = self._get_active_cookie_file()
        if cookie_file and cookie_file.exists() and cookie_file.stat().st_size > 0:
            size_kb = max(1, cookie_file.stat().st_size // 1024)
            self.lbl_cookie_status.setText(f'<span style="color:#34d399; font-weight:700;">[ {t("cookie_active_status").format(size=size_kb)} ]</span>')
            self.btn_del_cookie.setVisible(True)
        else:
            self.lbl_cookie_status.setText(f'<span style="color:#71717a; font-weight:700;">[ {t("cookie_none_status")} ]</span>')
            self.btn_del_cookie.setVisible(False)

    def _browse_dir(self):
        cur = self.txt_dir.text()
        chosen = QFileDialog.getExistingDirectory(self, t("browse_dir_dlg_title"), cur or os.path.expanduser("~"))
        if chosen:
            self.txt_dir.setText(os.path.normpath(chosen))

    def _open_download_dir(self):
        cur = self.txt_dir.text().strip() or str(get_app_dir())
        os.makedirs(cur, exist_ok=True)
        try:
            if os.path.exists(cur):
                os.startfile(cur)
            else:
                subprocess.Popen(f'explorer "{cur}"')
        except Exception:
            subprocess.Popen(f'explorer "{cur}"')

    def _import_cookie(self):
        chosen, _ = QFileDialog.getOpenFileName(self, t("import_cookies_dlg_title"), os.path.expanduser("~"), "Text Files (*.txt);;All Files (*)")
        if chosen:
            try:
                import shutil
                dest = get_app_dir() / "cookies.txt"
                shutil.copy2(chosen, dest)
                self._check_cookie_status()
                QMessageBox.information(self, t("dialog_success"), t("cookies_installed_success"))
            except Exception as e:
                QMessageBox.critical(self, t("dialog_error"), t("cookies_install_failed").format(err=e))

    def _delete_cookie(self):
        try:
            app_cookie = get_app_dir() / "cookies.txt"
            if app_cookie.exists():
                app_cookie.unlink()
            from backend.config import DEFAULT_COOKIE_FILE
            if DEFAULT_COOKIE_FILE.exists():
                DEFAULT_COOKIE_FILE.unlink()
            self._check_cookie_status()
            QMessageBox.information(self, t("dialog_info"), t("cookies_deleted_success"))
        except Exception as e:
            QMessageBox.critical(self, t("dialog_error"), t("cookies_delete_failed").format(err=e))

    def _open_ext_folder(self):
        norm_path = self.ext_path_str
        try:
            if os.path.exists(norm_path):
                os.startfile(norm_path)
            else:
                subprocess.Popen(f'explorer "{norm_path}"')
        except Exception:
            subprocess.Popen(f'explorer "{norm_path}"')

    def _copy_ext_path(self):
        QApplication.clipboard().setText(self.ext_path_str)
        self.btn_copy_ext_path.setText(t("copied_badge"))
        QTimer.singleShot(2000, lambda: self.btn_copy_ext_path.setText(t("btn_copy_ext_path")))

    def _copy_text(self, text, btn):
        QApplication.clipboard().setText(text)
        btn.setText(t("copied_badge"))
        QTimer.singleShot(2000, lambda: btn.setText(t("btn_copy_ext_url")))

    def _save(self):
        settings = get_settings()
        new_dir = self.txt_dir.text().strip()
        if new_dir:
            os.makedirs(new_dir, exist_ok=True)
            settings["download_dir"] = new_dir
        settings["max_concurrent_downloads"] = self.spin_concurrent.value()
        settings["download_speed_limit"] = self.spin_speed.value()
        settings["theme"] = self.combo_theme.currentData()
        settings["language"] = self.combo_lang.currentData()
        save_settings(settings)
        self.settings_saved.emit(settings)
        self.accept()
