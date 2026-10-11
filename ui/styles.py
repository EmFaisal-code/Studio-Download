import os
from pathlib import Path

_UI_DIR = Path(__file__).resolve().parent
_ARROW_ICON_PATH = (_UI_DIR / "arrow_down.png").as_posix()

def _ensure_arrow_icon():
    if not os.path.exists(_ARROW_ICON_PATH):
        try:
            from PySide6.QtGui import QImage, QPainter, QColor, QPolygonF
            from PySide6.QtCore import QPointF
            img = QImage(16, 16, QImage.Format_ARGB32)
            img.fill(0)
            p = QPainter(img)
            p.setRenderHint(QPainter.Antialiasing)
            p.setBrush(QColor('#a1a1aa'))
            p.setPen(QColor(0, 0, 0, 0))
            p.drawPolygon(QPolygonF([QPointF(3.5, 6.0), QPointF(12.5, 6.0), QPointF(8.0, 10.5)]))
            p.end()
            img.save(_ARROW_ICON_PATH)
        except Exception:
            pass

_ensure_arrow_icon()

# Studio Download - Developer / IDE Editorial Console & Studio Themes
# Aesthetics: Vercel, Linear & Developer Console inspired craft
# Typography: JetBrains Mono / Cascadia Code / Consolas / Segoe UI

ZINC_TOKENS = {
    "bg_base": "#09090b",
    "bg_surface": "#111216",
    "bg_surface_elevated": "#16171d",
    "bg_surface_hover": "#1c1d24",
    "border_subtle": "#27272a",
    "border_medium": "#3f3f46",
    "border_strong": "#52525b",
    "text_primary": "#f4f4f5",
    "text_secondary": "#a1a1aa",
    "text_muted": "#71717a",
    "text_faint": "#52525b",
    # Syntax & developer accents
    "syntax_keyword": "#818cf8",  # Indigo / Purple
    "syntax_func": "#38bdf8",     # Cyan / Sky
    "syntax_string": "#34d399",   # Emerald
    "syntax_num": "#fbbf24",      # Amber / Orange
    "syntax_comment": "#71717a",  # Muted Zinc
    "accent_contrast": "#ffffff",
    "accent_danger": "#f43f5e"
}

YELLOW_TOKENS = {
    "bg_base": "#0f0f12",
    "bg_surface": "#16161c",
    "bg_surface_elevated": "#1e1e26",
    "bg_surface_hover": "#262632",
    "border_subtle": "#2a2a36",
    "border_medium": "#3e3e50",
    "border_strong": "#52526a",
    "text_primary": "#ffffff",
    "text_secondary": "#cbd5e1",
    "text_muted": "#94a3b8",
    "text_faint": "#64748b",
    "syntax_keyword": "#f59e0b",
    "syntax_func": "#fbbf24",
    "syntax_string": "#34d399",
    "syntax_num": "#f59e0b",
    "syntax_comment": "#94a3b8",
    "accent_contrast": "#f59e0b",
    "accent_danger": "#e11d48"
}

