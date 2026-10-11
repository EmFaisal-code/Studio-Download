import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QPoint, Signal, QUrl
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices
from backend.i18n import t, get_current_lang
from backend.config import get_settings, save_settings, get_active_session_profile

class CustomTitleBar(QWidget):
    open_history_requested = Signal()
    open_settings_requested = Signal()
    open_user_profile_requested = Signal()
    language_changed = Signal(str)

    def __init__(self, parent=None, title="Studio Download", icon_path=None):
        super().__init__(parent)
        self.parent_window = parent
        self.icon_path = icon_path
        self.drag_position = QPoint()
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QWidget#titleBar {
                background-color: #111216;
                border-bottom: 1px solid #22232a;
            }
            QLabel#titleText {
                color: #f4f4f5;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: -0.2px;
            }
            QLabel#badgeVer {
                background-color: transparent;
                color: #71717a;
                border: none;
                padding: 0 4px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 500;
            }
            QLabel#statusBadge {
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                color: #71717a;
                padding-left: 6px;
            }
            QPushButton.tbBtn {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 10px;
                color: #a1a1aa;
                font-family: 'JetBrains Mono', 'Segoe UI', monospace;
                font-weight: 500;
                font-size: 11px;
            }
            QPushButton.tbBtn:hover {
                background-color: #16171d;
                border: 1px solid #27272a;
                color: #f4f4f5;
            }
            QPushButton.tbBtn:pressed {
                background-color: #111216;
            }
            QPushButton#btnUserBadge {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 4px 10px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton#btnUserBadge:hover {
                background-color: #181c26;
                border-color: #38bdf8;
                color: #7dd3fc;
            }
            QPushButton#btnUserBadge[guest="true"] {
                color: #fbbf24;
                border-color: #78350f;
                background-color: #171410;
            }
            QPushButton#btnUserBadge[guest="true"]:hover {
                border-color: #fbbf24;
                color: #fef08a;
                background-color: #241d14;
            }
            QPushButton#btnDonate {
                background-color: #1a1016;
                border: 1px solid #9d174d;
                border-radius: 6px;
                padding: 4px 10px;
                color: #f472b6;
                font-family: 'JetBrains Mono', 'Segoe UI', monospace;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton#btnDonate:hover {
                background-color: #2b1323;
                border-color: #f472b6;
                color: #fce7f3;
            }
            QPushButton#btnDonate:pressed {
                background-color: #140b11;
            }
            QPushButton.winBtn {
                background-color: transparent;
                border: none;
                width: 38px;
                height: 38px;
                color: #71717a;
                font-size: 12px;
                font-weight: 500;
                border-radius: 0px;
            }
            QPushButton.winBtn:hover {
                background-color: #1c1d24;
                color: #f4f4f5;
            }
            QPushButton#btnClose:hover {
                background-color: #f43f5e;
                color: #ffffff;
            }
        """)
        self.setObjectName("titleBar")
        self._init_ui(title)

    def _init_ui(self, title):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        # App Logo Icon (Clean, crisp 18x18 branding)
        icon_file = self.icon_path
        if not icon_file or not os.path.exists(icon_file):
            from backend.config import get_bundle_dir, get_app_dir
            for cand in [
                get_bundle_dir() / "app_icon.png",
                get_app_dir() / "app_icon.png",
                Path(__file__).resolve().parent.parent.parent / "app_icon.png",
                get_bundle_dir() / "app_icon.ico",
                get_app_dir() / "app_icon.ico",
                Path(__file__).resolve().parent.parent.parent / "app_icon.ico"
            ]:
                if cand.exists():
                    icon_file = str(cand)
                    break

        if icon_file and os.path.exists(icon_file):
            self.icon_lbl = QLabel(self)
            self.icon_lbl.setObjectName("appTitleLogo")
            pix = QPixmap(icon_file).scaled(18, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.icon_lbl.setPixmap(pix)
            self.icon_lbl.setFixedSize(18, 18)
            layout.addWidget(self.icon_lbl)

        # Title Label
        title_lbl = QLabel(title, self)
        title_lbl.setObjectName("titleText")
        layout.addWidget(title_lbl)

        # Version text (Clean plain text, no box)
        ver_lbl = QLabel("v1.0", self)
        ver_lbl.setObjectName("badgeVer")
        layout.addWidget(ver_lbl)

        # System Status Indicator (Clean developer indicator)
        status_lbl = QLabel(
            '<span style="color:#52525b;">[</span><span style="color:#a1a1aa;">SYS</span><span style="color:#52525b;">:</span>'
            '<span style="color:#34d399; font-weight:700;">READY_200</span><span style="color:#52525b;">|</span>'
            '<span style="color:#38bdf8;">ENGINE</span><span style="color:#52525b;">:</span>'
            '<span style="color:#38bdf8; font-weight:700;">PYSIDE6</span><span style="color:#52525b;">]</span>',
            self
        )
        status_lbl.setObjectName("statusBadge")
        layout.addWidget(status_lbl)

        layout.addStretch()

        # Action Buttons on Right: [USR: @user] User Badge, [LOG] History & [CONFIG] Settings
        self.btn_user = QPushButton(self)
        self.btn_user.setObjectName("btnUserBadge")
        self.btn_user.setFixedHeight(28)
        self.btn_user.setToolTip(t("title_user_badge_tooltip"))
        self.btn_user.clicked.connect(self.open_user_profile_requested.emit)
        layout.addWidget(self.btn_user)

        self.btn_donate = QPushButton(f"[{t('btn_donate')}]", self)
        self.btn_donate.setObjectName("btnDonate")
        self.btn_donate.setFixedHeight(28)
        self.btn_donate.setToolTip(t("nav_donate_title"))
        self.btn_donate.clicked.connect(self._open_donate)
        layout.addWidget(self.btn_donate)

        self.btn_history = QPushButton(f"[LOG] {t('nav_history')}", self)
        self.btn_history.setProperty("class", "tbBtn")
        self.btn_history.setFixedHeight(28)
        self.btn_history.setToolTip(t("nav_history_title"))
        self.btn_history.clicked.connect(self.open_history_requested.emit)
        layout.addWidget(self.btn_history)

        self.btn_settings = QPushButton(f"[CONFIG] {t('nav_settings')}", self)
        self.btn_settings.setProperty("class", "tbBtn")
        self.btn_settings.setFixedHeight(28)
        self.btn_settings.setToolTip(t("nav_settings_title"))
        self.btn_settings.clicked.connect(self.open_settings_requested.emit)
        layout.addWidget(self.btn_settings)

        # Update initial user badge state
        self.update_user_badge()

        # Window Controls (Minimize & Close only, no fullscreen)
        btn_min = QPushButton("🗕", self)
        btn_min.setProperty("class", "winBtn")
        btn_min.setToolTip("Minimize")
        btn_min.clicked.connect(self.parent_window.showMinimized if self.parent_window else self.showMinimized)
        layout.addWidget(btn_min)

        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("btnClose")
        btn_close.setProperty("class", "winBtn")
        btn_close.setToolTip("Close to Background")
        btn_close.clicked.connect(self.parent_window.close if self.parent_window else self.close)
        layout.addWidget(btn_close)

    def update_user_badge(self, profile: dict = None):
        if profile is None:
            profile = get_active_session_profile()
        is_guest = profile.get("is_guest", True) if profile else True
        if is_guest:
            self.btn_user.setText(t("title_user_badge_guest"))
            self.btn_user.setProperty("guest", "true")
        else:
            raw_username = profile.get("username", "@user")
            clean_name = raw_username.upper()[:12]
            self.btn_user.setText(f"[USR: {clean_name}]")
            self.btn_user.setProperty("guest", "false")
        self.btn_user.setToolTip(t("title_user_badge_tooltip"))
        # Refresh dynamic property styling
        self.btn_user.style().unpolish(self.btn_user)
        self.btn_user.style().polish(self.btn_user)

    def _open_donate(self):
        QDesktopServices.openUrl(QUrl("https://sociabuzz.com/emef/tribe"))

    def retranslate_ui(self):
        self.btn_donate.setText(f"[{t('btn_donate')}]")
        self.btn_donate.setToolTip(t("nav_donate_title"))
        self.btn_history.setText(f"[LOG] {t('nav_history')}")
        self.btn_history.setToolTip(t('nav_history_title'))
        self.btn_settings.setText(f"[CONFIG] {t('nav_settings')}")
        self.btn_settings.setToolTip(t("nav_settings_title"))
        self.update_user_badge()


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.parent_window and not self.parent_window.isMaximized():
            self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        # Maximize / fullscreen disabled for fixed layout utility console
        pass
