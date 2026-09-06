import os
import sys

# Ensure stdout and stderr are not None in Windows GUI (--noconsole) mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import time
import socket
import threading
import webbrowser
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import uvicorn
from backend.config import get_settings, get_app_dir, get_bundle_dir

def get_icon_path() -> str | None:
    for candidate in [
        get_bundle_dir() / "app_icon.ico",
        get_app_dir() / "app_icon.ico",
        BASE_DIR / "app_icon.ico"
    ]:
        if candidate.exists():
            return str(candidate)
    return None

def set_app_icon_win32(icon_path: str):
    if not icon_path or sys.platform != "win32":
        return
    import ctypes
    def _worker():
        for _ in range(25):
            time.sleep(0.3)
            WM_SETICON = 0x0080
            ICON_SMALL = 0
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x0010
            user32 = ctypes.windll.user32
            found = False

            def enum_windows_callback(hwnd, extra):
                nonlocal found
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    if "Studio Download" in buff.value:
                        h_icon_big = user32.LoadImageW(0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                        h_icon_small = user32.LoadImageW(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
                        if h_icon_small:
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
                        if h_icon_big:
                            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                        found = True
                return True

            try:
                WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
            except Exception:
                pass
            if found:
                break

    threading.Thread(target=_worker, daemon=True).start()

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(start_port: int = 8080) -> int:
    port = start_port
    while is_port_in_use(port):
        port += 1
    return port

def run_server(port: int):
    try:
        # Import app inside thread to ensure clean startup
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
        import traceback
        try:
            err_log = get_app_dir() / "server_error.log"
            with open(err_log, "w", encoding="utf-8") as f:
                traceback.print_exc(file=f)
        except Exception:
            pass

def main():
    app_dir = get_app_dir()
    os.environ["PATH"] = str(app_dir) + os.pathsep + os.environ.get("PATH", "")

    settings = get_settings()
    configured_port = settings.get("port", 8080)
    port = find_available_port(configured_port)
    url = f"http://127.0.0.1:{port}"

    print("=" * 60)
    print("   STUDIO DOWNLOAD - Pro YouTube Media Engine")
    print("=" * 60)
    print(f"[*] Menjalankan backend server di {url}...")

    # Start FastAPI server in a background thread
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to become responsive
    attempts = 0
    while not is_port_in_use(port) and attempts < 50:
        time.sleep(0.2)
        attempts += 1

    if not is_port_in_use(port):
        err_log = app_dir / "server_error.log"
        err_msg = "Server backend gagal merespons pada port " + str(port)
        if err_log.exists():
            err_msg += "\n\n" + err_log.read_text(encoding="utf-8", errors="ignore")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Gagal menjalankan Studio Download:\n{err_msg}", "Studio Download Error", 0x10)
        except Exception:
            pass
        sys.exit(1)

    print(f"[+] Server aktif di {url}")

    use_browser = "--browser" in sys.argv

    if not use_browser:
        try:
            import webview
            print("[*] Membuka antarmuka desktop native (PyWebView)...")
            icon_path = get_icon_path()
            if icon_path:
                set_app_icon_win32(icon_path)
            window = webview.create_window(
                title="Studio Download - Pro YouTube Media Engine",
                url=url,
                width=1120,
                height=820,
                min_size=(920, 680),
                background_color="#09090b"
            )
            webview.start(icon=icon_path)
            print("[*] Aplikasi desktop ditutup oleh pengguna.")
            sys.exit(0)
        except Exception as e:
            print(f"[!] Tidak dapat membuka jendela native ({e}), beralih ke browser default...")

    # Fallback to browser
    print(f"[*] Membuka browser: {url}")
    webbrowser.open(url)

    print("\nTekan Ctrl+C di terminal ini untuk mematikan aplikasi Studio Download.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Mematikan Studio Download. Sampai jumpa!")

if __name__ == "__main__":
    main()
