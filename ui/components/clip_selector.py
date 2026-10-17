import re
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QMessageBox
)
from backend.i18n import t
from backend.parser import parse_time_str, format_duration, format_duration_hms, format_time_label

class ClipRowWidget(QFrame):
    delete_clicked = Signal(object)
    changed = Signal()

    def __init__(self, index: int, start_sec: int = 0, end_sec: int = 60, max_sec: int = 0, parent=None):
        super().__init__(parent)
        self.max_sec = max_sec
        self.setObjectName("clipRow")
        self.setFixedHeight(46)
        self.setStyleSheet("""
            QFrame#clipRow {
                background-color: #121318;
                border: 1px solid #27272a;
                border-left: 3px solid #38bdf8;
                border-radius: 6px;
                padding: 0 8px;
            }
            QFrame#clipRow:hover {
                border-color: #3f3f46;
                border-left-color: #38bdf8;
                background-color: #15161d;
            }
            QLabel {
                background: transparent;
                font-family: 'JetBrains Mono', monospace;
            }
            QLineEdit {
                background-color: #0c0d11;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 0 6px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
            QPushButton.delBtn {
                background-color: transparent;
                border: 1px solid rgba(244, 63, 94, 0.3);
                border-radius: 4px;
                color: #f43f5e;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 0 6px;
            }
            QPushButton.delBtn:hover {
                background-color: #f43f5e;
                color: #ffffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # Index badge
        self.lbl_idx = QLabel(f"KLIP #{index}", self)
        self.lbl_idx.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700; min-width: 55px;")
        layout.addWidget(self.lbl_idx)

        # Start input
        lbl_start = QLabel(t("clip_start_label"), self)
        lbl_start.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 600;")
        layout.addWidget(lbl_start)

        self.txt_start = QLineEdit(self)
        self.txt_start.setFixedWidth(85)
        self.txt_start.setFixedHeight(26)
        self.txt_start.setAlignment(Qt.AlignCenter)
        self.txt_start.setText(format_duration_hms(start_sec))
        self.txt_start.setToolTip(t("clip_start_tip"))
        self.txt_start.textChanged.connect(self._on_input_changed)
        layout.addWidget(self.txt_start)

        # Arrow
        lbl_arrow = QLabel("➔", self)
        lbl_arrow.setStyleSheet("color: #52525b; font-size: 11px;")
        layout.addWidget(lbl_arrow)

        # End input
        lbl_end = QLabel(t("clip_end_label"), self)
        lbl_end.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 600;")
        layout.addWidget(lbl_end)

        self.txt_end = QLineEdit(self)
        self.txt_end.setFixedWidth(85)
        self.txt_end.setFixedHeight(26)
        self.txt_end.setAlignment(Qt.AlignCenter)
        self.txt_end.setText(format_duration_hms(end_sec))
        self.txt_end.setToolTip(t("clip_end_tip"))
        self.txt_end.textChanged.connect(self._on_input_changed)
        layout.addWidget(self.txt_end)

        # Duration preview label
        self.lbl_duration = QLabel("", self)
        self.lbl_duration.setStyleSheet("color: #fbbf24; font-size: 10.5px; font-weight: 700; min-width: 95px;")
        layout.addWidget(self.lbl_duration)

        # Optional label / title input
        self.txt_label = QLineEdit(self)
        self.txt_label.setFixedHeight(26)
        self.txt_label.setPlaceholderText("// Label klip (opsional)...")
        self.txt_label.setStyleSheet("font-weight: 500; font-size: 11px;")
        self.txt_label.textChanged.connect(lambda: self.changed.emit())
        layout.addWidget(self.txt_label, 1)

        # Delete button
        self.btn_del = QPushButton("✕", self)
        self.btn_del.setProperty("class", "delBtn")
        self.btn_del.setFixedSize(26, 26)
        self.btn_del.setToolTip("Hapus klip ini")
        self.btn_del.clicked.connect(lambda: self.delete_clicked.emit(self))
        layout.addWidget(self.btn_del)

        self.size_estimator = None
        self._update_duration_display()

    def set_index(self, index: int):
        self.lbl_idx.setText(f"KLIP #{index}")

    def _on_input_changed(self):
        self._update_duration_display()
        self.changed.emit()

    def _update_duration_display(self):
        s_sec = parse_time_str(self.txt_start.text())
        e_sec = parse_time_str(self.txt_end.text())
        if e_sec > s_sec:
            diff = e_sec - s_sec
            dur_str = format_duration_hms(diff)
            est_str = ""
            if callable(getattr(self, "size_estimator", None)):
                try:
                    est_str = self.size_estimator(diff)
                except Exception:
                    pass
            txt = f"[{dur_str} | {est_str}]" if est_str else f"[{dur_str}]"
            self.lbl_duration.setText(txt)
            self.lbl_duration.setStyleSheet("color: #fbbf24; font-size: 10.5px; font-weight: 700; min-width: 95px;")
        else:
            self.lbl_duration.setText("[! WAKTU SALAH]")
            self.lbl_duration.setStyleSheet("color: #f43f5e; font-size: 10px; font-weight: 700; min-width: 95px;")

    def get_data(self) -> dict:
        s_sec = parse_time_str(self.txt_start.text())
        e_sec = parse_time_str(self.txt_end.text())
        is_valid = (e_sec > s_sec)
        label_text = self.txt_label.text().strip()
        time_tag = f"[{format_time_label(s_sec)}-{format_time_label(e_sec)}]"
        return {
            "start": s_sec,
            "end": e_sec,
            "start_str": self.txt_start.text().strip(),
            "end_str": self.txt_end.text().strip(),
            "duration": max(0, e_sec - s_sec),
            "label": label_text,
            "time_tag": time_tag,
            "is_valid": is_valid
        }


class ClipSelectorWidget(QFrame):
    clips_changed = Signal(list)
    toggled = Signal(bool)
    open_trimmer_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.max_duration_seconds = 0
        self.max_duration_str = "--"
        self.clip_rows = []
        self.setObjectName("clipSelectorCard")
        self.setStyleSheet("""
            QFrame#clipSelectorCard {
                background-color: #0e0f13;
                border: 1px solid #27272a;
                border-radius: 8px;
                padding: 0px;
            }
            QCheckBox {
                color: #e4e4e7;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3f3f46;
                border-radius: 4px;
                background-color: #14151b;
            }
            QCheckBox::indicator:checked {
                background-color: #38bdf8;
                border-color: #38bdf8;
                image: none;
            }
            QPushButton#btnAddClip {
                background-color: rgba(56, 189, 248, 0.08);
                border: 1px dashed rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 6px 12px;
            }
            QPushButton#btnAddClip:hover {
                background-color: rgba(56, 189, 248, 0.18);
                border-color: #38bdf8;
            }
            QPushButton#btnOpenTrimmer {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid #38bdf8;
                border-radius: 6px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
                padding: 6px 14px;
            }
            QPushButton#btnOpenTrimmer:hover {
                background-color: #38bdf8;
                color: #09090b;
            }
        """)

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        # Header toggle bar
        header_h = QHBoxLayout()
        header_h.setSpacing(12)

        self.chk_enable = QCheckBox(t("clip_enable_toggle"), self)
        self.chk_enable.toggled.connect(self._on_toggled)
        header_h.addWidget(self.chk_enable)

        # Prominent ALWAYS VISIBLE button in header
        self.btn_header_trimmer = QPushButton(t("trimmer_open_btn"), self)
        self.btn_header_trimmer.setObjectName("btnOpenTrimmer")
        self.btn_header_trimmer.setFixedHeight(26)
        self.btn_header_trimmer.setCursor(Qt.PointingHandCursor)
        self.btn_header_trimmer.clicked.connect(self._on_open_trimmer_clicked)
        header_h.addWidget(self.btn_header_trimmer)

        header_h.addStretch()

        self.lbl_badge = QLabel("", self)
        self.lbl_badge.setStyleSheet("color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700; background: #0e1926; border: 1px solid #1a3556; border-radius: 4px; padding: 2px 8px;")
        self.lbl_badge.setVisible(False)
        header_h.addWidget(self.lbl_badge)

        main_layout.addLayout(header_h)

        # Body container for clips list
        self.body_container = QWidget(self)
        self.body_layout = QVBoxLayout(self.body_container)
        self.body_layout.setContentsMargins(0, 4, 0, 0)
        self.body_layout.setSpacing(8)

        # Helper text
        self.lbl_helper = QLabel("// Tentukan satu atau beberapa rentang durasi. Setiap rentang akan dipotong & diunduh sebagai file klip terpisah:", self.body_container)
        self.lbl_helper.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px;")
        self.lbl_helper.setWordWrap(True)
        self.body_layout.addWidget(self.lbl_helper)

        # Rows container
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(6)
        self.body_layout.addLayout(self.rows_layout)

        # Action bar under clips (Add clip button + Open Visual Trimmer button)
        actions_h = QHBoxLayout()
        actions_h.setSpacing(8)

        self.btn_add_clip = QPushButton(t("clip_add_btn"), self.body_container)
        self.btn_add_clip.setObjectName("btnAddClip")
        self.btn_add_clip.setFixedHeight(30)
        self.btn_add_clip.clicked.connect(self._on_add_clip_clicked)
        actions_h.addWidget(self.btn_add_clip)


        actions_h.addStretch()
        self.body_layout.addLayout(actions_h)

        self.body_container.setVisible(False)
        main_layout.addWidget(self.body_container)

    def retranslate_ui(self):
        self.chk_enable.setText(t("clip_enable_toggle"))
        self.btn_header_trimmer.setText(t("trimmer_open_btn"))
        self.btn_add_clip.setText(t("clip_add_btn"))
        self._update_clips()

    def set_max_duration(self, seconds: int, duration_str: str):
        self.max_duration_seconds = max(0, int(seconds or 0))
        self.max_duration_str = duration_str or "--"

    def _on_open_trimmer_clicked(self):
        if not self.chk_enable.isChecked():
            self.chk_enable.setChecked(True)
        self.open_trimmer_requested.emit()

    def _on_toggled(self, checked: bool):
        self.body_container.setVisible(checked)
        self.lbl_badge.setVisible(checked)
        if checked and len(self.clip_rows) == 0:
            # Add initial default clip: 1 hour if video >= 1 hour, otherwise min(max_duration, 300)
            if self.max_duration_seconds >= 3600:
                end_val = min(self.max_duration_seconds, 3600)
            elif self.max_duration_seconds > 0:
                end_val = min(self.max_duration_seconds, 300)
            else:
                end_val = 3600
            self.add_clip(0, end_val)
        self._update_clips()
        self.toggled.emit(checked)

    def _on_add_clip_clicked(self):
        # Calculate smart default start from last clip's end
        start_sec = 0
        step = 3600 if self.max_duration_seconds >= 3600 else 300
        if self.clip_rows:
            last_end = self.clip_rows[-1].get_data()["end"]
            start_sec = last_end
        end_sec = start_sec + step
        if self.max_duration_seconds > 0:
            end_sec = min(end_sec, self.max_duration_seconds)
            if start_sec >= self.max_duration_seconds:
                start_sec = max(0, self.max_duration_seconds - step)
                end_sec = self.max_duration_seconds

        self.add_clip(start_sec, end_sec)

    def set_size_estimator(self, estimator_fn):
        self.size_estimator = estimator_fn
        for row in self.clip_rows:
            row.size_estimator = estimator_fn
            row._update_duration_display()

    def add_clip(self, start_sec: int = 0, end_sec: int = 3600):
        idx = len(self.clip_rows) + 1
        row = ClipRowWidget(idx, start_sec, end_sec, self.max_duration_seconds, self.body_container)
        if hasattr(self, "size_estimator"):
            row.size_estimator = self.size_estimator
            row._update_duration_display()
        row.delete_clicked.connect(self._on_delete_row)
        row.changed.connect(self._update_clips)
        self.rows_layout.addWidget(row)
        self.clip_rows.append(row)
        self._update_clips()

    def _on_delete_row(self, row_widget):
        if len(self.clip_rows) <= 1:
            # If deleting the only row, just uncheck the toggle
            self.chk_enable.setChecked(False)
            return

        if row_widget in self.clip_rows:
            self.clip_rows.remove(row_widget)
            self.rows_layout.removeWidget(row_widget)
            row_widget.deleteLater()

        # Re-index remaining rows
        for i, row in enumerate(self.clip_rows):
            row.set_index(i + 1)

        self._update_clips()

    def _update_clips(self):
        clips = self.get_clips()
        count = len(clips)
        self.lbl_badge.setText(f"[KLIP AKTIF: {count}]")
        self.clips_changed.emit(clips)

    def is_enabled(self) -> bool:
        return self.chk_enable.isChecked()

    def get_clips(self) -> list:
        if not self.chk_enable.isChecked():
            return []
        res = []
        for row in self.clip_rows:
            data = row.get_data()
            if data["is_valid"]:
                res.append(data)
        return res

    def validate_clips(self) -> tuple[bool, str]:
        if not self.chk_enable.isChecked():
            return True, ""
        if not self.clip_rows:
            return False, "Belum ada klip yang ditentukan."
        for i, row in enumerate(self.clip_rows):
            data = row.get_data()
            if not data["is_valid"]:
                return False, t("clip_err_invalid").format(idx=i + 1)
        return True, ""

    def set_clips(self, clips_list: list):
        """Programmatically set clips from external source (like VisualTrimmerDialog)."""
        while self.clip_rows:
            row = self.clip_rows.pop(0)
            self.rows_layout.removeWidget(row)
            row.deleteLater()

        if clips_list:
            self.chk_enable.setChecked(True)
            self.body_container.setVisible(True)
            self.lbl_badge.setVisible(True)
            for c in clips_list:
                s_sec = c.get("start", 0)
                e_sec = c.get("end", 60)
                lbl = c.get("label", "")
                idx = len(self.clip_rows) + 1
                row = ClipRowWidget(idx, s_sec, e_sec, self.max_duration_seconds, self.body_container)
                if lbl:
                    row.txt_label.setText(lbl)
                if hasattr(self, "size_estimator") and self.size_estimator:
                    row.size_estimator = self.size_estimator
                    row._update_duration_display()
                row.delete_clicked.connect(self._on_delete_row)
                row.changed.connect(self._update_clips)
                self.rows_layout.addWidget(row)
                self.clip_rows.append(row)
        self._update_clips()

    def reset(self):
        self.chk_enable.setChecked(False)
        while self.clip_rows:
            row = self.clip_rows.pop(0)
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self.body_container.setVisible(False)
        self.lbl_badge.setVisible(False)
