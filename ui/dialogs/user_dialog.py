import sys
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QMessageBox
)

from backend.i18n import t
from backend.config import (
    get_active_session_profile, register_and_activate_user,
    logout_to_guest, get_settings
)


class WhoAreYouDialog(QDialog):
    user_logged_in = Signal(dict)
    guest_session_started = Signal()

    def __init__(self, parent=None, is_editing: bool = False):
        super().__init__(parent)
        self.is_editing = is_editing
        self.drag_position = QPoint()

        self.setWindowTitle(t("who_dlg_title"))
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())
        self.setFixedSize(540, 430)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._init_ui()
        self._load_current_data()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 10px;
            }
            QFrame#cardFrame {
                background-color: #0e0f14;
                border: 1px solid #22232a;
                border-radius: 8px;
            }
            QLabel.eyebrow {
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                color: #38bdf8;
            }
            QLabel.heading {
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: 800;
                color: #f4f4f5;
                letter-spacing: -0.3px;
            }
            QLabel.subText {
                font-size: 12px;
                color: #a1a1aa;
                line-height: 1.4;
            }
            QLabel.fieldLabel {
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                color: #cbd5e1;
            }
            QLineEdit, QComboBox {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 8px 12px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', 'Segoe UI', monospace;
                font-size: 12px;
                selection-background-color: #38bdf8;
                selection-color: #09090b;
            }
            QLineEdit:focus, QComboBox:focus {
                border-color: #38bdf8;
                background-color: #181a22;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #71717a;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #14151b;
                border: 1px solid #27272a;
                selection-background-color: #27272a;
                selection-color: #38bdf8;
                color: #f4f4f5;
                padding: 4px;
            }
            QPushButton#btnSubmit {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 10px 16px;
                color: #09090b;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton#btnSubmit:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
            QPushButton#btnSubmit:pressed {
                background-color: #0284c7;
            }
            QPushButton#btnGuest {
                background-color: #14151b;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 9px 14px;
                color: #fbbf24;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#btnGuest:hover {
                background-color: #1f212a;
                border-color: #3f3f46;
                color: #fef08a;
            }
            QPushButton#btnCloseTop {
                background-color: transparent;
                border: none;
                color: #71717a;
                font-size: 13px;
                font-weight: 700;
                border-radius: 4px;
                width: 28px;
                height: 28px;
            }
            QPushButton#btnCloseTop:hover {
                background-color: #27272a;
                color: #f4f4f5;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(14)

        # Top Bar: Eyebrow + Close Button (✕)
        top_h = QHBoxLayout()
        self.lbl_eyebrow = QLabel(t("who_dlg_eyebrow"), self)
        self.lbl_eyebrow.setProperty("class", "eyebrow")
        top_h.addWidget(self.lbl_eyebrow)

        top_h.addStretch()

        self.btn_close_top = QPushButton("✕", self)
        self.btn_close_top.setObjectName("btnCloseTop")
        self.btn_close_top.clicked.connect(self._on_skip_or_close)
        top_h.addWidget(self.btn_close_top)
        layout.addLayout(top_h)

        # Header Title
        self.lbl_heading = QLabel(t("who_dlg_heading"), self)
        self.lbl_heading.setProperty("class", "heading")
        layout.addWidget(self.lbl_heading)

        # Card Form Container
        card = QFrame(self)
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        # 1. Name / Username
        self.lbl_name = QLabel(t("who_name_label"), card)
        self.lbl_name.setProperty("class", "fieldLabel")
        card_layout.addWidget(self.lbl_name)

        self.txt_name = QLineEdit(card)
        self.txt_name.setPlaceholderText(t("who_name_placeholder"))
        self.txt_name.returnPressed.connect(self._on_submit)
        card_layout.addWidget(self.txt_name)

        # 2. Role / Profession
        self.lbl_role = QLabel(t("who_role_label"), card)
        self.lbl_role.setProperty("class", "fieldLabel")
        card_layout.addWidget(self.lbl_role)

        self.cbo_role = QComboBox(card)
        self._populate_roles()
        card_layout.addWidget(self.cbo_role)

        # 3. Contact / Social (Optional)
        self.lbl_contact = QLabel(t("who_contact_label"), card)
        self.lbl_contact.setProperty("class", "fieldLabel")
        card_layout.addWidget(self.lbl_contact)

        self.txt_contact = QLineEdit(card)
        self.txt_contact.setPlaceholderText(t("who_contact_placeholder"))
        self.txt_contact.returnPressed.connect(self._on_submit)
        card_layout.addWidget(self.txt_contact)

        layout.addWidget(card)

        layout.addStretch()

        # Action Buttons Bottom
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_guest = QPushButton(t("who_btn_guest"), self)
        self.btn_guest.setObjectName("btnGuest")
        self.btn_guest.clicked.connect(self._on_skip_or_close)
        btn_layout.addWidget(self.btn_guest)

        btn_layout.addStretch()

        self.btn_submit = QPushButton(t("who_btn_submit"), self)
        self.btn_submit.setObjectName("btnSubmit")
        self.btn_submit.clicked.connect(self._on_submit)
        btn_layout.addWidget(self.btn_submit)

        layout.addLayout(btn_layout)

    def _populate_roles(self):
        self.cbo_role.clear()
        self.roles_data = [
            ("video_editor", t("role_video_editor")),
            ("content_creator", t("role_content_creator")),
            ("student", t("role_student")),
            ("audio_engineer", t("role_audio_engineer")),
            ("general", t("role_general")),
        ]
        for key, text in self.roles_data:
            self.cbo_role.addItem(text, userData=key)

    def _load_current_data(self):
        cur = get_active_session_profile()
        if cur and not cur.get("is_guest"):
            username = cur.get("username", "")
            if username.startswith("@"):
                username = username[1:]
            self.txt_name.setText(username)
            self.txt_contact.setText(cur.get("contact", ""))

            role_str = cur.get("role", "")
            for i in range(self.cbo_role.count()):
                item_text = self.cbo_role.itemText(i)
                if (role_str and role_str in item_text) or (item_text and item_text in role_str):
                    self.cbo_role.setCurrentIndex(i)
                    break
        else:
            self.txt_name.setFocus()

    def _on_submit(self):
        raw_name = self.txt_name.text().strip()
        if not raw_name:
            QMessageBox.warning(self, t("dialog_warning"), t("who_err_empty_name"))
            self.txt_name.setFocus()
            return

        role = self.cbo_role.currentText()
        contact = self.txt_contact.text().strip()

        try:
            profile = register_and_activate_user(raw_name, role=role, contact=contact)
            self.user_logged_in.emit(profile)
        except Exception as e:
            print(f"[!] Warning activating user: {e}")
            fallback_profile = {
                "user_id": "usr_local",
                "username": f"@{raw_name}" if not raw_name.startswith("@") else raw_name,
                "role": role,
                "contact": contact,
                "is_guest": False
            }
            self.user_logged_in.emit(fallback_profile)
        finally:
            self.accept()

    def _on_skip_or_close(self):
        # Switch to Guest mode
        try:
            logout_to_guest()
            self.guest_session_started.emit()
        except Exception as e:
            print(f"[!] Warning entering guest mode: {e}")
        finally:
            self.reject()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._on_skip_or_close()
        else:
            super().keyPressEvent(event)

    def retranslate_ui(self):
        self.setWindowTitle(t("who_dlg_title"))
        self.lbl_eyebrow.setText(t("who_dlg_eyebrow"))
        self.lbl_heading.setText(t("who_dlg_heading"))
        self.lbl_name.setText(t("who_name_label"))
        self.txt_name.setPlaceholderText(t("who_name_placeholder"))
        self.lbl_role.setText(t("who_role_label"))
        self.lbl_contact.setText(t("who_contact_label"))
        self.txt_contact.setPlaceholderText(t("who_contact_placeholder"))
        self.btn_submit.setText(t("who_btn_submit"))
        self.btn_guest.setText(t("who_btn_guest"))

        cur_idx = self.cbo_role.currentIndex()
        self._populate_roles()
        if 0 <= cur_idx < self.cbo_role.count():
            self.cbo_role.setCurrentIndex(cur_idx)

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
