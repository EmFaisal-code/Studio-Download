import sys
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)

from backend.i18n import t
from backend.config import (
    get_active_session_profile, logout_to_guest
)
from ui.dialogs.user_dialog import WhoAreYouDialog


class UserProfileDialog(QDialog):
    profile_switched = Signal(dict)
    guest_mode_activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_position = QPoint()

        self.setWindowTitle(t("profile_dlg_title"))
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())
        self.setFixedSize(430, 220)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._init_ui()
        self.refresh_profile()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0e12;
                border: 1px solid #27272a;
                border-radius: 12px;
            }
            QLabel#avatarCircle {
                background-color: #181920;
                border: 1px solid #2a2b34;
                border-radius: 24px;
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 20px;
                color: #f4f4f5;
                qproperty-alignment: AlignCenter;
            }
            QLabel#avatarCircle[guest="true"] {
                background-color: #1a1814;
                border-color: #3f321d;
                color: #fbbf24;
            }
            QLabel#avatarCircle[guest="false"] {
                background-color: #0c2838;
                border-color: #0369a1;
                color: #38bdf8;
            }
            QLabel#userName {
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 17px;
                font-weight: 700;
                color: #f4f4f5;
            }
            QLabel#userRole {
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 12px;
                color: #a1a1aa;
            }
            QPushButton.btnPrimary {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 7px 16px;
                color: #09090b;
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton.btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton.btnSecondary {
                background-color: #181920;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 7px 14px;
                color: #e4e4e7;
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton.btnSecondary:hover {
                background-color: #24252e;
                border-color: #3f3f46;
                color: #ffffff;
            }
            QPushButton.btnDanger {
                background-color: transparent;
                border: 1px solid #3f3f46;
                border-radius: 6px;
                padding: 7px 14px;
                color: #f87171;
                font-family: 'Segoe UI', 'JetBrains Mono', sans-serif;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton.btnDanger:hover {
                background-color: #2b1418;
                border-color: #dc2626;
                color: #fca5a5;
            }
            QPushButton.btnClose {
                background-color: transparent;
                border: none;
                color: #71717a;
                font-size: 14px;
                font-weight: 700;
                border-radius: 4px;
                width: 28px;
                height: 28px;
            }
            QPushButton.btnClose:hover {
                background-color: #22232a;
                color: #f4f4f5;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(22, 16, 22, 18)
        main_layout.setSpacing(16)

        # Top Header Bar: Clean Eyebrow + Close (✕)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.lbl_eyebrow = QLabel(t("profile_dlg_eyebrow"), self)
        self.lbl_eyebrow.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700; color: #71717a; letter-spacing: 0.5px;")
        top_bar.addWidget(self.lbl_eyebrow)

        top_bar.addStretch()

        self.btn_close_top = QPushButton("✕", self)
        self.btn_close_top.setProperty("class", "btnClose")
        self.btn_close_top.clicked.connect(self.close)
        top_bar.addWidget(self.btn_close_top)

        main_layout.addLayout(top_bar)

        # Profile Row: [Avatar 48x48]  [Name & Role]
        profile_row = QHBoxLayout()
        profile_row.setSpacing(14)
        profile_row.setAlignment(Qt.AlignVCenter)

        self.avatar_circle = QLabel("👤", self)
        self.avatar_circle.setObjectName("avatarCircle")
        self.avatar_circle.setFixedSize(48, 48)
        profile_row.addWidget(self.avatar_circle)

        name_box = QVBoxLayout()
        name_box.setSpacing(3)
        name_box.setAlignment(Qt.AlignVCenter)

        self.lbl_name = QLabel(t("profile_guest_name"), self)
        self.lbl_name.setObjectName("userName")
        name_box.addWidget(self.lbl_name)

        self.lbl_role = QLabel(t("profile_guest_role"), self)
        self.lbl_role.setObjectName("userRole")
        name_box.addWidget(self.lbl_role)

        profile_row.addLayout(name_box, 1)

        main_layout.addLayout(profile_row)

        main_layout.addStretch()

        # Bottom Buttons
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)

        self.btn_primary = QPushButton(t("profile_btn_login"), self)
        self.btn_primary.setProperty("class", "btnPrimary")
        self.btn_primary.clicked.connect(self._on_primary_clicked)
        self.btn_layout.addWidget(self.btn_primary)

        self.btn_logout = QPushButton(t("profile_btn_logout"), self)
        self.btn_logout.setProperty("class", "btnDanger")
        self.btn_logout.clicked.connect(self._switch_to_guest)
        self.btn_layout.addWidget(self.btn_logout)

        self.btn_layout.addStretch()

        self.btn_close = QPushButton(t("profile_btn_close"), self)
        self.btn_close.setProperty("class", "btnSecondary")
        self.btn_close.clicked.connect(self.close)
        self.btn_layout.addWidget(self.btn_close)

        main_layout.addLayout(self.btn_layout)

    def refresh_profile(self):
        profile = get_active_session_profile()
        is_guest = profile.get("is_guest", True) if profile else True

        if is_guest:
            self.avatar_circle.setProperty("guest", "true")
            self.avatar_circle.setText("👤")
            self.lbl_name.setText(t("profile_guest_name"))
            self.lbl_role.setText(t("profile_guest_role"))

            self.btn_primary.setText(t("profile_btn_login"))
            self.btn_logout.setVisible(False)
        else:
            self.avatar_circle.setProperty("guest", "false")
            raw_username = profile.get("username", "@user")
            initial = raw_username.lstrip("@")[:1].upper() or "U"
            self.avatar_circle.setText(initial)
            self.lbl_name.setText(raw_username)
            role = profile.get("role") or t("role_video_editor")
            self.lbl_role.setText(role)

            self.btn_primary.setText(t("profile_btn_switch"))
            self.btn_logout.setVisible(True)

        self.avatar_circle.style().unpolish(self.avatar_circle)
        self.avatar_circle.style().polish(self.avatar_circle)

    def _on_primary_clicked(self):
        # Open WhoAreYou onboarding dialog
        dlg = WhoAreYouDialog(self, is_editing=True)
        dlg.user_logged_in.connect(self._on_user_logged_in)
        dlg.guest_session_started.connect(self._on_guest_started)
        dlg.exec()

    def _on_user_logged_in(self, profile: dict):
        self.refresh_profile()
        self.profile_switched.emit(profile)

    def _on_guest_started(self):
        self.refresh_profile()
        self.guest_mode_activated.emit()

    def _switch_to_guest(self):
        try:
            logout_to_guest()
        except Exception as e:
            print(f"[!] Warning switching to guest: {e}")
        self.refresh_profile()
        self.guest_mode_activated.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def retranslate_ui(self):
        self.setWindowTitle(t("profile_dlg_title"))
        self.lbl_eyebrow.setText(t("profile_dlg_eyebrow"))
        self.btn_close.setText(t("profile_btn_close"))
        self.refresh_profile()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self.drag_position.isNull():
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = QPoint()
        super().mouseReleaseEvent(event)
