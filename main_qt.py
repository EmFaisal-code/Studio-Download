import os
import sys
from pathlib import Path

# Ensure stdout and stderr are not None in Windows GUI (--noconsole) mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Enable High-DPI scaling and crisp fonts
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# Windows DPI Awareness & Taskbar AppUserModelID
if sys.platform == "win32":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        myappid = "emfaisal.studiodownload.native.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure tool paths (ffmpeg.exe, etc.) are available on PATH
from backend.config import get_app_dir, get_bundle_dir
app_dir = get_app_dir()
os.environ["PATH"] = str(app_dir) + os.pathsep + os.environ.get("PATH", "")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from ui.styles import MAIN_QSS
from ui.main_window import MainWindow


def get_application_icon_path() -> str | None:
    for candidate in [
        get_bundle_dir() / "app_icon.ico",
        get_app_dir() / "app_icon.ico",
        BASE_DIR / "app_icon.ico",
        BASE_DIR / "app_icon.png"
    ]:
        if candidate.exists():
            return str(candidate)
    return None

def get_application_icon() -> QIcon | None:
    path = get_application_icon_path()
    if path:
        return QIcon(path)
    return None

def set_window_icon_win32(hwnd: int, icon_path: str):
    if not icon_path or sys.platform != "win32":
        return
    try:
        import ctypes
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        user32 = ctypes.windll.user32
        h_icon_big = user32.LoadImageW(0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_icon_small = user32.LoadImageW(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
        if h_icon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
        if h_icon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
    except Exception:
        pass


import socket
import threading

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8080) -> int:
    port = start_port
    while is_port_in_use(port) and port < 8090:
        port += 1
    return port

def start_background_server():
    port = find_available_port(8080)
    def _worker():
        try:
            import uvicorn
            from backend.app import app
            config = uvicorn.Config(
                app,
                host="127.0.0.1",
                port=port,
                log_config=None,
                access_log=False,
                loop="asyncio",
                http="h11",
                ws="websockets"
            )
            server = uvicorn.Server(config)
            server.run()
        except Exception as e:
            pass
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def main():
    # Start background API server for browser companion extension IPC
    start_background_server()

    # Configure High-DPI rounding policy
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Studio Download")
    app.setApplicationDisplayName("Studio Download")
    app.setOrganizationName("EmFaisal")

    icon = get_application_icon()
    icon_path = get_application_icon_path()
    if icon:
        app.setWindowIcon(icon)

    # Apply global modern cyberpunk / dark glassmorphism stylesheet
    app.setStyleSheet(MAIN_QSS)

    # Instantiate and display main window with solid icon binding
    window = MainWindow(app_icon=icon, icon_path=icon_path)
    if icon:
        window.setWindowIcon(icon)
    window.show()

    # Ensure native Win32 window HWND has the icon attached for taskbar and Alt+Tab
    if icon_path and sys.platform == "win32":
        set_window_icon_win32(int(window.winId()), icon_path)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