DEVELOPER_ZINC_QSS = """
/* ==========================================================================
   DEVELOPER ZINC (IDE CONSOLE CRAFT) - PROPORTIONAL & RESPONSIVE
   ========================================================================== */

QWidget {
    background-color: transparent;
    color: #f4f4f5;
    font-family: 'JetBrains Mono', 'Cascadia Code', 'Consolas', 'Segoe UI', monospace;
    font-size: 13px;
}

QLabel {
    background: transparent;
    background-color: transparent;
}

QMainWindow, QDialog {
    background-color: #09090b;
}

/* Custom Sleek Scrollbar */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #09090b;
    width: 6px;
    margin: 0px;
    border-radius: 3px;
}

QScrollBar::handle:vertical {
    background: #27272a;
    min-height: 24px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #38bdf8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    height: 0px;
    border: none;
    background: transparent;
}

/* Tooltips */
QToolTip {
    background-color: #16171d;
    color: #f4f4f5;
    border: 1px solid #3f3f46;
    padding: 4px 10px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
}

/* Terminal & Code Text Inputs */
QLineEdit {
    background-color: #111216;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f4f4f5;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: #38bdf8;
    selection-color: #09090b;
}

QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #14151b;
}

/* Developer Console Standard Buttons */
QPushButton {
    background-color: #16171d;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 7px 16px;
    color: #f4f4f5;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #1e2029;
    border-color: #3f3f46;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #111216;
}

QPushButton:disabled {
    background-color: #111216;
    border-color: #1c1d24;
    color: #52525b;
}

/* Ghost / Nav Buttons - Clean, borderless when idle */
QPushButton.ghostBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 5px 12px;
    color: #a1a1aa;
    font-family: 'JetBrains Mono', 'Segoe UI', monospace;
    font-weight: 500;
    font-size: 11px;
}

QPushButton.ghostBtn:hover {
    background-color: #1c1d24;
    color: #f4f4f5;
}

QPushButton.ghostBtn:pressed {
    background-color: #14151a;
}

/* High-Contrast Primary Command Button (Sky Cyan Accent) */
QPushButton#btnPrimary {
    background-color: #38bdf8;
    color: #09090b;
    border: none;
    border-radius: 8px;
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.2px;
    padding: 8px 18px;
}

QPushButton#btnPrimary:hover {
    background-color: #7dd3fc;
    color: #09090b;
}

QPushButton#btnPrimary:pressed {
    background-color: #0284c7;
    color: #ffffff;
}

QPushButton#btnPrimary:disabled {
    background-color: #27272a;
    color: #71717a;
}

/* ComboBox in Clean Standard Style */
QComboBox {
    background-color: #16171d;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 4px 10px;
    padding-right: 28px;
    color: #f4f4f5;
    font-family: 'JetBrains Mono', 'Consolas', monospace;
    font-size: 11px;
    min-width: 90px;
    height: 22px;
}

QComboBox:hover {
    border-color: #3f3f46;
    background-color: #1a1b24;
}

QComboBox:focus {
    border-color: #38bdf8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 22px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__ARROW_ICON__");
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #111216;
    border: 1px solid #3f3f46;
    selection-background-color: #16171d;
    selection-color: #38bdf8;
    color: #f4f4f5;
    outline: none;
    padding: 4px;
    font-size: 11px;
    border-radius: 6px;
}

/* Smooth Progress Bar */
QProgressBar {
    background-color: #16171d;
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #38bdf8;
    border-radius: 3px;
}

/* SpinBox */
QSpinBox {
    background-color: #111216;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 6px 10px;
    color: #ffffff;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
}

QSpinBox:focus {
    border-color: #38bdf8;
}

"""

MODERN_YELLOW_QSS = """
/* ==========================================================================
   STUDIO YELLOW / AMBER THEME - PROPORTIONAL & RESPONSIVE
   ========================================================================== */

QWidget {
    background-color: transparent;
    color: #ffffff;
    font-family: 'Outfit', 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
    font-size: 14px;
}

QLabel {
    background: transparent;
    background-color: transparent;
}

QMainWindow, QDialog {
    background-color: #0f0f12;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #0f0f12;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #2a2a36;
    min-height: 28px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #f59e0b;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QLineEdit {
    background-color: #16161c;
    border: 1px solid #2a2a36;
    border-radius: 8px;
    padding: 10px 14px;
    color: #ffffff;
    font-size: 14px;
    selection-background-color: #f59e0b;
    selection-color: #09090b;
}

QLineEdit:focus {
    border: 1px solid #f59e0b;
    background-color: #1e1e26;
}

QPushButton {
    background-color: #16161c;
    border: 1px solid #2a2a36;
    border-radius: 8px;
    padding: 9px 18px;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #262632;
    border-color: #3e3e50;
    color: #ffffff;
}

QPushButton#btnPrimary {
    background-color: #f59e0b;
    color: #09090b;
    border: none;
    font-weight: 700;
    font-size: 13px;
    padding: 10px 22px;
}

QPushButton#btnPrimary:hover {
    background-color: #d97706;
    color: #ffffff;
}

QProgressBar {
    background-color: #1e1e26;
    border: 1px solid #2a2a36;
    border-radius: 5px;
    height: 9px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #f59e0b;
    border-radius: 4px;
}

/* ComboBox in Amber Modern Style */
QComboBox {
    background-color: #16161c;
    border: 1px solid #2a2a36;
    border-radius: 6px;
    padding: 6px 12px;
    padding-right: 28px;
    color: #ffffff;
    font-family: 'Outfit', 'Plus Jakarta Sans', 'Segoe UI', sans-serif;
    font-size: 12px;
    min-width: 90px;
}

QComboBox:hover {
    border-color: #3e3e50;
    background-color: #1e1e26;
}

QComboBox:focus {
    border-color: #f59e0b;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 22px;
    border: none;
    background: transparent;
}

QComboBox::down-arrow {
    image: url("__ARROW_ICON__");
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #16161c;
    border: 1px solid #3e3e50;
    selection-background-color: #1e1e26;
    selection-color: #f59e0b;
    color: #ffffff;
    outline: none;
    padding: 4px;
    font-size: 12px;
    border-radius: 6px;
}
"""

def get_theme_qss(theme_name: str = "developer-zinc") -> str:
    _ensure_arrow_icon()
    raw = MODERN_YELLOW_QSS if theme_name in ("modern-yellow", "cyber-yellow") else DEVELOPER_ZINC_QSS
    return raw.replace("__ARROW_ICON__", _ARROW_ICON_PATH)

MAIN_QSS = get_theme_qss("developer-zinc")
