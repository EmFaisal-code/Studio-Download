import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

import uuid
import platform
from datetime import datetime

from backend.config import get_settings, save_settings, get_app_dir, get_bundle_dir, get_users_registry, save_user_to_registry
from backend.parser import parse_url
from backend.history import get_history, delete_history_entry, clear_all_history
from backend.downloader import download_manager, subscribe_progress, unsubscribe_progress, active_tasks
from backend.telemetry import sync_user_to_cloud

app = FastAPI(title="Studio Download API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = get_app_dir()
BUNDLE_DIR = get_bundle_dir()
FRONTEND_DIR = BUNDLE_DIR / "frontend"

# Active WebSocket connections
ws_clients = set()
loop = None

@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()

    # Register progress callback for DownloadManager
    def progress_listener(task_id, data):
        if not ws_clients or not loop:
            return
        payload = json.dumps({"type": "progress", "task_id": task_id, "data": data})
        for ws in list(ws_clients):
            try:
                asyncio.run_coroutine_threadsafe(ws.send_text(payload), loop)
            except Exception:
                pass

    subscribe_progress(progress_listener)

    # Sync current user to cloud database in background
    profile = get_settings().get("user_profile")
    if profile:
        asyncio.create_task(asyncio.to_thread(sync_user_to_cloud, profile))

class ParseRequest(BaseModel):
    url: str
    title: Optional[str] = None
    referer: Optional[str] = None
    cookie: Optional[str] = None
    user_agent: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    mode: str = "video"       # "video" or "audio"
    height: Optional[int] = None
    format: str = "mp4"       # "mp4", "mkv", "mp3", "m4a"
    codec_preference: str = "compatible" # "compatible" (VP9/H.264 + AAC) or "av1"
    audio_quality: str = "320"
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration: Optional[str] = None
    duration_seconds: Optional[int] = None
    filesize_approx: Optional[str] = None
    bitrate: Optional[str] = None
    custom_dir: Optional[str] = None
    referer: Optional[str] = None
    format_id: Optional[str] = None
    cookie: Optional[str] = None
    user_agent: Optional[str] = None

class SettingsRequest(BaseModel):
    download_dir: Optional[str] = None
    default_resolution: Optional[str] = None
    default_format: Optional[str] = None
    embed_thumbnail: Optional[bool] = None
    cookie_source: Optional[str] = None
    cookie_browser: Optional[str] = None
    cookie_file: Optional[str] = None
    theme: Optional[str] = None
    language: Optional[str] = None
    max_concurrent_downloads: Optional[int] = None
    download_speed_limit: Optional[int] = None

class CookiePasteRequest(BaseModel):
    content: str

class PathActionRequest(BaseModel):
    filepath: Optional[str] = None
    directory: Optional[str] = None

class UserRegisterRequest(BaseModel):
    username: str
    role: Optional[str] = "Editor / Creator"
    contact: Optional[str] = ""

class RemoteStreamRequest(BaseModel):
    url: str
    title: Optional[str] = None
    referer: Optional[str] = None
    cookie: Optional[str] = None
    user_agent: Optional[str] = None

# --- API ROUTES ---

@app.post("/api/remote_stream")
async def api_remote_stream(req: RemoteStreamRequest):
    # Bring the desktop software window to front if running on Windows
    import ctypes
    try:
        user32 = ctypes.windll.user32
        def enum_handler(hwnd, extra):
            length = user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value
            if "Studio Download" in title:
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                user32.SetForegroundWindow(hwnd)
                return False
            return True
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_handler), 0)
    except Exception:
        pass

    # Broadcast to all connected Studio Download windows (including desktop software window)
    if ws_clients and loop:
        payload = json.dumps({
            "type": "remote_stream",
            "url": req.url,
            "title": req.title,
            "referer": req.referer,
            "cookie": req.cookie,
            "user_agent": req.user_agent
        })
        for ws in list(ws_clients):
            try:
                asyncio.run_coroutine_threadsafe(ws.send_text(payload), loop)
            except Exception:
                pass
        return {"status": "sent_to_software", "clients_count": len(ws_clients)}

    return {"status": "no_clients"}

