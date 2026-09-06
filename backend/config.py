import os
import sys
import json
from pathlib import Path

def get_app_dir() -> Path:
    """Returns directory where persistent user data (settings, history, cookies) is stored."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

def get_bundle_dir() -> Path:
    """Returns directory containing packaged read-only assets (frontend HTML, icons, templates)."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_app_dir()
SETTINGS_FILE = BASE_DIR / "settings.json"
USERS_FILE = BASE_DIR / "users.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "StudioDownload"
DEFAULT_COOKIE_FILE = BASE_DIR / "cookies.txt"

DEFAULT_SETTINGS = {
    "download_dir": str(DEFAULT_DOWNLOAD_DIR),
    "default_resolution": "best",
    "default_format": "mkv",
    "download_subtitles": False,
    "embed_thumbnail": True,
    "port": 8080,
    "cookie_source": "auto",       # "auto", "file", "browser", "none"
    "cookie_browser": "chrome",     # "chrome", "edge", "firefox", "brave"
    "cookie_file": str(DEFAULT_COOKIE_FILE) if DEFAULT_COOKIE_FILE.exists() else "",
    "theme": "modern-yellow",       # "modern-yellow", "developer-zinc"
    "language": "id",               # "id" (Bahasa Indonesia), "en" (English)
    "max_concurrent_downloads": 2,  # 0 = unlimited, 1, 2, 3, 5
    "download_speed_limit": 0,      # 0 = unlimited, in KB/s (e.g. 1024, 2048, 5120)
    "user_profile": None            # None or dict: { user_id, username, role, contact, registered_at }
}

def get_users_registry():
    """Retrieve list of registered users on this installation for admin dashboard."""
    if not USERS_FILE.exists():
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_user_to_registry(profile: dict):
    """Save or update user in persistent users.json registry."""
    users = get_users_registry()
    user_id = profile.get("user_id")
    found = False
    for i, u in enumerate(users):
        if u.get("user_id") == user_id:
            users[i] = profile
            found = True
            break
    if not found:
        users.append(profile)
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    except Exception:
        pass
    return users

def get_settings():
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            if "download_dir" in data:
                data["download_dir"] = os.path.normpath(str(data["download_dir"]))
            return data
    except Exception:
        return DEFAULT_SETTINGS.copy()

def save_settings(new_settings):
    current = get_settings() if SETTINGS_FILE.exists() else DEFAULT_SETTINGS.copy()
    current.update(new_settings)
    if "download_dir" in current:
        current["download_dir"] = os.path.normpath(str(current["download_dir"]))
    # Ensure download directory exists
    download_dir = Path(current["download_dir"])
    download_dir.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4)
    return current

def get_ydl_cookie_opts():
    """Builds cookie, JS runtime, and EJS solver options for yt-dlp to bypass bot checks."""
    opts = {
        'js_runtimes': {'node': {}},
        'remote_components': ['ejs:github'],
    }
    settings = get_settings()
    source = settings.get("cookie_source", "auto")

    if source == "none":
        return opts

    if source == "browser":
        browser = settings.get("cookie_browser", "chrome")
        opts['cookiesfrombrowser'] = (browser, None, None, None)
        return opts

    # For "auto" or "file":
    # 1. Direct configured cookie file
    cfg_file = settings.get("cookie_file", "").strip()
    if cfg_file and Path(cfg_file).exists() and Path(cfg_file).is_file():
        opts['cookiefile'] = str(cfg_file)
        return opts

    # 2. Check for cookies.txt in project root
    if DEFAULT_COOKIE_FILE.exists():
        opts['cookiefile'] = str(DEFAULT_COOKIE_FILE)
        return opts

    # 3. Check for cookies.txt in user's download directory
    dl_cookie = Path(settings.get("download_dir", "")) / "cookies.txt"
    if dl_cookie.exists():
        opts['cookiefile'] = str(dl_cookie)
        return opts

    return opts

# Ensure default download folder exists on startup
DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
