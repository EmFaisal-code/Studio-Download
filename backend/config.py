import os
import sys
import json
from pathlib import Path

_APP_DIR_CACHE: Path | None = None

def _is_directory_writable(dir_path: Path) -> bool:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        test_file = dir_path / f".perm_check_{os.getpid()}"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")
        test_file.unlink(missing_ok=True)
        return True
    except Exception:
        return False

def get_app_dir() -> Path:
    """Returns directory where persistent user data (settings, history, cookies) is stored.
    Guarantees write permissions even when installed in protected directories like Program Files."""
    global _APP_DIR_CACHE
    if _APP_DIR_CACHE is not None:
        return _APP_DIR_CACHE

    # 1. In dev mode (not frozen), always use workspace root
    if not getattr(sys, 'frozen', False):
        _APP_DIR_CACHE = Path(__file__).resolve().parent.parent
        return _APP_DIR_CACHE

    exe_dir = Path(sys.executable).resolve().parent

    # 2. Check for explicit portable mode (e.g. portable.flag or portable.dat present)
    is_explicit_portable = (exe_dir / "portable.flag").exists() or (exe_dir / "portable.dat").exists()
    if is_explicit_portable and _is_directory_writable(exe_dir):
        _APP_DIR_CACHE = exe_dir
        return _APP_DIR_CACHE

    # 3. If installed to Program Files or exe_dir is not writable, use standard APPDATA directory
    is_system_dir = False
    for sys_var in ["ProgramFiles", "ProgramFiles(x86)", "ProgramW6432", "SystemRoot"]:
        val = os.environ.get(sys_var)
        if val and str(exe_dir).lower().startswith(val.lower()):
            is_system_dir = True
            break

    if not is_system_dir and _is_directory_writable(exe_dir):
        # Writable non-system directory (e.g. custom user folder, Desktop, USB drive)
        _APP_DIR_CACHE = exe_dir
        return _APP_DIR_CACHE

    # 4. Standard Windows / Cross-platform User Data Directory
    appdata_root = os.environ.get("APPDATA")
    if appdata_root:
        target_dir = Path(appdata_root) / "StudioDownload"
    else:
        target_dir = Path.home() / "AppData" / "Roaming" / "StudioDownload" if sys.platform == "win32" else Path.home() / ".config" / "StudioDownload"

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    if not _is_directory_writable(target_dir):
        # Fallback to user home directory
        target_dir = Path.home() / ".studiodownload"
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    # Copy bundled default settings.json if it exists and user settings does not yet exist
    try:
        user_settings = target_dir / "settings.json"
        bundle_settings = exe_dir / "settings.json"
        if bundle_settings.exists() and not user_settings.exists():
            import shutil
            shutil.copy2(bundle_settings, user_settings)
    except Exception:
        pass

    _APP_DIR_CACHE = target_dir
    return _APP_DIR_CACHE

def get_bundle_dir() -> Path:
    """Returns directory containing packaged read-only assets (frontend HTML, icons, templates)."""
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            return Path(sys._MEIPASS)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_app_dir()
SETTINGS_FILE = BASE_DIR / "settings.json"
USERS_FILE = BASE_DIR / "users.json"
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "StudioDownload"
DEFAULT_COOKIE_FILE = BASE_DIR / "cookies.txt"