@app.post("/api/parse")
async def api_parse(req: ParseRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong.")
    try:
        custom_headers = {}
        if req.referer and req.referer.strip():
            custom_headers["Referer"] = req.referer.strip()
        if req.cookie and req.cookie.strip():
            custom_headers["Cookie"] = req.cookie.strip()
        if req.user_agent and req.user_agent.strip():
            custom_headers["User-Agent"] = req.user_agent.strip()
        # Run parsing in thread pool to not block async loop
        info = await asyncio.to_thread(parse_url, req.url.strip(), custom_headers or None, req.title)
        return info
    except Exception as e:
        err_msg = str(e)
        status_code = 403 if "BOT_CHECK_REQUIRED" in err_msg else 400
        raise HTTPException(status_code=status_code, detail=err_msg)

@app.post("/api/download")
async def api_download(req: DownloadRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="URL tidak boleh kosong.")
    try:
        options = req.model_dump()
        task_id = download_manager.start_download(req.url.strip(), options)
        return {"status": "started", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def api_get_tasks():
    return active_tasks

@app.post("/api/tasks/{task_id}/cancel")
async def api_cancel_task(task_id: str):
    download_manager.cancel_download(task_id)
    return {"status": "cancelled"}

@app.delete("/api/tasks/{task_id}")
async def api_dismiss_task(task_id: str):
    download_manager.dismiss_task(task_id)
    return {"status": "dismissed"}

@app.delete("/api/tasks")
async def api_clear_tasks():
    cleared = download_manager.clear_inactive_tasks()
    return {"status": "cleared", "count": cleared}

@app.get("/api/history")
async def api_get_history():
    return get_history()

@app.delete("/api/history/{task_id}")
async def api_delete_history(task_id: str, delete_file: bool = False):
    result = delete_history_entry(task_id, delete_file=delete_file)
    return result

@app.delete("/api/history")
async def api_clear_history(delete_files: bool = False):
    result = clear_all_history(delete_files=delete_files)
    return result

@app.get("/api/settings")
async def api_get_settings():
    return get_settings()

@app.post("/api/settings")
async def api_update_settings(req: SettingsRequest):
    new_data = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = save_settings(new_data)
    return updated

@app.get("/api/cookies/status")
async def api_cookies_status():
    settings = get_settings()
    source = settings.get("cookie_source", "auto")
    cf_path = settings.get("cookie_file") or str(BASE_DIR / "cookies.txt")
    has_file = os.path.exists(cf_path) and os.path.isfile(cf_path)
    file_size = os.path.getsize(cf_path) if has_file else 0

    return {
        "cookie_source": source,
        "cookie_browser": settings.get("cookie_browser", "chrome"),
        "has_cookie_file": has_file,
        "cookie_file_path": cf_path if has_file else "",
        "cookie_file_size": file_size
    }

@app.post("/api/cookies/paste")
async def api_cookies_paste(req: CookiePasteRequest):
    content = req.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Konten cookies kosong.")
    target_path = BASE_DIR / "cookies.txt"
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    # Automatically update settings to use this file
    save_settings({
        "cookie_source": "file",
        "cookie_file": str(target_path)
    })
    return {
        "status": "saved",
        "path": str(target_path),
        "size": len(content)
    }

@app.delete("/api/cookies")
async def api_cookies_delete():
    target_path = BASE_DIR / "cookies.txt"
    if target_path.exists():
        try:
            os.remove(target_path)
        except Exception:
            pass
    save_settings({
        "cookie_source": "none",
        "cookie_file": ""
    })
    return {"status": "cleared"}

@app.post("/api/open-folder")
async def api_open_folder(req: PathActionRequest):
    try:
        if req.filepath and os.path.exists(req.filepath):
            # Select file in Windows Explorer
            norm_path = os.path.normpath(req.filepath)
            subprocess.Popen(f'explorer /select,"{norm_path}"')
            return {"status": "ok"}
        elif req.directory and os.path.exists(req.directory):
            norm_path = os.path.normpath(req.directory)
            subprocess.Popen(f'explorer "{norm_path}"')
            return {"status": "ok"}
        else:
            settings = get_settings()
            d_dir = settings.get("download_dir")
            if os.path.exists(d_dir):
                subprocess.Popen(f'explorer "{os.path.normpath(d_dir)}"')
                return {"status": "ok"}
            raise HTTPException(status_code=404, detail="File atau folder tidak ditemukan.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/open-file")
async def api_open_file(req: PathActionRequest):
    try:
        if req.filepath and os.path.exists(req.filepath):
            os.startfile(os.path.normpath(req.filepath))
            return {"status": "ok"}
        raise HTTPException(status_code=404, detail="File tidak ditemukan di disk.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def resolve_extension_dir() -> Path:
    """Finds the browser extension directory across dev and portable builds."""
    candidates = [
        BASE_DIR / "Extension",
        BASE_DIR / "extra",
        BUNDLE_DIR / "Extension",
        BUNDLE_DIR / "extra",
    ]
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.insert(0, exe_dir / "Extension")
        candidates.insert(1, exe_dir / "extra")

    for p in candidates:
        if p.exists() and (p / "manifest.json").exists():
            return p

    for p in candidates:
        if p.exists():
            return p

    return candidates[0]

@app.get("/api/extension/info")
async def api_extension_info():
    ext_dir = resolve_extension_dir()
    exists = ext_dir.exists() and (ext_dir / "manifest.json").exists()
    return {
        "path": os.path.normpath(str(ext_dir)),
        "exists": exists,
        "version": "1.0",
        "install_url": "chrome://extensions"
    }

@app.post("/api/extension/open")
async def api_extension_open():
    ext_dir = resolve_extension_dir()
    if not ext_dir.exists():
        raise HTTPException(status_code=404, detail=f"Folder ekstensi tidak ditemukan: {ext_dir}")
    norm_path = os.path.normpath(str(ext_dir))
    try:
        subprocess.Popen(f'explorer "{norm_path}"')
        return {"status": "ok", "path": norm_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/current")
async def api_get_current_user():
    settings = get_settings()
    profile = settings.get("user_profile")
    users = get_users_registry()
    return {
        "registered": bool(profile and profile.get("username")),
        "profile": profile,
        "total_users_count": len(users)
    }

@app.post("/api/user/register")
async def api_register_user(req: UserRegisterRequest):
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username / nama wajib diisi.")
    
    settings = get_settings()
    existing_profile = settings.get("user_profile") or {}
    
    user_id = existing_profile.get("user_id") or f"usr_{uuid.uuid4().hex[:8]}"
    registered_at = existing_profile.get("registered_at") or datetime.now().isoformat()
    
    profile = {
        "user_id": user_id,
        "username": username,
        "role": req.role or "Editor / Creator",
        "contact": (req.contact or "").strip(),
        "registered_at": registered_at,
        "app_version": "v1.0",
        "platform": f"{platform.system()} {platform.release()}",
        "last_active": datetime.now().isoformat()
    }
    
    # Save into settings.json
    save_settings({"user_profile": profile})
    # Save into users.json registry
    save_user_to_registry(profile)
    # Sync to cloud database
    asyncio.create_task(asyncio.to_thread(sync_user_to_cloud, profile))
    
    return {
        "status": "ok",
        "profile": profile,
        "total_users": len(get_users_registry())
    }

@app.get("/api/admin/users")
async def api_admin_users():
    users = get_users_registry()
    history = get_history()
    settings = get_settings()
    return {
        "total_users": len(users),
        "users": users,
        "current_user": settings.get("user_profile"),
        "total_downloads": len(history),
        "app_version": "v1.0"
    }

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_clients.add(websocket)
    try:
        # Send current active tasks on connection
        await websocket.send_text(json.dumps({"type": "init", "tasks": active_tasks}))
        while True:
            # Keep alive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in ws_clients:
            ws_clients.remove(websocket)

# Mount frontend assets
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"status": "Frontend not ready yet."})
