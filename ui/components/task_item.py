import os
import subprocess
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy
)
from backend.i18n import t

class ElidedLabel(QLabel):
    """
    A QLabel that elides overflowing text with an ellipsis (...) instead of
    expanding its minimumSizeHint width to the full string width, preventing
    parent layouts and scroll areas from horizontally stretching or clipping.
    """
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text or ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if self._full_text:
            self.setToolTip(self._full_text)

    def set_full_text(self, text: str, update_tooltip: bool = True):
        self._full_text = text or ""
        if update_tooltip:
            self.setToolTip(self._full_text)
        self._update_elided()

    def setText(self, text: str):
        self.set_full_text(text)

    def text(self) -> str:
        return self._full_text

    def minimumSizeHint(self) -> QSize:
        sh = super().minimumSizeHint()
        return QSize(50, sh.height() if sh.height() > 0 else 18)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self):
        if not self._full_text:
            super().setText("")
            return
        w = max(10, self.width() - 4)
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.ElideRight, w)
        if super().text() != elided:
            super().setText(elided)

class TaskItemWidget(QFrame):
    pause_clicked = Signal(str)
    resume_clicked = Signal(str)
    cancel_clicked = Signal(str)
    retry_clicked = Signal(str)
    open_folder_clicked = Signal(str)
    open_file_clicked = Signal(str)
    delete_clicked = Signal(str)
    config_clicked = Signal()
    check_disk_clicked = Signal(str)

    def __init__(self, task_data: dict, parent=None):
        super().__init__(parent)
        self.task_id = task_data.get("id", "")
        self.task_data = task_data
        self.setObjectName("taskCard")
        self.setFixedHeight(118)
        self._current_status = None
        self.setStyleSheet("""
            QFrame#taskCard {
                background-color: #111216;
                border: 1px solid #27272a;
                border-left: 4px solid #38bdf8;
                border-radius: 10px;
                padding: 0px;
            }
            QFrame#taskCard:hover {
                border-color: #3f3f46;
                border-left-color: #38bdf8;
                background-color: #14151b;
            }
            QFrame#taskCard QLabel {
                background: transparent;
                background-color: transparent;
            }
            QLabel#taskTitle {
                color: #f4f4f5;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-weight: 700;
                font-size: 13px;
            }
            QLabel#taskStats {
                color: #a1a1aa;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
            }
            QLabel#taskEta {
                color: #38bdf8;
                font-family: 'JetBrains Mono', monospace;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#badgeStatus {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 2px 8px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
                font-weight: 700;
            }
            QPushButton.cardActionBtn {
                background-color: #16171d;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 0 12px;
                color: #f4f4f5;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton.cardActionBtn:hover {
                background-color: #1c1d24;
                border-color: #38bdf8;
                color: #38bdf8;
            }
            QPushButton.cardCancelBtn {
                background-color: rgba(244, 63, 94, 0.12);
                border: 1px solid rgba(244, 63, 94, 0.35);
                border-radius: 6px;
                padding: 0 14px;
                color: #f43f5e;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton.cardCancelBtn:hover {
                background-color: #f43f5e;
                color: #ffffff;
            }
            QPushButton.cardPauseBtn {
                background-color: rgba(251, 191, 36, 0.12);
                border: 1px solid rgba(251, 191, 36, 0.35);
                border-radius: 6px;
                padding: 0 12px;
                color: #fbbf24;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton.cardPauseBtn:hover {
                background-color: #fbbf24;
                color: #09090b;
            }
            QPushButton.cardResumeBtn {
                background-color: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 6px;
                padding: 0 12px;
                color: #38bdf8;
                font-family: 'JetBrains Mono', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton.cardResumeBtn:hover {
                background-color: #38bdf8;
                color: #09090b;
            }
        """)

        self._init_ui()
        self.update_data(task_data)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(8)

        # Top row: Title + Status Badge
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)
        self.lbl_title = ElidedLabel(self.task_data.get("title", t("task_default_title")), self)
        self.lbl_title.setObjectName("taskTitle")
        top_row.addWidget(self.lbl_title, 1, Qt.AlignVCenter)

        self.lbl_badge = QLabel(self)
        self.lbl_badge.setObjectName("badgeStatus")
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.setFixedHeight(24)
        self.lbl_badge.setMinimumWidth(185)
        top_row.addWidget(self.lbl_badge, 0, Qt.AlignVCenter)

        main_layout.addLayout(top_row)

        # Progress Bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Bottom Row: Stats (Left) + Buttons (Right)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(12)

        self.lbl_stats = ElidedLabel("", self)
        self.lbl_stats.setObjectName("taskStats")
        self.lbl_stats.setMinimumWidth(120)
        bottom_row.addWidget(self.lbl_stats, 1, Qt.AlignVCenter)

        self.lbl_eta = QLabel(self)
        self.lbl_eta.setObjectName("taskEta")
        self.lbl_eta.setMinimumWidth(60)
        bottom_row.addWidget(self.lbl_eta, 0, Qt.AlignVCenter)

        bottom_row.addStretch()

        # Action Buttons Container
        self.actions_layout = QHBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(8)
        bottom_row.addLayout(self.actions_layout)

        main_layout.addLayout(bottom_row)

    def _set_progress_bar_color(self, color_hex: str):
        if getattr(self, "_last_pb_color", None) == color_hex:
            return
        self._last_pb_color = color_hex
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #16171d;
                border: none;
                border-radius: 3px;
                height: 6px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {color_hex};
                border-radius: 3px;
            }}
        """)

    def _set_card_border(self, color_hex: str):
        if getattr(self, "_last_border_color", None) == color_hex:
            return
        self._last_border_color = color_hex
        self.setStyleSheet(f"""
            QFrame#taskCard {{
                background-color: #111216;
                border: 1px solid #27272a;
                border-left: 4px solid {color_hex};
                border-radius: 10px;
                padding: 0px;
            }}
            QFrame#taskCard:hover {{
                border-color: #3f3f46;
                border-left-color: {color_hex};
                background-color: #14151b;
            }}
            QFrame#taskCard QLabel {{
                background: transparent;
                background-color: transparent;
            }}
        """)

    def update_data(self, data: dict):
        self.task_data = data
        if "title" in data and data["title"]:
            self.lbl_title.set_full_text(data["title"])
        status = data.get("status", "starting")
        progress = float(data.get("progress", 0))
        speed = data.get("speed", "--")
        eta = data.get("eta", "--")
        downloaded = data.get("downloaded", "0 MB")
        total = data.get("total", "--")
        stage = data.get("stage", "")

        self.progress_bar.setValue(int(progress))

        # Check if active task is in video transcoding phase
        is_transcoding = (stage == "transcode_prores") or ("transcode" in eta.lower()) or ("prores" in eta.lower())

        # Developer status badges & live telemetry
        if status == "downloading":
            self.lbl_badge.setText(f"[STATUS:{t('status_downloading')} {progress:.1f}%]")
            self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #38bdf8; color: #38bdf8; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            self.lbl_stats.setText(f"[{downloaded} / {total}]  |  {speed}")
            self.lbl_stats.setToolTip("")
            self.lbl_eta.setText(f"ETA: {eta}")
            self._set_progress_bar_color("#38bdf8")
            self._set_card_border("#38bdf8")
        elif status == "muxing":
            if is_transcoding:
                self.lbl_badge.setText(f"[STATUS:{t('status_transcoding')} {progress:.1f}%]")
                self.lbl_badge.setStyleSheet("background-color: #1c1917; border: 1px solid #f59e0b; color: #fbbf24; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
                self._set_progress_bar_color("#f59e0b")
                self._set_card_border("#f59e0b")

                cur_t = data.get("transcode_current")
                tot_t = data.get("transcode_total")
                t_eta = data.get("transcode_eta")
                if cur_t and tot_t:
                    self.lbl_stats.setText(f"Transcoding ProRes 422: {progress:.1f}% [{cur_t} / {tot_t}]  |  {speed}")
                elif "transcode" in eta.lower():
                    self.lbl_stats.setText(eta)
                else:
                    self.lbl_stats.setText(f"Transcoding ProRes 422: {progress:.1f}%  |  {speed}")

                if t_eta and t_eta != "--":
                    self.lbl_eta.setText(f"ETA: {t_eta}")
                elif speed and speed != "--":
                    self.lbl_eta.setText(f"Speed: {speed}")
                else:
                    self.lbl_eta.setText("")

                self.lbl_stats.setToolTip(
                    f"Tahap: Transcoding Apple ProRes 422\n"
                    f"Progress: {progress:.1f}%\n"
                    f"Durasi Diproses: {cur_t or '--'} / {tot_t or '--'}\n"
                    f"Kecepatan Render: {speed}\n"
                    f"Estimasi Sisa Waktu (ETA): {t_eta or '--'}"
                )
            else:
                if progress > 0 and progress < 100:
                    self.lbl_badge.setText(f"[STATUS:{t('status_muxing')} {progress:.1f}%]")
                else:
                    self.lbl_badge.setText(f"[STATUS:{t('status_muxing')}]")
                self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #fbbf24; color: #fbbf24; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
                self._set_progress_bar_color("#fbbf24")
                self._set_card_border("#fbbf24")
                self.lbl_stats.setText(eta or t("task_muxing_desc"))
                self.lbl_stats.setToolTip("")
                self.lbl_eta.setText("")
        elif status == "paused":
            if data.get("disk_low"):
                self.lbl_badge.setText(f"[STATUS:{t('status_low_disk')}]")
                self.lbl_badge.setStyleSheet(
                    "background-color: rgba(244, 63, 94, 0.15); "
                    "border: 1px solid #f43f5e; "
                    "color: #fb7185; "
                    "border-radius: 4px; "
                    "padding: 2px 8px; "
                    "font-weight: 700; "
                    "font-size: 10px; "
                    "font-family: 'JetBrains Mono', monospace;"
                )
                disk_f = data.get("disk_free", "--")
                disk_n = data.get("disk_needed", "--")
                dr = data.get("disk_drive", "Disk")
                dr_label = dr.rstrip(":")
                self.lbl_stats.setText(f"[{dr_label}: Sisa {disk_f} / Butuh {disk_n}]")
                self.lbl_stats.setToolTip(
                    f"Peringatan Ruang Penyimpanan:\n"
                    f"Lokasi: {dr}\n"
                    f"Ruang Kosong: {disk_f}\n"
                    f"Dibutuhkan: {disk_n}\n\n"
                    f"Status: Konversi dijeda otomatis untuk mencegah file korup.\n"
                    f"Sistem memantau secara real-time dan akan melanjutkan otomatis setelah ruang disk kosong,\n"
                    f"atau tekan tombol [CEK DISK] untuk memeriksa ulang secara manual."
                )
                self.lbl_eta.setText(t("task_low_disk_desc"))
                self._set_progress_bar_color("#f43f5e")
                self._set_card_border("#f43f5e")
            else:
                self.lbl_badge.setText(f"[STATUS:{t('status_paused')} {progress:.1f}%]")
                self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #fbbf24; color: #fbbf24; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
                self.lbl_stats.setText(f"[{downloaded} / {total}]  |  Paused")
                self.lbl_stats.setToolTip("")
                self.lbl_eta.setText(t("task_paused_desc"))
                self._set_progress_bar_color("#fbbf24")
                self._set_card_border("#fbbf24")
        elif status == "completed":
            self.lbl_badge.setText(f"[STATUS:{t('status_completed')}]")
            self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #34d399; color: #34d399; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            self.lbl_stats.setText(f"[{total or downloaded}]  |  {t('task_ready_edit')}")
            self.lbl_stats.setToolTip("")
            self.lbl_eta.setText("")
            self._set_progress_bar_color("#34d399")
            self._set_card_border("#34d399")
        elif status == "error":
            err_msg = data.get("error", t("task_err_default"))
            self.lbl_badge.setText(f"[STATUS:{t('status_error')}]")
            self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #f43f5e; color: #f43f5e; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            if "DISK_FULL" in err_msg:
                short_msg = err_msg.replace("DISK_FULL: ", "")
                self.lbl_stats.setText(f"ERR: {short_msg[:95]}")
                self.lbl_stats.setToolTip(f"{err_msg}\n\nTip: Buka menu [CONFIG] Settings untuk memilih folder unduhan pada drive lain yang masih memiliki ruang.")
            elif "BOT_CHECK_REQUIRED" in err_msg:
                self.lbl_stats.setText("ERR: BOT_CHECK_REQUIRED (Perlu Login / Pasang Cookies)")
                self.lbl_stats.setToolTip(f"{err_msg}\n\nTip: Buka menu CONFIG untuk memasang cookies.txt dari browser.")
            else:
                self.lbl_stats.setText(f"ERR: {err_msg[:95]}")
                self.lbl_stats.setToolTip(f"{err_msg}\n\nTip: Buka menu CONFIG untuk pengaturan cookies atau koneksi.")
            self.lbl_eta.setText("")
            self._set_progress_bar_color("#f43f5e")
            self._set_card_border("#f43f5e")
        elif status == "cancelled":
            self.lbl_badge.setText(f"[STATUS:{t('status_cancelled')}]")
            self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #52525b; color: #71717a; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            self.lbl_stats.setText(t("task_aborted_user"))
            self.lbl_stats.setToolTip("")
            self.lbl_eta.setText("")
            self._set_progress_bar_color("#52525b")
            self._set_card_border("#52525b")
        else:
            self.lbl_badge.setText(f"[STATUS:{t('status_connecting')}]")
            self.lbl_badge.setStyleSheet("background-color: #16171d; border: 1px solid #818cf8; color: #818cf8; border-radius: 4px; padding: 2px 8px; font-weight: 700; font-size: 10px; font-family: 'JetBrains Mono', monospace;")
            self.lbl_stats.setText(eta or t("task_connecting"))
            self.lbl_stats.setToolTip("")
            self.lbl_eta.setText("")
            self._set_progress_bar_color("#818cf8")
            self._set_card_border("#818cf8")

        is_low_disk = bool(data.get("disk_low"))
        if status != self._current_status or is_low_disk != getattr(self, "_last_is_low_disk", None):
            self._refresh_buttons(status, data)
            self._current_status = status
            self._last_is_low_disk = is_low_disk

    def _refresh_buttons(self, status: str, data: dict):
        while self.actions_layout.count():
            item = self.actions_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        file_dest = data.get("destination") or data.get("filepath") or ""

        if status in ("starting", "downloading"):
            btn_pause = QPushButton(t("task_btn_pause"), self)
            btn_pause.setProperty("class", "cardPauseBtn")
            btn_pause.setFixedHeight(26)
            btn_pause.clicked.connect(lambda: self.pause_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_pause)

            btn_cancel = QPushButton(t("task_btn_abort"), self)
            btn_cancel.setProperty("class", "cardCancelBtn")
            btn_cancel.setFixedHeight(26)
            btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_cancel)
        elif status == "paused":
            if data.get("disk_low"):
                btn_check = QPushButton(t("task_btn_check_disk"), self)
                btn_check.setProperty("class", "cardResumeBtn")
                btn_check.setFixedHeight(26)
                btn_check.setToolTip("Periksa ketersediaan ruang disk dan lanjutkan konversi jika sudah cukup")
                btn_check.clicked.connect(lambda: self.check_disk_clicked.emit(self.task_id))
                self.actions_layout.addWidget(btn_check)

                btn_cfg = QPushButton(t("task_btn_storage"), self)
                btn_cfg.setProperty("class", "cardActionBtn")
                btn_cfg.setFixedHeight(26)
                btn_cfg.clicked.connect(self.config_clicked.emit)
                self.actions_layout.addWidget(btn_cfg)

                btn_cancel = QPushButton(t("task_btn_abort"), self)
                btn_cancel.setProperty("class", "cardCancelBtn")
                btn_cancel.setFixedHeight(26)
                btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
                self.actions_layout.addWidget(btn_cancel)
            else:
                btn_resume = QPushButton(t("task_btn_resume"), self)
                btn_resume.setProperty("class", "cardResumeBtn")
                btn_resume.setFixedHeight(26)
                btn_resume.clicked.connect(lambda: self.resume_clicked.emit(self.task_id))
                self.actions_layout.addWidget(btn_resume)

                btn_cancel = QPushButton(t("task_btn_abort"), self)
                btn_cancel.setProperty("class", "cardCancelBtn")
                btn_cancel.setFixedHeight(26)
                btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
                self.actions_layout.addWidget(btn_cancel)
        elif status == "muxing":
            btn_pause = QPushButton(t("task_btn_pause"), self)
            btn_pause.setProperty("class", "cardPauseBtn")
            btn_pause.setFixedHeight(26)
            btn_pause.clicked.connect(lambda: self.pause_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_pause)

            btn_cancel = QPushButton(t("task_btn_abort"), self)
            btn_cancel.setProperty("class", "cardCancelBtn")
            btn_cancel.setFixedHeight(26)
            btn_cancel.clicked.connect(lambda: self.cancel_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_cancel)
        elif status == "completed":
            if file_dest and os.path.exists(file_dest):
                btn_open_file = QPushButton(t("task_btn_play"), self)
                btn_open_file.setProperty("class", "cardActionBtn")
                btn_open_file.setFixedHeight(26)
                btn_open_file.clicked.connect(lambda: self._open_file(file_dest))
                self.actions_layout.addWidget(btn_open_file)

                btn_folder = QPushButton(t("task_btn_dir"), self)
                btn_folder.setProperty("class", "cardActionBtn")
                btn_folder.setFixedHeight(26)
                btn_folder.clicked.connect(lambda: self._open_folder(file_dest))
                self.actions_layout.addWidget(btn_folder)

            btn_del = QPushButton(t("task_btn_del"), self)
            btn_del.setProperty("class", "cardActionBtn")
            btn_del.setFixedHeight(26)
            btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_del)
        elif status in ("error", "cancelled"):
            err_str = str(data.get("error", "")).lower()
            if "bot_check" in err_str or "cookie" in err_str or "disk_full" in err_str:
                label_txt = t("task_btn_storage") if "disk_full" in err_str else t("task_btn_config")
                btn_cfg = QPushButton(label_txt, self)
                btn_cfg.setProperty("class", "cardActionBtn")
                btn_cfg.setStyleSheet("color: #fbbf24; border-color: rgba(251, 191, 36, 0.4);")
                btn_cfg.setFixedHeight(26)
                if "disk_full" in err_str:
                    btn_cfg.setToolTip("Buka menu Pengaturan untuk memilih folder unduhan pada drive lain")
                else:
                    btn_cfg.setToolTip("Buka menu Pengaturan untuk memasang file cookies.txt terbaru")
                btn_cfg.clicked.connect(self.config_clicked.emit)
                self.actions_layout.addWidget(btn_cfg)

            btn_retry = QPushButton(t("task_btn_retry"), self)
            btn_retry.setProperty("class", "cardActionBtn")
            btn_retry.setFixedHeight(26)
            btn_retry.clicked.connect(lambda: self.retry_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_retry)

            btn_del = QPushButton(t("task_btn_del"), self)
            btn_del.setProperty("class", "cardActionBtn")
            btn_del.setFixedHeight(26)
            btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.task_id))
            self.actions_layout.addWidget(btn_del)

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