# Configure SSL certificates for libcurl (curl_cffi), requests, and yt-dlp
def _init_ssl_certs():
    try:
        import certifi
        ca_path = ""
        candidates = [
            get_bundle_dir() / "_internal" / "certifi" / "cacert.pem",
            get_bundle_dir() / "certifi" / "cacert.pem",
            get_bundle_dir() / "cacert.pem",
            get_app_dir() / "_internal" / "certifi" / "cacert.pem",
            get_app_dir() / "certifi" / "cacert.pem",
            get_app_dir() / "cacert.pem",
        ]
        try:
            candidates.append(Path(certifi.where()))
        except Exception:
            pass

        for c in candidates:
            if c and c.exists() and c.stat().st_size > 1000:
                ca_path = str(c.resolve())
                break

        # Fallback for Windows: Export system Root certificates if no bundle exists
        if not ca_path and sys.platform == "win32":
            try:
                import ssl
                certs = ssl.enum_certificates("ROOT")
                if certs:
                    fallback_file = get_app_dir() / "_internal" / "certifi" / "cacert.pem"
                    fallback_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(fallback_file, "w", encoding="utf-8") as f:
                        for cert in certs:
                            f.write(ssl.DER_cert_to_PEM_cert(cert[0]))
                    if fallback_file.exists() and fallback_file.stat().st_size > 1000:
                        ca_path = str(fallback_file.resolve())
            except Exception:
                pass

        if ca_path:
            os.environ["SSL_CERT_FILE"] = ca_path
            os.environ["CURL_CA_BUNDLE"] = ca_path
            os.environ["REQUESTS_CA_BUNDLE"] = ca_path
            certifi.where = lambda: ca_path
            try:
                import curl_cffi.curl
                curl_cffi.curl.DEFAULT_CACERT = ca_path
            except Exception:
                pass
    except Exception:
        pass

def get_node_path() -> str:
    """Finds node.exe executable path on Windows / Linux / macOS."""
    import shutil
    p = shutil.which("node")
    if p:
        return p
    for cand in [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
        str(Path.home() / "AppData" / "Roaming" / "nvm" / "node.exe"),
    ]:
        if os.path.exists(cand):
            return cand
    return ""

# Ensure Node.js folder is in os.environ["PATH"] for yt-dlp JS challenge solvers
_np = get_node_path()
if _np:
    _ndir = str(Path(_np).parent)
    if _ndir.lower() not in os.environ.get("PATH", "").lower():
        os.environ["PATH"] = _ndir + os.pathsep + os.environ.get("PATH", "")

_init_ssl_certs()

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
    "theme": "developer-zinc",      # "modern-yellow", "developer-zinc"
    "language": "en",               # "en" (English), "id" (Bahasa Indonesia)
    "max_concurrent_downloads": 2,  # 0 = unlimited, 1, 2, 3, 5
    "download_speed_limit": 0,      # 0 = unlimited, in KB/s (e.g. 1024, 2048, 5120)
    "user_profile": None,           # None or dict: { user_id, username, role, contact, registered_at }
    "onboarding_completed": False
}

GUEST_PROFILE = {
    "user_id": "guest_session",
    "username": "Guest",
    "role": "Guest User",
    "contact": "",
    "registered_at": "",
    "app_version": "v1.0",
    "platform": "",
    "is_guest": True
}

_active_session_profile = None

def get_guest_profile() -> dict:
    """Return a fresh copy of the default guest session profile."""
    return GUEST_PROFILE.copy()

def get_active_session_profile() -> dict:
    """Get the currently active in-memory user session profile."""
    global _active_session_profile
    if _active_session_profile is not None:
        return _active_session_profile

    # Fallback to saved profile in settings.json if exists
    try:
        settings = get_settings()
        saved_profile = settings.get("user_profile")
        if saved_profile and isinstance(saved_profile, dict) and saved_profile.get("username"):
            _active_session_profile = saved_profile
            return _active_session_profile
    except Exception:
        pass

    _active_session_profile = get_guest_profile()
    return _active_session_profile

def set_active_session_profile(profile: dict | None):
    """Set active in-memory user session profile."""
    global _active_session_profile
    if profile is None:
        _active_session_profile = get_guest_profile()
    else:
        _active_session_profile = profile

def logout_to_guest():
    """Switch the current session to guest mode and set onboarding as completed."""
    global _active_session_profile
    _active_session_profile = get_guest_profile()
    try:
        save_settings({
            "user_profile": _active_session_profile,
            "onboarding_completed": True
        })
    except Exception as e:
        print(f"[!] Warning: Failed to save guest profile: {e}")
    return _active_session_profile

