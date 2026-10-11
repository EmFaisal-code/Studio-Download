from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from backend.i18n import t

class FormatCardWidget(QFrame):
    card_selected = Signal(dict)

    def __init__(self, format_data: dict, index: int, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.format_data = format_data
        self.index = index
        self.is_selected = is_selected
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(84)
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setObjectName("formatCard")
        self._init_ui()
        self.set_selected(is_selected)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header: Index + Label
        header = QHBoxLayout()
        idx_lbl = QLabel(f"#{self.index:02d}", self)
        idx_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        idx_lbl.setStyleSheet("color: #818cf8; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700; background: transparent;")
        header.addWidget(idx_lbl)

        label_raw = self.format_data.get("label") or self.format_data.get("resolution") or self.format_data.get("name") or "Standard"
        clean_label = label_raw.replace(" / Source (File Size Asli)", " (Source)").replace(" (File Size Asli)", "")
        self.lbl_title = QLabel(clean_label, self)
        self.lbl_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_title.setStyleSheet("color: #f4f4f5; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 12px; background: transparent;")
        header.addWidget(self.lbl_title, 1)

        layout.addLayout(header)

        # Body: FPS & Codec
        body = QHBoxLayout()
        fps = self.format_data.get("fps")
        fps_str = f"{fps} FPS" if fps else "Audio"
        self.lbl_fps = QLabel(fps_str, self)
        self.lbl_fps.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_fps.setStyleSheet("color: #a1a1aa; font-family: 'JetBrains Mono', monospace; font-size: 10px; background: transparent;")
        body.addWidget(self.lbl_fps)

        codec = self.format_data.get("vcodec") or self.format_data.get("codec") or self.format_data.get("format", "H.264")
        self.lbl_codec = QLabel(f"[{codec}]", self)
        self.lbl_codec.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_codec.setStyleSheet("color: #34d399; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; background: transparent;")
        body.addWidget(self.lbl_codec)
        body.addStretch()

        layout.addLayout(body)
        layout.addStretch()

        # Footer: Filesize (Amber Monospace) + Selection Tag
        footer = QHBoxLayout()
        size_str = self.format_data.get("filesize_formatted", "--")
        self.lbl_size = QLabel(f"~ {size_str}", self)
        self.lbl_size.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_size.setStyleSheet("color: #fbbf24; font-family: 'JetBrains Mono', monospace; font-weight: 700; font-size: 12px; background: transparent;")
        size_tooltip = t("card_size_tooltip").format(size=size_str)
        self.lbl_size.setToolTip(size_tooltip)
        self.setToolTip(f"{clean_label} | {fps_str} | [{codec}]\n{size_tooltip}")
        footer.addWidget(self.lbl_size)

        footer.addStretch()

        self.lbl_tag = QLabel(t("card_select"), self)
        self.lbl_tag.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.lbl_tag.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; background: transparent;")
        footer.addWidget(self.lbl_tag)

        layout.addLayout(footer)

    def update_format_data(self, format_data: dict):
        self.format_data = format_data
        codec = self.format_data.get("vcodec") or self.format_data.get("codec") or self.format_data.get("format", "H.264")
        self.lbl_codec.setText(f"[{codec}]")
        size_str = self.format_data.get("filesize_formatted", "--")
        self.lbl_size.setText(f"~ {size_str}")
        size_tooltip = t("card_size_tooltip").format(size=size_str)
        self.lbl_size.setToolTip(size_tooltip)
        fps = self.format_data.get("fps")
        fps_str = f"{fps} FPS" if fps else "Audio"
        self.lbl_fps.setText(fps_str)
        label_raw = self.format_data.get("label") or self.format_data.get("resolution") or self.format_data.get("name") or "Standard"
        clean_label = label_raw.replace(" / Source (File Size Asli)", " (Source)").replace(" (File Size Asli)", "")
        self.lbl_title.setText(clean_label)
        self.setToolTip(f"{clean_label} | {fps_str} | [{codec}]\n{size_tooltip}")

    def set_selected(self, selected: bool):
        self.is_selected = selected
        if selected:
            self.setStyleSheet("""
                QFrame#formatCard {
                    background-color: #141724;
                    border: 2px solid #38bdf8;
                    border-radius: 8px;
                }
            """)
            self.lbl_tag.setText(t("card_selected"))
            self.lbl_tag.setStyleSheet("color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; font-weight: 700;")
        else:
            self.setStyleSheet("""
                QFrame#formatCard {
                    background-color: #111216;
                    border: 1px solid #27272a;
                    border-radius: 8px;
                }
                QFrame#formatCard:hover {
                    background-color: #16171d;
                    border-color: #38bdf8;
                }
            """)
            self.lbl_tag.setText(t("card_select"))
            self.lbl_tag.setStyleSheet("color: #71717a; font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 600; background: transparent;")


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_selected.emit(self.format_data)
        super().mousePressEvent(event)
