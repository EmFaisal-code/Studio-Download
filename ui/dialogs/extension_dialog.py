import os
import subprocess
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QApplication
)
from backend.app import resolve_extension_dir
from backend.i18n import t

class ExtensionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"[EXT] {t('tab_ext_desc').replace('// ', '')}")
        self.setFixedSize(680, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QLabel.groupTitle {
                color: #818cf8;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 11px;
                letter-spacing: 0.5px;
                margin-top: 4px;
            }
            QFrame.guideCard {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton.actionBtn {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 6px 12px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.actionBtn:hover {
                background-color: #1c1d24;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton#btnPrimary {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
                color: #09090b;
                font-weight: 700;
            }
            QPushButton#btnPrimary:hover {
                background-color: #7dd3fc;
                border-color: #7dd3fc;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)

        # Header
        header_row = QHBoxLayout()
        v_head = QVBoxLayout()
        lbl_eyebrow = QLabel("// COMPANION_BROWSER_EXTENSION", self)
        lbl_eyebrow.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600;")
        v_head.addWidget(lbl_eyebrow)

        lbl_title = QLabel(t("tab_ext_desc").replace("// ", ""), self)
        lbl_title.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 800;")
        v_head.addWidget(lbl_title)
        header_row.addLayout(v_head, 1)

        status_tag = QLabel("[READY v1.0] [PORT: 8080]", self)
        status_tag.setStyleSheet("color: #34d399; background: #062316; border: 1px solid #059669; border-radius: 4px; padding: 3px 8px; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;")
        header_row.addWidget(status_tag)
        layout.addLayout(header_row)

        desc = QLabel(t("ext_desc"), self)
        desc.setStyleSheet("color: #a1a1aa; font-size: 11.5px; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Card 1: Extension Folder Path
        lbl_sec1 = QLabel(f"[01] {t('ext_path_label')}", self)
        lbl_sec1.setProperty("class", "groupTitle")
        layout.addWidget(lbl_sec1)

        card_path = QFrame(self)
        card_path.setProperty("class", "guideCard")
        c1_layout = QVBoxLayout(card_path)
        c1_layout.setSpacing(8)

        ext_dir = resolve_extension_dir()
        self.ext_path_str = os.path.normpath(str(ext_dir))

        path_row = QHBoxLayout()
        self.txt_path = QLineEdit(self.ext_path_str, self)
        self.txt_path.setReadOnly(True)
        self.txt_path.setStyleSheet("background: #16171d; border: 1px solid #27272a; border-radius: 6px; padding: 6px 10px; color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        path_row.addWidget(self.txt_path, 1)

        self.btn_open_folder = QPushButton(t("btn_open_ext"), self)
        self.btn_open_folder.setProperty("class", "actionBtn")
        self.btn_open_folder.setObjectName("btnPrimary")
        self.btn_open_folder.clicked.connect(self._open_folder)
        path_row.addWidget(self.btn_open_folder)

        self.btn_copy_path = QPushButton(t("btn_copy_ext_path"), self)
        self.btn_copy_path.setProperty("class", "actionBtn")
        self.btn_copy_path.clicked.connect(self._copy_path)
        path_row.addWidget(self.btn_copy_path)
        c1_layout.addLayout(path_row)
        layout.addWidget(card_path)

        # Card 2: 3-Step Installation Guide
        lbl_sec2 = QLabel(f"[02] {t('ext_guide_title')}", self)
        lbl_sec2.setProperty("class", "groupTitle")
        layout.addWidget(lbl_sec2)

        card_guide = QFrame(self)
        card_guide.setProperty("class", "guideCard")
        c2_layout = QVBoxLayout(card_guide)
        c2_layout.setSpacing(8)

        # Step 1
        s1_row = QHBoxLayout()
        s1_text = QLabel(t("ext_step1"), self)
        s1_text.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        s1_text.setWordWrap(True)
        s1_row.addWidget(s1_text, 1)

        btn_copy_url = QPushButton(t("btn_copy_ext_url"), self)
        btn_copy_url.setProperty("class", "actionBtn")
        btn_copy_url.setStyleSheet("padding: 3px 10px; font-size: 10.5px;")
        btn_copy_url.clicked.connect(lambda: self._copy_text("chrome://extensions", btn_copy_url))
        s1_row.addWidget(btn_copy_url)
        c2_layout.addLayout(s1_row)

        # Step 2
        s2_text = QLabel(t("ext_step2"), self)
        s2_text.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        s2_text.setWordWrap(True)
        c2_layout.addWidget(s2_text)

        # Step 3
        s3_text = QLabel(t("ext_step3"), self)
        s3_text.setStyleSheet("color: #d4d4d8; font-family: 'JetBrains Mono', monospace; font-size: 11px;")
        s3_text.setWordWrap(True)
        c2_layout.addWidget(s3_text)

        layout.addWidget(card_guide)

        # Card 3: Features & Workflow
        lbl_sec3 = QLabel(f"[03] {t('ext_features_title')}", self)
        lbl_sec3.setProperty("class", "groupTitle")
        layout.addWidget(lbl_sec3)

        card_features = QFrame(self)
        card_features.setProperty("class", "guideCard")
        c3_layout = QVBoxLayout(card_features)
        c3_layout.setSpacing(6)

        f1 = QLabel(t("ext_feat_cookie"), self)
        f1.setStyleSheet("color: #a1a1aa; font-size: 11px; line-height: 1.3;")
        f1.setWordWrap(True)
        c3_layout.addWidget(f1)

        f2 = QLabel(t("ext_feat_stream"), self)
        f2.setStyleSheet("color: #a1a1aa; font-size: 11px; line-height: 1.3;")
        f2.setWordWrap(True)
        c3_layout.addWidget(f2)

        layout.addWidget(card_features)

        layout.addStretch()

        # Bottom Close Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton(t("btn_close_dialog"), self)
        btn_close.setProperty("class", "actionBtn")
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _open_folder(self):
        try:
            if os.path.exists(self.ext_path_str):
                os.startfile(self.ext_path_str)
            else:
                subprocess.Popen(f'explorer "{self.ext_path_str}"')
        except Exception:
            subprocess.Popen(f'explorer "{self.ext_path_str}"')

    def _copy_path(self):
        QApplication.clipboard().setText(self.ext_path_str)
        self.btn_copy_path.setText(t("copied_badge"))
        QTimer.singleShot(2000, lambda: self.btn_copy_path.setText(t("btn_copy_ext_path")))

    def _copy_text(self, text, btn):
        QApplication.clipboard().setText(text)
        btn.setText(t("copied_badge"))
        QTimer.singleShot(2000, lambda: btn.setText(t("btn_copy_ext_url")))