def register_and_activate_user(username: str, role: str = "Video Editor (Universal)", contact: str = "") -> dict:
    """Register a new user identity or update existing one, activate session, and persist to Supabase & local."""
    import uuid
    import platform as plat
    from datetime import datetime

    raw_username = username.strip()
    clean_username = f"@{raw_username}" if not raw_username.startswith("@") else raw_username

    existing_profile = {}
    try:
        settings = get_settings()
        existing_profile = settings.get("user_profile") or {}
    except Exception:
        pass

    now_iso = datetime.now().isoformat()
    registered_at = existing_profile.get("registered_at") or now_iso
    initial_uid = existing_profile.get("user_id") if (existing_profile.get("username") == clean_username) else f"usr_{uuid.uuid4().hex[:8]}"

    profile = {
        "user_id": initial_uid,
        "username": clean_username,
        "role": role or "Video Editor (Universal)",
        "contact": contact.strip() if contact else "",
        "registered_at": registered_at,
        "app_version": "v1.0",
        "platform": f"{plat.system()} {plat.release()}",
        "last_active": now_iso,
        "is_guest": False
    }

    # Synchronize to Supabase immediately (silent fallback if offline or fails)
    try:
        from backend.telemetry import sync_user_to_cloud
        res = sync_user_to_cloud(profile)
        if res and res.get("id"):
            profile["user_id"] = res.get("id")
    except Exception:
        pass

    # Persist in settings and users registry
    try:
        save_settings({
            "user_profile": profile,
            "onboarding_completed": True
        })
        save_user_to_registry(profile)
    except Exception as e:
        print(f"[!] Warning: Failed to persist user profile: {e}")

    set_active_session_profile(profile)
    return profile

def get_users_registry():
    """Retrieve list of locally saved user profiles on this machine."""
    try:
        if not USERS_FILE.exists():
            return []
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_user_to_registry(profile: dict):
    """Save or update user profile locally on this machine."""
    users = get_users_registry()
    user_id = profile.get("user_id")
    found = False
    for i, u in enumerate(users):
        if u.get("user_id") == user_id or u.get("username") == profile.get("username"):
            users[i] = profile
            found = True
            break
    if not found:
        users.append(profile)
    try:
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print(f"[!] Warning: Failed to write to {USERS_FILE}: {e}")
    return users


def get_settings():
    if not SETTINGS_FILE.exists():
        try:
            save_settings(DEFAULT_SETTINGS)
        except Exception:
            pass
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
    except Exception as e:
        print(f"[!] Warning: Failed to read settings from {SETTINGS_FILE}: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(new_settings):
    try:
        current = get_settings() if SETTINGS_FILE.exists() else DEFAULT_SETTINGS.copy()
        current.update(new_settings)
        if "download_dir" in current:
            current["download_dir"] = os.path.normpath(str(current["download_dir"]))
        # Ensure download directory exists
        try:
            download_dir = Path(current["download_dir"])
            download_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4)
        return current
    except Exception as e:
        print(f"[!] Warning: Failed to write settings to {SETTINGS_FILE}: {e}")
        try:
            current.update(new_settings)
            return current
        except Exception:
            return DEFAULT_SETTINGS.copy()

def get_ydl_cookie_opts():
    """Builds cookie, JS runtime, and EJS solver options for yt-dlp to bypass bot checks."""
    node_exe = get_node_path()
    opts = {
        'remote_components': ['ejs:github'],
    }
    if node_exe:
        opts['js_runtimes'] = {'node': {'path': node_exe}}
    else:
        opts['js_runtimes'] = {'node': {}}
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

    # 2. Check for cookies.txt in user data / app directory
    app_cookie = get_app_dir() / "cookies.txt"
    if app_cookie.exists():
        opts['cookiefile'] = str(app_cookie)
        return opts

    # 3. Check for cookies.txt in bundle / exe directory
    bundle_cookie = get_bundle_dir() / "cookies.txt"
    if bundle_cookie.exists():
        opts['cookiefile'] = str(bundle_cookie)
        return opts

    # 4. Check for cookies.txt in project root
    if DEFAULT_COOKIE_FILE.exists():
        opts['cookiefile'] = str(DEFAULT_COOKIE_FILE)
        return opts

    # 5. Check for cookies.txt in user's download directory
    dl_cookie = Path(settings.get("download_dir", "")) / "cookies.txt"
    if dl_cookie.exists():
        opts['cookiefile'] = str(dl_cookie)
        return opts

    return opts

# Ensure default download folder exists on startup
try:
    DEFAULT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
