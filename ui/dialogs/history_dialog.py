import os
import subprocess
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QWidget, QFrame, QMessageBox,
    QSizePolicy
)
from backend.history import get_history, clear_history, delete_history_item
from backend.i18n import t

class HistoryDialog(QDialog):
    redownload_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"[LOG] {t('history_title')}")
        if parent and parent.windowIcon():
            self.setWindowIcon(parent.windowIcon())
        self.resize(760, 580)
        self.setMinimumWidth(620)
        self.setStyleSheet("""
            QDialog {
                background-color: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
            QFrame.histCard {
                background-color: #111216;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 10px;
            }
            QFrame.histCard:hover {
                background-color: #16171d;
                border-color: #3f3f46;
            }
            QLabel.histTitle {
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
                font-size: 13px;
            }
            QLabel.histMeta {
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
            }
            QPushButton.histBtn {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 3px 8px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.histBtn:hover {
                background-color: #1c1d24;
                color: #38bdf8;
                border-color: #38bdf8;
            }
            QPushButton.histBtnRedownload {
                background-color: #0c2134;
                border: 1px solid #0284c7;
                border-radius: 4px;
                padding: 3px 10px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton.histBtnRedownload:hover {
                background-color: #0e3b60;
                border-color: #38bdf8;
                color: #e0f2fe;
            }
            QPushButton.histBtnRedownload:pressed {
                background-color: #081a29;
            }
        """)
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # Header Row
        header_row = QHBoxLayout()
        header_lbl = QLabel(t("history_dlg_title"), self)
        header_lbl.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-size: 14px; font-weight: 800;")
        header_row.addWidget(header_lbl)

        header_row.addStretch()

        self.btn_clear = QPushButton(t("history_btn_clear_all"), self)
        self.btn_clear.setStyleSheet("color: #f43f5e; border-color: rgba(244,63,94,0.3);")
        self.btn_clear.clicked.connect(self._clear_all)
        header_row.addWidget(self.btn_clear)

        layout.addLayout(header_row)

        # Search / Filter Bar
        self.txt_search = QLineEdit(self)
        self.txt_search.setPlaceholderText(t("history_search_placeholder"))
        self.txt_search.textChanged.connect(self._filter_history)
        layout.addWidget(self.txt_search)

        # Scroll Area for List
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.container = QWidget()
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        # Close button
        btn_close = QPushButton(t("history_btn_close"), self)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignRight)

    def load_history(self):
        self.all_items = get_history()
        self._render_items(self.all_items)

    def _filter_history(self, text: str):
        query = text.strip().lower()
        if not query:
            filtered = self.all_items
        else:
            filtered = [item for item in self.all_items if query in str(item.get("title", "")).lower()]
        self._render_items(filtered)

    def _render_items(self, items: list):
        while self.list_layout.count() > 1:
            w = self.list_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        if not items:
            lbl_empty = QLabel(t("history_empty_ledger"), self.container)
            lbl_empty.setStyleSheet("color: #52525b; font-family: 'JetBrains Mono', monospace; font-style: italic; padding: 30px; text-align: center;")
            lbl_empty.setAlignment(Qt.AlignCenter)
            self.list_layout.insertWidget(0, lbl_empty)
            return

        for idx, item in enumerate(items):
            card = QFrame(self.container)
            card.setProperty("class", "histCard")
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(10, 8, 10, 8)
            c_layout.setSpacing(6)

            title_row = QHBoxLayout()
            idx_tag = QLabel(f"#{idx + 1:03d}", card)
            idx_tag.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;")
            title_row.addWidget(idx_tag)

            title = QLabel(item.get("title", "Unduhan"), card)
            title.setProperty("class", "histTitle")
            title.setWordWrap(True)
            title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            title_row.addWidget(title, 1)

            size_str = item.get("total") or item.get("filesize") or "--"
            lbl_size = QLabel(size_str, card)
            lbl_size.setStyleSheet("color: #fbbf24; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;")
            title_row.addWidget(lbl_size)
            c_layout.addLayout(title_row)

            # URL Display Row
            item_url = item.get("url") or ""
            if not item_url and isinstance(item.get("options"), dict):
                item_url = item.get("options", {}).get("url") or ""

            if item_url:
                url_row = QHBoxLayout()
                url_row.setSpacing(6)

                lbl_url_icon = QLabel("🔗", card)
                lbl_url_icon.setStyleSheet("color: #38bdf8; font-size: 11px; background: transparent;")
                url_row.addWidget(lbl_url_icon)

                lbl_url = QLabel(item_url, card)
                lbl_url.setCursor(Qt.PointingHandCursor)
                lbl_url.setWordWrap(True)
                lbl_url.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                lbl_url.setStyleSheet("""
                    color: #38bdf8;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 10.5px;
                    text-decoration: underline;
                    background: transparent;
                """)
                lbl_url.setToolTip(t("history_url_tooltip"))
                lbl_url.mousePressEvent = lambda _, u=item_url: self._trigger_redownload(u)
                url_row.addWidget(lbl_url, 1)

                btn_copy_url = QPushButton("[COPY]", card)
                btn_copy_url.setProperty("class", "histBtn")
                btn_copy_url.setStyleSheet("padding: 1px 6px; font-size: 9.5px; color: #a1a1aa;")
                btn_copy_url.setToolTip(t("history_btn_copy_tooltip"))
                def _make_copy_handler(b, u):
                    return lambda: self._copy_and_feedback(b, u)
                btn_copy_url.clicked.connect(_make_copy_handler(btn_copy_url, item_url))
                url_row.addWidget(btn_copy_url)

                c_layout.addLayout(url_row)

            # Meta & Actions
            meta_row = QHBoxLayout()
            meta_row.setSpacing(8)

            date_str = item.get("created_at") or item.get("updated_at") or "--"
            res_str = item.get("resolution") or item.get("format") or "--"
            lbl_meta = QLabel(f"[{res_str}]  |  {date_str}", card)
            lbl_meta.setProperty("class", "histMeta")
            meta_row.addWidget(lbl_meta, 1)

            # Actions
            filepath = item.get("filepath", "")
            item_id = item.get("id", "")

            # Re-download action button (always available if URL exists)
            if item_url:
                btn_redl = QPushButton(f"[RETRY] {t('history_btn_redownload')}", card)
                btn_redl.setProperty("class", "histBtnRedownload")
                btn_redl.setToolTip(t("history_redownload_tooltip"))
                btn_redl.clicked.connect(lambda _, u=item_url: self._trigger_redownload(u))
                meta_row.addWidget(btn_redl)

            if filepath and os.path.exists(filepath):
                btn_play = QPushButton(t("task_btn_play"), card)
                btn_play.setProperty("class", "histBtn")
                btn_play.clicked.connect(lambda _, p=filepath: self._open_file(p))
                meta_row.addWidget(btn_play)

                btn_fld = QPushButton(t("task_btn_dir"), card)
                btn_fld.setProperty("class", "histBtn")
                btn_fld.clicked.connect(lambda _, p=filepath: self._open_folder(p))
                meta_row.addWidget(btn_fld)

            btn_del = QPushButton(t("task_btn_del"), card)
            btn_del.setProperty("class", "histBtn")
            btn_del.setToolTip(t("history_del_tooltip"))
            btn_del.clicked.connect(lambda _, i=item_id: self._delete_item(i))
            meta_row.addWidget(btn_del)

            c_layout.addLayout(meta_row)
            self.list_layout.insertWidget(idx, card)

    def _trigger_redownload(self, url: str):
        if url:
            self.redownload_requested.emit(url)
            self.accept()

    def _copy_url(self, url: str):
        from PySide6.QtGui import QGuiApplication
        cb = QGuiApplication.clipboard()
        if cb and url:
            cb.setText(url)

    def _copy_and_feedback(self, btn, url: str):
        self._copy_url(url)
        btn.setText("[COPIED!]")
        btn.setStyleSheet("padding: 1px 6px; font-size: 9.5px; color: #34d399; border-color: #34d399;")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: [
            btn.setText("[COPY]"),
            btn.setStyleSheet("padding: 1px 6px; font-size: 9.5px; color: #a1a1aa;")
        ])

    def _open_file(self, path: str):
        try:
            if os.path.exists(path):
                os.startfile(path)
        except Exception:
            pass

    def _open_folder(self, path: str):
        try:
            folder = os.path.dirname(path) if os.path.isfile(path) else path
            if os.path.exists(folder):
                subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            else:
                os.startfile(folder)
        except Exception:
            pass

    def _delete_item(self, item_id: str):
        delete_history_item(item_id)
        self.load_history()

    def _clear_all(self):
        confirm = QMessageBox.question(
            self, t("history_clear_confirm_title"),
            t("history_clear_confirm_msg"),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            clear_history()
            self.load_history()
