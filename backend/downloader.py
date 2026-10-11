import os
import sys
import re
import uuid
import shutil
import threading
import subprocess
import time
from pathlib import Path
import yt_dlp

from backend.config import get_settings, get_ydl_cookie_opts, get_bundle_dir
from backend.history import add_history_entry, update_history_entry
from backend.parser import (
    format_bytes, format_duration, format_time_label, parse_time_str,
    is_tiktok_url, fetch_tiktok_tikwm, fetch_tiktok_original_task,
    resolve_tiktok_url, normalize_youtube_url, get_prores_bitrate_mbps
)

# Global active downloads dictionary: {task_id: task_data}
active_tasks = {}
# Cancellation events: {task_id: threading.Event}
cancel_events = {}
# Pause events: {task_id: threading.Event} (set = running, clear = paused)
pause_events = {}
# Active threads: {task_id: threading.Thread}
active_threads = {}
# Active spawned subprocesses (ffmpeg, etc.): {task_id: subprocess.Popen}
active_subprocesses = {}
# Thread-local storage for passing task context to monkeypatched downloaders
_thread_local = threading.local()
# Queue for tasks waiting for concurrency slot: [(task_id, url, options, out_dir)]
download_queue = []
# Concurrency tracking lock
running_tasks_lock = threading.Lock()
# Listeners for real-time progress events: [callable]
progress_subscribers = []

class DownloadCancelledException(Exception):
    pass

class YtDlpTaskLogger:
    """Interceptors logs from yt-dlp to update detailed connecting/download stages."""
    def __init__(self, task_id, task):
        self.task_id = task_id
        self.task = task

    def debug(self, msg):
        self._handle(msg)

    def info(self, msg):
        self._handle(msg)

    def warning(self, msg):
        pass

    def error(self, msg):
        if msg:
            m = str(msg).strip()
            self.task["_last_log_error"] = m

    def _handle(self, msg):
        if not msg:
            return
        m = str(msg).strip()
        if self.task.get("status") == "starting":
            if "Downloading webpage" in m:
                self.task["eta"] = "Membaca metadata video..."
                broadcast_progress(self.task_id, self.task)
            elif any(k in m for k in ("Downloading player", "Downloading ios player", "Downloading visionos", "Downloading mweb")):
                self.task["eta"] = "Menyiapkan stream & solver YouTube..."
                broadcast_progress(self.task_id, self.task)
            elif "Downloading m3u8" in m:
                self.task["eta"] = "Menganalisis manifest HLS..."
                broadcast_progress(self.task_id, self.task)
            elif "Downloading 1 time ranges" in m or "time range" in m:
                self.task["eta"] = "Menghubungkan ke rentang klip..."
                broadcast_progress(self.task_id, self.task)
            elif "Destination:" in m:
                self.task["eta"] = "Memulai transfer data..."
                broadcast_progress(self.task_id, self.task)

def _get_best_temp_dir(target_out_dir: str, required_bytes: int, task_id: str) -> str:
    """
    Determines optimal isolated temp directory.
    When merging high-res videos (4K / 2160p), both input streams and merged output file
    coexist on disk (requiring ~2.2x the file size).
    If the target drive has insufficient space for both, this automatically routes
    the temporary stream files to a secondary drive with ample space (e.g., D:),
    allowing FFmpeg to merge seamlessly into target_out_dir without 'Conversion failed!' errors.
    """
    try:
        target_free = shutil.disk_usage(target_out_dir).free
    except Exception:
        target_free = 0

    # If target drive has plenty of headroom (>= 2.2x required or >= required + 8GB), use local temp
    safe_target_headroom = max(int(required_bytes * 2.2), int(required_bytes + 8 * 1024**3)) if required_bytes > 0 else 0
    if required_bytes <= 0 or target_free >= safe_target_headroom:
        return os.path.join(target_out_dir, f".studio_temp_{task_id}")

    # Search for high-capacity drive
    candidate_roots = []
    from backend.config import get_app_dir, get_bundle_dir
    candidate_roots.append(str(get_app_dir()))
    candidate_roots.append(str(get_bundle_dir()))

    if sys.platform == "win32":
        import string
        import ctypes
        try:
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    candidate_roots.append(f"{letter}:\\")
                bitmask >>= 1
        except Exception:
            pass

    best_root = None
    best_free = target_free

    for c_root in candidate_roots:
        try:
            if not os.path.exists(c_root):
                continue
            free_sp = shutil.disk_usage(c_root).free
            if free_sp > best_free and free_sp >= max(int(required_bytes * 1.3), 1024**3):
                best_free = free_sp
                best_root = c_root
        except Exception:
            pass

    if best_root and best_free > target_free:
        alt_temp = os.path.join(best_root, "StudioDownload_Temp", f".studio_temp_{task_id}")
        try:
            os.makedirs(alt_temp, exist_ok=True)
            return alt_temp
        except Exception:
            pass

    return os.path.join(target_out_dir, f".studio_temp_{task_id}")

def _parse_ffmpeg_size_bytes(sz_str: str) -> int:
    if not sz_str:
        return 0
    m = re.match(r"([\d\.]+)\s*([a-zA-Z]+)", sz_str.strip())
    if not m:
        return 0
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit in ("kib", "kb"):
        return int(val * 1024)
    if unit in ("mib", "mb"):
        return int(val * 1024 * 1024)
    if unit in ("gib", "gb"):
        return int(val * 1024 * 1024 * 1024)
    return int(val)

def _stream_ffmpeg_progress(proc, task_id, target_duration):
    buf = bytearray()
    last_b = 0
    try:
        while proc.poll() is None:
            chunk = proc.stderr.read(128)
            if not chunk:
                break
            buf.extend(chunk)
            while b'\r' in buf or b'\n' in buf:
                r_idx = buf.find(b'\r')
                n_idx = buf.find(b'\n')
                indices = [i for i in (r_idx, n_idx) if i >= 0]
                idx = min(indices)
                line = buf[:idx].decode('utf-8', errors='ignore').strip()
                buf = buf[idx+1:]
                if 'time=' in line:
                    time_m = re.search(r'time=(\d+):(\d+):(\d+\.?\d*)', line)
                    speed_m = re.search(r'speed=\s*([\d\.]+)x', line)
                    size_m = re.search(r'size=\s*([\d\.]+\s*\w+)', line)
                    if time_m:
                        h, m, s = time_m.groups()
                        sec = int(h)*3600 + int(m)*60 + float(s)
                        pct = min(98.5, max(0.5, (sec / target_duration * 100))) if target_duration > 0 else 0
                        spd = f"{speed_m.group(1)}x" if speed_m else "--"
                        sz = size_m.group(1) if size_m else "--"
                        now = time.time()
                        if now - last_b >= 0.12 or pct >= 98.0:
                            last_b = now
                            task = active_tasks.get(task_id)
                            if task and task.get("status") in ("starting", "downloading"):
                                task["status"] = "downloading"
                                task["progress"] = round(pct, 1)

                                cur_b = _parse_ffmpeg_size_bytes(sz)
                                dl_str = format_bytes(cur_b) if cur_b > 0 else sz
                                task["speed"] = f"{spd} ({dl_str})"
                                task["eta"] = f"Klip: {format_duration(sec)} / {format_duration(target_duration)}"
                                task["downloaded"] = dl_str

                                # Dynamically converge total file size based on actual bitrate
                                if target_duration > 0 and cur_b > 0 and sec >= 2.0:
                                    ratio = sec / target_duration
                                    est_total_b = int(cur_b / ratio)
                                    task["total"] = format_bytes(est_total_b)
                                elif task.get("filesize_bytes"):
                                    task["total"] = format_bytes(task["filesize_bytes"])

                                broadcast_progress(task_id, task)
    except Exception:
        pass
    finally:
        active_subprocesses.pop(task_id, None)

def _install_ffmpeg_range_monitor():
    try:
        from yt_dlp.downloader import FFmpegFD
        orig_popen = FFmpegFD._call_downloader.__globals__.get('Popen')
        if not orig_popen or getattr(orig_popen, '_is_monitored', False):
            return

        class MonitoredPopen(orig_popen):
            _is_monitored = True
            def __init__(self, *args, **kwargs):
                task_id = getattr(_thread_local, 'current_task_id', None)
                target_dur = getattr(_thread_local, 'target_duration', 0)
                if task_id:
                    cmd = list(args[0])
                    if '-loglevel' in cmd:
                        idx = cmd.index('-loglevel')
                        if idx + 1 < len(cmd):
                            cmd[idx+1] = 'info'
                    args = (cmd,) + args[1:]
                    kwargs['stderr'] = subprocess.PIPE
                    super().__init__(*args, **kwargs)
                    active_subprocesses[task_id] = self
                    t = threading.Thread(target=_stream_ffmpeg_progress, args=(self, task_id, target_dur), daemon=True)
                    t.start()
                else:
                    super().__init__(*args, **kwargs)

        FFmpegFD._call_downloader.__globals__['Popen'] = MonitoredPopen
    except Exception as e:
        print(f"[!] Warning: Failed to install FFmpeg range monitor: {e}")

_install_ffmpeg_range_monitor()

def subscribe_progress(callback):
    progress_subscribers.append(callback)

def unsubscribe_progress(callback):
    if callback in progress_subscribers:
        progress_subscribers.remove(callback)

def broadcast_progress(task_id, data):
    for sub in list(progress_subscribers):
        try:
            sub(task_id, data)
        except Exception:
            pass

def clean_filename(title: str) -> str:
    if not title:
        return "video"
    t = title.strip()
    # Strip leading Watch / Nonton / Streaming
    t = re.sub(r'^(?:Watch|Nonton|Streaming)\s+', '', t, flags=re.I)
    # Strip common site ad tags and watermark suffixes
    t = re.sub(r'\s+(?:English\s+Sub(?:/Dub)?\s+)?online\s+Free(?:\s+on\s+[\w\.\-]+)?.*$', '', t, flags=re.I)
    t = re.sub(r'\s*-\s*(?:Anikoto|Otakudesu|Samehadaku|Kuramanime|Oploverz|AnimeIndo|Bilibili|Bstation).*$', '', t, flags=re.I)
    t = re.sub(r'\s*\|\s*(?:Anikoto|Otakudesu|Samehadaku|Kuramanime|Oploverz|AnimeIndo).*$', '', t, flags=re.I)
    # Replace colon with dash for clean Windows filenames
    t = re.sub(r'\s*:\s*', ' - ', t)
    # Strip Windows reserved characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', "", t).strip()
    cleaned = re.sub(r'[\s\.\-]+$', '', cleaned)
    return cleaned if cleaned else "video"

def get_unique_filepath(directory: str, title: str, ext: str) -> str:
    base_name = clean_filename(title)
    candidate = os.path.join(directory, f"{base_name}.{ext}")
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(directory, f"{base_name} ({counter}).{ext}")
        counter += 1
    return candidate

def format_speed(bytes_per_sec):
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "0 KB/s"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    return f"{bytes_per_sec / 1024:.1f} KB/s"

def format_time(seconds):
    if not seconds or seconds <= 0:
        return "0s"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"

class DownloadManager:
    def __init__(self):
        pass

    def subscribe_progress(self, callback):
        subscribe_progress(callback)

    def unsubscribe_progress(self, callback):
        unsubscribe_progress(callback)

    def _get_active_running_count(self) -> int:
        return sum(
            1 for t in active_tasks.values()
            if t.get("status") in ("starting", "downloading", "muxing")
        )

    def start_download(self, url: str, options: dict):
        """
        options: {
            "mode": "video" | "audio",
            "height": int (optional),
            "format": "mp4" | "mkv" | "mp3" | "m4a",
            "codec_preference": "compatible" | "av1",
            "audio_quality": "320" | "192",
            "title": str (optional),
            "thumbnail": str (optional),
            "duration": str (optional),
            "duration_seconds": int (optional),
            "filesize_approx": str (optional),
            "bitrate": str (optional),
            "custom_dir": str (optional)
        }
        """
        url = normalize_youtube_url(url)
        task_id = str(uuid.uuid4())[:8]
        settings = get_settings()
        out_dir = options.get("custom_dir") or settings.get("download_dir")
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        cancel_events[task_id] = threading.Event()
        pause_events[task_id] = threading.Event()
        pause_events[task_id].set()

        max_concurrent = settings.get("max_concurrent_downloads", 2)
        if max_concurrent is None:
            max_concurrent = 2

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        duration = options.get("duration", "--")
        duration_seconds = options.get("duration_seconds", 0)

        # Check section start and end for multi-clip trimming
        sec_start = options.get("section_start")
        sec_end = options.get("section_end")
        if sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start):
            duration_seconds = int(float(sec_end) - float(sec_start))
            duration = format_duration(duration_seconds)
            s_lbl = format_time_label(sec_start)
            e_lbl = format_time_label(sec_end)
            clip_tag = f"[{s_lbl}-{e_lbl}]"
            base_title = options.get("title", "Video")
            if clip_tag not in base_title:
                options["title"] = f"{base_title} {clip_tag}"

            # Calculate realistic pro-rated or bitrate-estimated size for the clip
            clip_dur_s = float(duration_seconds)
            full_dur_s = options.get("full_duration_seconds", 0)
            orig_bytes = options.get("filesize_bytes", 0)

            if options.get("mode") == "audio":
                bitrate_bps = 320_000
            else:
                h = options.get("height") or 1080
                bitrate_bps = 20_000_000 if h >= 2160 else (12_000_000 if h >= 1440 else 5_000_000)
            clip_est_bytes = int(clip_dur_s * bitrate_bps / 8)

            if full_dur_s > 0 and orig_bytes > 0 and full_dur_s > clip_dur_s:
                ratio = min(1.0, max(0.001, clip_dur_s / full_dur_s))
                clip_bytes = int(orig_bytes * ratio)
            elif orig_bytes > 0 and orig_bytes <= clip_est_bytes * 2.5:
                clip_bytes = orig_bytes
            else:
                clip_bytes = clip_est_bytes

            options["filesize_bytes"] = clip_bytes
            options["filesize_approx"] = format_bytes(clip_bytes)

        filesize_approx = options.get("filesize_approx", "")
        bitrate = options.get("bitrate", "")
        if not bitrate:
            if options.get("mode") == "audio":
                bitrate = f"{options.get('audio_quality', '320')} kbps"
            elif options.get("height"):
                bitrate = f"{options.get('height')}p"
            else:
                bitrate = "Standard"

        is_yt = ("youtube.com" in url.lower() or "youtu.be" in url.lower())
        is_tt = is_tiktok_url(url)
        if is_yt:
            eta_init = "Menghubungkan ke YouTube..."
        elif is_tt:
            eta_init = "Menghubungkan ke TikTok (TikWM)..."
        else:
            eta_init = "Menghubungkan ke server stream..."

        task_data = {
            "id": task_id,
            "url": url,
            "title": options.get("title", "Mengambil informasi..."),
            "thumbnail": options.get("thumbnail", ""),
            "mode": options.get("mode", "video"),
            "format": options.get("format", "mp4"),
            "resolution": f"{options.get('height')}p" if options.get("height") else "Audio",
            "status": "starting",
            "progress": 0,
            "speed": "0 KB/s",
            "eta": eta_init,
            "downloaded": "0 MB",
            "total": filesize_approx or "0 MB",
            "filesize_bytes": options.get("filesize_bytes", 0),
            "duration": duration,
            "duration_seconds": duration_seconds,
            "bitrate": bitrate,
            "filepath": "",
            "error": "",
            "created_at": now_str,
            "updated_at": now_str,
            "options": options,
            "_streams": {}  # stream_id -> {"downloaded": int, "total": int}
        }

        with running_tasks_lock:
            active_count = self._get_active_running_count()
            is_queued = (max_concurrent > 0 and active_count >= max_concurrent)
            if is_queued:
                task_data["status"] = "queued"
                task_data["eta"] = "Menunggu antrean..."
                task_data["speed"] = "Queued"
                active_tasks[task_id] = task_data
                add_history_entry(task_data)
                broadcast_progress(task_id, task_data)
                download_queue.append((task_id, url, options, out_dir))
                return task_id
            else:
                active_tasks[task_id] = task_data
                add_history_entry(task_data)
                broadcast_progress(task_id, task_data)

        # Run download in an isolated thread
        thread = threading.Thread(target=self._run_ytdlp, args=(task_id, url, options, out_dir), daemon=True)
        thread.start()

        return task_id

    def _start_next_queued_task(self):
        with running_tasks_lock:
            settings = get_settings()
            max_concurrent = settings.get("max_concurrent_downloads", 2)
            if max_concurrent is None:
                max_concurrent = 2

            active_count = self._get_active_running_count()
            if max_concurrent > 0 and active_count >= max_concurrent:
                return

            if not download_queue:
                return

            next_item = None
            while download_queue:
                candidate = download_queue.pop(0)
                cand_id = candidate[0]
                c_ev = cancel_events.get(cand_id)
                if c_ev and c_ev.is_set():
                    continue
                cand_task = active_tasks.get(cand_id)
                if not cand_task or cand_task.get("status") in ("cancelled", "completed", "error"):
                    continue
                next_item = candidate
                break

            if not next_item:
                return

            task_id, url, options, out_dir = next_item
            task = active_tasks.get(task_id)
            if task_id in active_threads:
                if task:
                    task["status"] = "downloading"
                    task["eta"] = "Melanjutkan unduhan..."
                    task["speed"] = "--"
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    task["updated_at"] = now_str
                    update_history_entry(task_id, {"status": "downloading", "updated_at": now_str})
                    broadcast_progress(task_id, task)
                if task_id in pause_events:
                    pause_events[task_id].set()
            else:
                if task:
                    task["status"] = "starting"
                    task["eta"] = "Menghubungkan ke YouTube..."
                    task["speed"] = "0 KB/s"
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    task["updated_at"] = now_str
                    update_history_entry(task_id, {"status": "starting", "updated_at": now_str})
                    broadcast_progress(task_id, task)

                thread = threading.Thread(target=self._run_ytdlp, args=(task_id, url, options, out_dir), daemon=True)
                thread.start()

    def cancel_download(self, task_id: str):
        if task_id in cancel_events:
            cancel_events[task_id].set()
        if task_id in pause_events:
            pause_events[task_id].set()

        proc = active_subprocesses.pop(task_id, None)
        if proc:
            try:
                proc.kill()
            except Exception:
                pass

        with running_tasks_lock:
            for item in list(download_queue):
                if item[0] == task_id:
                    download_queue.remove(item)

        task = active_tasks.get(task_id)
        if task:
            task["status"] = "cancelled"
            task["eta"] = "Dibatalkan"
            task["speed"] = "--"
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            task["updated_at"] = now_str
            update_history_entry(task_id, {"status": "cancelled", "updated_at": now_str})
            broadcast_progress(task_id, task)

        self._start_next_queued_task()
        return True

    def pause_download(self, task_id: str) -> bool:
        task = active_tasks.get(task_id)
        if not task:
            return False
        if task.get("status") in ("starting", "downloading", "queued"):
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            task["status"] = "paused"
            task["speed"] = "0 KB/s"
            task["eta"] = "Dijeda (Paused)"
            task["updated_at"] = now_str
            if task_id in pause_events:
                pause_events[task_id].clear()

            proc = active_subprocesses.get(task_id)
            if proc:
                try:
                    import ctypes
                    handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                    if handle:
                        ctypes.windll.ntdll.NtSuspendProcess(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                except Exception:
                    pass

            with running_tasks_lock:
                for item in list(download_queue):
                    if item[0] == task_id:
                        download_queue.remove(item)
            update_history_entry(task_id, {"status": "paused", "updated_at": now_str})
            broadcast_progress(task_id, task)
            self._start_next_queued_task()
            return True
        return False

    def resume_download(self, task_id: str) -> bool:
        task = active_tasks.get(task_id)
        if not task:
            return False
        if task.get("status") == "paused":
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            settings = get_settings()
            max_concurrent = settings.get("max_concurrent_downloads", 2)
            if max_concurrent is None:
                max_concurrent = 2

            with running_tasks_lock:
                active_count = self._get_active_running_count()
                if max_concurrent > 0 and active_count >= max_concurrent:
                    task["status"] = "queued"
                    task["eta"] = "Menunggu antrean..."
                    task["speed"] = "Queued"
                    task["updated_at"] = now_str
                    out_dir = task.get("options", {}).get("custom_dir") or settings.get("download_dir")
                    download_queue.append((task_id, task.get("url"), task.get("options", {}), out_dir))
                    update_history_entry(task_id, {"status": "queued", "updated_at": now_str})
                    broadcast_progress(task_id, task)
                    return True

            if task_id in active_threads:
                task["status"] = "downloading"
                task["speed"] = "--"
                task["eta"] = "Melanjutkan unduhan..."
                task["updated_at"] = now_str
                if task_id in pause_events:
                    pause_events[task_id].set()

                proc = active_subprocesses.get(task_id)
                if proc:
                    try:
                        import ctypes
                        handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                        if handle:
                            ctypes.windll.ntdll.NtResumeProcess(handle)
                            ctypes.windll.kernel32.CloseHandle(handle)
                    except Exception:
                        pass

                update_history_entry(task_id, {"status": "downloading", "updated_at": now_str})
                broadcast_progress(task_id, task)
                return True
            else:
                task["status"] = "starting"
                task["speed"] = "--"
                task["eta"] = "Menghubungkan..."
                task["updated_at"] = now_str
                if task_id in pause_events:
                    pause_events[task_id].set()
                update_history_entry(task_id, {"status": "starting", "updated_at": now_str})
                broadcast_progress(task_id, task)
                out_dir = task.get("options", {}).get("custom_dir") or settings.get("download_dir")
                thread = threading.Thread(target=self._run_ytdlp, args=(task_id, task.get("url"), task.get("options", {}), out_dir), daemon=True)
                thread.start()
                return True
        return False

    def dismiss_task(self, task_id: str):
        if task_id in active_tasks:
            del active_tasks[task_id]
        if task_id in cancel_events:
            del cancel_events[task_id]
        if task_id in pause_events:
            del pause_events[task_id]
        with running_tasks_lock:
            active_threads.pop(task_id, None)
        return True

    def delete_task(self, task_id: str):
        return self.dismiss_task(task_id)

    def retry_download(self, task_id: str):
        task = active_tasks.get(task_id)
        if not task:
            return None
        url = task.get("url")
        options = task.get("options") or {}
        self.dismiss_task(task_id)
        return self.start_download(url, options)

    def clear_inactive_tasks(self):
        to_delete = [
            tid for tid, t in active_tasks.items()
            if t.get("status") in ["completed", "error", "cancelled"]
        ]
        for tid in to_delete:
            self.dismiss_task(tid)
        return len(to_delete)

    def _run_ytdlp(self, task_id: str, url: str, options: dict, out_dir: str):
        task = active_tasks.get(task_id)
        if not task:
            return

        with running_tasks_lock:
            active_threads[task_id] = threading.current_thread()

        cancel_ev = cancel_events.get(task_id)
        temp_dir = None

        try:
            # Estimate required bytes for pre-flight disk validation and smart temp placement
            sec_start = options.get("section_start")
            sec_end = options.get("section_end")
            is_clip = sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start)

            approx_bytes = options.get("filesize_bytes") or task.get("filesize_bytes") or 0

            if is_clip:
                clip_dur_s = float(sec_end) - float(sec_start)
                if options.get("mode") == "audio":
                    bitrate_bps = 320_000
                else:
                    h = options.get("height") or 1080
                    bitrate_bps = 20_000_000 if h >= 2160 else (12_000_000 if h >= 1440 else 5_000_000)
                clip_est = int(clip_dur_s * bitrate_bps / 8)

                # Guard against approx_bytes carrying the whole video's full size
                if approx_bytes <= 0 or approx_bytes > clip_est * 2.5:
                    full_dur = options.get("full_duration_seconds", 0)
                    if full_dur > 0 and approx_bytes > 0:
                        approx_bytes = int(approx_bytes * min(1.0, clip_dur_s / full_dur))
                    else:
                        approx_bytes = clip_est
            elif not approx_bytes and options.get("duration_seconds"):
                dur_s = options.get("duration_seconds", 0)
                if options.get("mode") == "audio":
                    bitrate_bps = 320_000
                else:
                    h = options.get("height") or 1080
                    bitrate_bps = 20_000_000 if h >= 2160 else (12_000_000 if h >= 1440 else 5_000_000)
                approx_bytes = int(dur_s * bitrate_bps / 8)

            # Pre-flight check: ensure target out_dir has space for at least the final file
            out_free = shutil.disk_usage(out_dir).free
            if approx_bytes > 0 and out_free < int(approx_bytes * 1.05):
                drive_name = Path(out_dir).drive or out_dir
                raise RuntimeError(
                    f"DISK_FULL: Ruang kosong pada drive {drive_name} tidak mencukupi. "
                    f"Tersisa {format_bytes(out_free)}, dibutuhkan minimal {format_bytes(int(approx_bytes * 1.05))}. "
                    f"Silakan kosongkan ruang disk atau ubah Download Directory di menu [CONFIG] Settings."
                )

            # Automatically pick optimal temporary directory (routes to high-capacity secondary drive if target drive is tight)
            temp_dir = _get_best_temp_dir(out_dir, approx_bytes, task_id)
            os.makedirs(temp_dir, exist_ok=True)
            settings = get_settings()

            # Dedicated fast no-watermark download for TikTok
            if is_tiktok_url(url):
                try:
                    self._download_tiktok(task_id, url, options, out_dir, temp_dir, cancel_ev)
                    return
                except DownloadCancelledException:
                    raise
                except Exception as tt_err:
                    print(f"[!] TikWM direct download failed ({tt_err}), falling back to yt-dlp...")

            # Immediate status broadcast
            task["status"] = "starting"
            task["eta"] = "Menghubungkan ke YouTube..."
            broadcast_progress(task_id, task)

            def ytdl_hook(d):
                if cancel_ev and cancel_ev.is_set():
                    raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")

                pause_ev = pause_events.get(task_id)
                if pause_ev and not pause_ev.is_set():
                    while pause_ev and not pause_ev.is_set():
                        if cancel_ev and cancel_ev.is_set():
                            raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")
                        time.sleep(0.25)

                status = d.get('status')
                if status == 'downloading':
                    # Track cumulative progress across multiple streams (video + audio)
                    info = d.get('info_dict') or {}
                    stream_id = info.get('format_id') or 'default'

                    dl_bytes = d.get('downloaded_bytes') or 0
                    tot_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0

                    task["_streams"][stream_id] = {
                        "downloaded": dl_bytes,
                        "total": tot_bytes
                    }

                    total_downloaded = sum(s["downloaded"] for s in task["_streams"].values())
                    total_bytes = sum(s["total"] for s in task["_streams"].values())

                    pct = (total_downloaded / total_bytes * 100) if total_bytes > 0 else 0
                    # Cap progress at 98% until muxing is completely done
                    pct = min(pct, 98.0)

                    speed = d.get('speed', 0)
                    eta = d.get('eta', 0)

                    task["status"] = "downloading"
                    task["progress"] = round(pct, 1)
                    task["speed"] = format_speed(speed)
                    task["eta"] = format_time(eta)
                    task["downloaded"] = format_bytes(total_downloaded)
                    known_fs = task.get("filesize_bytes") or options.get("filesize_bytes") or 0
                    if total_bytes > 0:
                        if known_fs > 0 and total_bytes < int(known_fs * 0.5) and len(task["_streams"]) < 2:
                            task["total"] = format_bytes(known_fs)
                        else:
                            task["total"] = format_bytes(total_bytes)
                    else:
                        task["total"] = format_bytes(known_fs) if known_fs > 0 else (filesize_approx or "Unknown")

                    now = time.time()
                    last_b = task.get("_last_broadcast", 0)
                    if now - last_b >= 0.08 or pct >= 98.0:
                        task["_last_broadcast"] = now
                        broadcast_progress(task_id, task)

                elif status == 'finished':
                    task["status"] = "muxing"
                    task["progress"] = 99.0
                    task["speed"] = "--"
                    task["eta"] = "Menggabungkan video & audio (FFmpeg)..."
                    broadcast_progress(task_id, task)

            def postprocessor_hook(d):
                if cancel_ev and cancel_ev.is_set():
                    raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")
                status = d.get('status')
                if status == 'started':
                    task["status"] = "muxing"
                    task["eta"] = "Memproses format..."
                    broadcast_progress(task_id, task)

            mode = options.get("mode", "video")
            requested_format = options.get("format", "mp4")
            height = options.get("height")
            codec_pref = options.get("codec_preference", "compatible")

            # Isolated output template inside temp_dir
            out_template = os.path.join(temp_dir, "media.%(ext)s")

            # Multi-clip / time range slicing support
            sec_start = options.get("section_start")
            sec_end = options.get("section_end")
            target_dur = 0
            ydl_opts_ranges = None
            if sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start):
                from yt_dlp.utils import download_range_func
                ydl_opts_ranges = download_range_func(None, [(float(sec_start), float(sec_end))])
                target_dur = float(sec_end) - float(sec_start)

            _thread_local.current_task_id = task_id
            _thread_local.current_task = task
            _thread_local.target_duration = target_dur

            ydl_opts = {
                'outtmpl': out_template,
                'progress_hooks': [ytdl_hook],
                'postprocessor_hooks': [postprocessor_hook],
                'logger': YtDlpTaskLogger(task_id, task),
                'no_warnings': True,
                'noplaylist': True,
                'windowsfilenames': True,
                'restrictfilenames': False,
                'http_chunk_size': 10485760,  # 10 MB chunks (prevents connection stalls on massive 4K/2160p downloads while keeping pause/resume responsive)
                'hls_prefer_native': True,
                'concurrent_fragment_downloads': 4,
                'socket_timeout': 30,
                'retries': 10,
                'fragment_retries': 10,
                'file_access_retries': 5,
            }

            if ydl_opts_ranges:
                ydl_opts['download_ranges'] = ydl_opts_ranges
                ydl_opts['force_keyframes_at_cuts'] = False

            # Add cookie and JS runtime options
            ydl_opts.update(get_ydl_cookie_opts())

            # Add custom HTTP headers (Referer, Origin, Cookie, User-Agent, etc.) if provided
            custom_headers = options.get("headers") or {}
            referer = options.get("referer")
            cookie = options.get("cookie")
            user_agent = options.get("user_agent")
            if referer:
                custom_headers["Referer"] = referer
            if cookie:
                custom_headers["Cookie"] = cookie
            if user_agent:
                custom_headers["User-Agent"] = user_agent
            if custom_headers:
                ydl_opts['http_headers'] = custom_headers

            format_id = options.get("format_id")
            is_yt = ("youtube.com" in url.lower() or "youtu.be" in url.lower())

            # Enable Chrome impersonation via curl_cffi only for non-YouTube / generic sites that need Cloudflare bypass
            # (Do NOT force curl_cffi on YouTube stream downloads as googlevideo.com CDN does not require Cloudflare TLS bypass
            # and curl_cffi triggers curl: (28) timeout on large 4K / 2160p video chunks).
            if not is_yt:
                try:
                    from yt_dlp.networking.impersonate import ImpersonateTarget
                    ydl_opts['impersonate'] = ImpersonateTarget.from_str('chrome')
                    if 'extractor_args' not in ydl_opts:
                        ydl_opts['extractor_args'] = {}
                    ydl_opts['extractor_args']['generic'] = {'impersonate': ['chrome']}
                except Exception:
                    pass

            # Speed limit configuration
            speed_limit_kb = settings.get("download_speed_limit", 0)
            if speed_limit_kb and int(speed_limit_kb) > 0:
                ydl_opts['ratelimit'] = int(speed_limit_kb) * 1024  # bytes per second

            if mode == "audio":
                audio_quality = options.get("audio_quality", "320")
                ydl_opts['format'] = 'bestaudio/best'
                if requested_format == "mp3":
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': str(audio_quality),
                    }]
                elif requested_format == "m4a":
                    ydl_opts['postprocessors'] = [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'm4a',
                    }]
            else:
                # Video mode
                merge_fmt = requested_format if requested_format in ["mp4", "mkv"] else "mp4"
                is_clip = bool(ydl_opts_ranges)

                # Clip / time range slicing on YouTube:
                # Prefer m3u8_native (HLS) streams for both video and audio because FFmpeg
                # fetches only the discrete segments for the requested time range,
                # avoiding draining gigabytes from byte 0 on long videos.
                if is_yt and is_clip:
                    if height:
                        ydl_opts['format'] = (
                            f"bestvideo[height<={height}][protocol^=m3u8]+bestaudio[protocol^=m3u8]/"
                            f"bestvideo[height<={height}]+bestaudio[protocol^=m3u8]/"
                            f"bestvideo[height<={height}]+bestaudio/"
                            f"{format_id}+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio/bestvideo+bestaudio"
                        )
                    else:
                        ydl_opts['format'] = (
                            "bestvideo[protocol^=m3u8]+bestaudio[protocol^=m3u8]/"
                            "bestvideo+bestaudio"
                        )
                # If a specific stream format_id was chosen (from format card)
                elif format_id and format_id != "best":
                    if height:
                        ydl_opts['format'] = (
                            f"{format_id}+bestaudio[ext=m4a]/"
                            f"{format_id}+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}]+bestaudio/"
                            f"{format_id}/bestvideo+bestaudio"
                        )
                    else:
                        ydl_opts['format'] = (
                            f"{format_id}+bestaudio[ext=m4a]/"
                            f"{format_id}+bestaudio/"
                            f"{format_id}/bestvideo+bestaudio"
                        )
                # Fallback Codec strategy if format_id not provided:
                elif codec_pref == "compatible":
                    if height:
                        ydl_opts['format'] = (
                            f"bestvideo[height<={height}][vcodec^=avc1]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}][vcodec^=avc1]+bestaudio/"
                            f"bestvideo[height<={height}][vcodec!^=av01][vcodec!^=av1]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}][vcodec!^=av01][vcodec!^=av1]+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio/bestvideo+bestaudio"
                        )
                    else:
                        ydl_opts['format'] = (
                            "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/"
                            "bestvideo[vcodec!^=av01][vcodec!^=av1]+bestaudio[ext=m4a]/"
                            "bestvideo+bestaudio"
                        )
                elif codec_pref == "prores":
                    if height:
                        ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio/bestvideo+bestaudio"
                    else:
                        ydl_opts['format'] = "bestvideo+bestaudio"
                else:
                    # "original" / "av1" preference:
                    if height:
                        ydl_opts['format'] = (
                            f"bestvideo[height<={height}][vcodec^=av01]+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio/bestvideo+bestaudio"
                        )
                    else:
                        ydl_opts['format'] = "bestvideo+bestaudio"

                ydl_opts['merge_output_format'] = merge_fmt
                if 'postprocessor_args' not in ydl_opts:
                    ydl_opts['postprocessor_args'] = {}
                if 'Merger' not in ydl_opts['postprocessor_args']:
                    ydl_opts['postprocessor_args']['Merger'] = ['-strict', '-2']

            info = None
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as ydl_err:
                err_str = str(ydl_err)
                # Universal fallback: if impersonate / curl_cffi hits any curl error (e.g. curl 28 timeout, curl 77 bad CA),
                # transporterror, or connection timeout, automatically retry cleanly using native yt-dlp HTTP transport.
                if any(t in err_str.lower() for t in ("curl:", "curl ", "transporterror", "trust anchors", "cafile", "timed out", "timeout")) and ('impersonate' in ydl_opts or 'extractor_args' in ydl_opts):
                    retry_opts = ydl_opts.copy()
                    retry_opts.pop('impersonate', None)
                    if 'extractor_args' in retry_opts:
                        retry_opts['extractor_args'] = {k: v for k, v in retry_opts['extractor_args'].items() if k != 'generic'}
                        if not retry_opts['extractor_args']:
                            retry_opts.pop('extractor_args', None)
                    try:
                        with yt_dlp.YoutubeDL(retry_opts) as retry_ydl:
                            info = retry_ydl.extract_info(url, download=True)
                    except Exception as retry_e:
                        ydl_err = retry_e

                if not info:
                    if not is_yt and (url.split('?')[0].lower().endswith(('.m3u8', '.ts')) or any(k in url.lower() for k in ('/hls/', '.m3u8', '/manifest/'))):
                        self._download_hls_fallback(task_id, url, options, out_dir, temp_dir, custom_headers, cancel_ev)
                        return
                    raise ydl_err

            # Prioritize real user/task title over yt-dlp's generic placeholder (e.g. index-f1)
            raw_info_title = (info and info.get("title")) or ""
            chosen_title = options.get("title") or task.get("title") or ""

            dummy_patterns = ["index", "master", "playlist", "manifest", "stream", "video", "unknown", "chunk", "fragment"]
            is_info_dummy = (
                not raw_info_title or
                any(raw_info_title.lower().startswith(d) for d in dummy_patterns) or
                any(d in raw_info_title.lower() for d in ["index-", "master-", "playlist-", "f1.m3u8", "index_"])
            )

            if chosen_title and (is_info_dummy or len(chosen_title) > len(raw_info_title)):
                title = clean_filename(chosen_title)
            else:
                title = clean_filename(raw_info_title) if not is_info_dummy else (clean_filename(chosen_title) or "video")

            # Locate the produced output file in temp_dir
            produced_files = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if not f.endswith('.part') and not f.endswith('.ytdl')
            ]

            target_ext = requested_format
            source_file = None
            for pf in produced_files:
                if pf.endswith(f".{target_ext}"):
                    source_file = pf
                    break
            if not source_file and produced_files:
                source_file = produced_files[0]
                _, target_ext = os.path.splitext(source_file)
                target_ext = target_ext.lstrip(".")

            if not source_file or not os.path.exists(source_file):
                raise RuntimeError("File hasil unduhan tidak ditemukan di direktori proses.")

            # Transcode to Apple ProRes 422 if requested
            if codec_pref == "prores":
                sec_start = options.get("section_start")
                sec_end = options.get("section_end")
                if sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start):
                    dur_sec = float(sec_end) - float(sec_start)
                else:
                    dur_sec = task.get("duration_seconds") or (info and info.get("duration")) or 0
                height = 1080
                try:
                    res_val = task.get("resolution", "")
                    m_h = re.search(r"(\d+)p?", str(res_val))
                    if m_h:
                        height = int(m_h.group(1))
                except Exception:
                    pass

                bitrate_mbps = get_prores_bitrate_mbps(height, 30)
                est_bytes = int(dur_sec * (bitrate_mbps * 125000) * 1.1) if dur_sec > 0 else (15 * 1024**3)
                free_space = shutil.disk_usage(temp_dir).free

                if free_space < est_bytes:
                    task["eta"] = f"Ruang disk ({format_bytes(free_space)}) tidak cukup untuk ProRes 422 (~{format_bytes(est_bytes)}). Format asli disimpan."
                    broadcast_progress(task_id, task)
                    time.sleep(2.0)
                else:
                    task["status"] = "muxing"
                    task["stage"] = "transcode_prores"
                    task["progress"] = 0.5
                    task["speed"] = "0.0x"
                    task["eta"] = "Menyiapkan Transcode ProRes 422 (0.0%)..."
                    broadcast_progress(task_id, task)
                    prores_file = os.path.join(temp_dir, f"prores_master.mov")
                    cmd = [
                        "ffmpeg", "-y",
                        "-nostats",
                        "-progress", "pipe:1",
                        "-i", source_file,
                        "-c:v", "prores_ks",
                        "-profile:v", "2",
                        "-vendor", "apl0",
                        "-c:a", "pcm_s16le",
                        prores_file
                    ]
                    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                    proc = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        bufsize=1,
                        creationflags=creationflags
                    )
                    active_subprocesses[task_id] = proc
                    try:
                        cur_sec = 0.0
                        cur_speed = "1.0x"
                        last_ui_update = 0
                        while True:
                            if cancel_events.get(task_id) and cancel_events[task_id].is_set():
                                try:
                                    proc.kill()
                                except Exception:
                                    pass
                                if os.path.exists(prores_file):
                                    try:
                                        os.remove(prores_file)
                                    except Exception:
                                        pass
                                raise DownloadCancelledException("Dibatalkan saat transcoding ProRes.")

                            line = proc.stdout.readline()
                            if not line and proc.poll() is not None:
                                break
                            if not line:
                                continue

                            line = line.strip()
                            if "=" in line:
                                k, v = line.split("=", 1)
                                k, v = k.strip(), v.strip()
                                if k == "out_time_ms":
                                    try:
                                        cur_sec = float(v) / 1_000_000.0
                                    except ValueError:
                                        pass
                                elif k == "speed":
                                    cur_speed = v
                                elif k == "progress" and v == "end":
                                    break

                            now = time.time()
                            if now - last_ui_update >= 0.25:
                                last_ui_update = now
                                if dur_sec > 0:
                                    pct = min(99.0, max(0.5, (cur_sec / dur_sec) * 100.0))
                                    spd_num = 1.0
                                    try:
                                        spd_num = float(cur_speed.rstrip('x').strip())
                                    except Exception:
                                        spd_num = 1.0
                                    if spd_num <= 0.05:
                                        spd_num = 1.0
                                    rem_sec = max(0, int((dur_sec - cur_sec) / spd_num))
                                    eta_str = format_duration(rem_sec)
                                    cur_t_str = format_duration(int(cur_sec))
                                    tot_t_str = format_duration(int(dur_sec))

                                    task["stage"] = "transcode_prores"
                                    task["progress"] = round(pct, 1)
                                    task["speed"] = cur_speed
                                    task["transcode_current"] = cur_t_str
                                    task["transcode_total"] = tot_t_str
                                    task["transcode_eta"] = eta_str
                                    task["eta"] = f"Transcode: {pct:.1f}% [{cur_t_str} / {tot_t_str}] @ {cur_speed}"
                                else:
                                    task["stage"] = "transcode_prores"
                                    task["progress"] = 50.0
                                    task["speed"] = cur_speed
                                    task["eta"] = f"Transcode ProRes 422: {format_duration(int(cur_sec))} @ {cur_speed}"
                                broadcast_progress(task_id, task)

                        proc.wait()
                        if proc.returncode == 0 and os.path.exists(prores_file):
                            try:
                                os.remove(source_file)
                            except Exception:
                                pass
                            source_file = prores_file
                            target_ext = "mov"
                    finally:
                        active_subprocesses.pop(task_id, None)

            # Generate clean unique destination filepath in out_dir
            final_dest = get_unique_filepath(out_dir, title, target_ext)
            shutil.move(source_file, final_dest)

            # Read actual finished file size
            actual_size = os.path.getsize(final_dest)
            actual_size_mb = format_bytes(actual_size)
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            dur_sec = (info and info.get("duration")) or task.get("duration_seconds") or 0
            dur_str = task.get("duration")
            if not dur_str or dur_str == "--":
                dur_str = format_time(dur_sec)

            bitrate_str = task.get("bitrate") or ""
            if not bitrate_str or bitrate_str == "Standard":
                if dur_sec and dur_sec > 0:
                    calc_kbps = int((actual_size * 8) / (dur_sec * 1000))
                    bitrate_str = f"{calc_kbps} kbps"
                else:
                    bitrate_str = task.get("resolution", "")

            task["status"] = "completed"
            task["progress"] = 100.0
            task["speed"] = "Selesai"
            task["eta"] = "Siap Ditonton / Diedit"
            task["filepath"] = final_dest
            task["title"] = title
            task["total"] = actual_size_mb
            task["downloaded"] = actual_size_mb
            task["filesize_bytes"] = actual_size
            task["duration"] = dur_str
            task["duration_seconds"] = dur_sec
            task["bitrate"] = bitrate_str
            task["updated_at"] = now_str
            task["thumbnail"] = (info and info.get("thumbnail")) or task["thumbnail"]

            update_history_entry(task_id, {
                "status": "completed",
                "filepath": final_dest,
                "title": task["title"],
                "thumbnail": task["thumbnail"],
                "total": actual_size_mb,
                "filesize_bytes": actual_size,
                "duration": dur_str,
                "duration_seconds": dur_sec,
                "bitrate": bitrate_str,
                "updated_at": now_str
            })
            broadcast_progress(task_id, task)

        except DownloadCancelledException as e:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            task["status"] = "cancelled"
            task["eta"] = "Dibatalkan"
            task["speed"] = "--"
            task["error"] = str(e)
            task["updated_at"] = now_str
            update_history_entry(task_id, {"status": "cancelled", "error": str(e), "updated_at": now_str})
            broadcast_progress(task_id, task)

        except Exception as e:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            raw_err = str(e)
            clean_err = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_err).strip()
            last_log = task.get("_last_log_error", "")
            if "disk_full" in clean_err.lower():
                pass
            elif any(k in last_log.lower() for k in ("no space left", "disk full", "error 112", "not enough space")):
                clean_err = f"DISK_FULL: Ruang penyimpanan disk tidak mencukupi saat proses penggabungan video & audio FFmpeg. {clean_err}"
            elif "Failed to decrypt with DPAPI" in clean_err or "DPAPI" in clean_err:
                clean_err = "CHROME_DPAPI_BLOCKED: Google Chrome versi terbaru di Windows memblokir pembacaan cookies langsung dari database (App-Bound DPAPI Encryption). Solusi: Gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG dengan ekstensi 'Get cookies.txt LOCALLY'."
            elif "Could not copy" in clean_err and "cookie database" in clean_err:
                clean_err = "BROWSER_LOCKED: Database cookie browser terkunci karena browser sedang berjalan di Windows. Tutup browser terlebih dahulu, atau gunakan opsi 'AUTO // File cookies.txt'."
            elif "Sign in to confirm you're not a bot" in clean_err or "not a bot" in clean_err:
                clean_err = "BOT_CHECK_REQUIRED: YouTube mewajibkan autentikasi akun (Sign in to confirm you're not a bot). Silakan ekspor & pasang file cookies.txt terbaru di menu [CONFIG]."
            elif "Conversion failed" in clean_err and last_log:
                clean_err = f"{clean_err} // Log FFmpeg: {last_log[:120]}"
            task["status"] = "error"
            task["error"] = clean_err
            task["eta"] = "Gagal"
            task["speed"] = "--"
            task["updated_at"] = now_str
            update_history_entry(task_id, {
                "status": "error",
                "error": clean_err,
                "updated_at": now_str
            })
            broadcast_progress(task_id, task)

        finally:
            _thread_local.current_task_id = None
            _thread_local.current_task = None
            _thread_local.target_duration = 0
            active_subprocesses.pop(task_id, None)

            with running_tasks_lock:
                active_threads.pop(task_id, None)

            # Clean up the isolated temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass

            self._start_next_queued_task()

    def _download_tiktok(self, task_id: str, url: str, options: dict, out_dir: str, temp_dir: str, cancel_ev: threading.Event):
        import urllib.request
        import subprocess

        task = active_tasks.get(task_id)
        if not task:
            return

        task["status"] = "starting"
        task["eta"] = "Menghubungkan ke server TikTok CDN (TikWM)..."
        task["speed"] = "--"
        broadcast_progress(task_id, task)

        canonical_url = resolve_tiktok_url(url)
        tt_data = fetch_tiktok_tikwm(canonical_url)
        if not tt_data:
            raise RuntimeError("Gagal mengambil data TikTok dari TikWM.")

        mode = options.get("mode", "video")
        req_format = options.get("format", "mp4").lower()
        format_id = options.get("format_id", "tiktok_original")

        # Select target URL
        if mode == "audio":
            dl_url = options.get("direct_url") or tt_data.get("music")
            if not dl_url:
                dl_url = tt_data.get("play") or tt_data.get("hdplay")
            raw_filename = "audio_raw.mp3"
        else:
            raw_filename = "video_raw.mp4"
            dl_url = None

            # If user wants Original File Size or HD, prioritize the genuine uncompressed original file
            if format_id in ("tiktok_original", "tiktok_hd") or not format_id:
                # 1. Check if a direct original URL was already provided in options
                direct_opt = options.get("direct_url")
                if direct_opt and ("_original.mp4" in direct_opt or "tokcdn.com" in direct_opt):
                    dl_url = direct_opt
                else:
                    task["status"] = "starting"
                    task["eta"] = "Mengambil stream video kualitas original (file size asli)..."
                    broadcast_progress(task_id, task)
                    try:
                        task_info = fetch_tiktok_original_task(canonical_url)
                        if task_info and task_info.get("play_url"):
                            dl_url = task_info["play_url"]
                    except Exception:
                        pass

                # Fallback to the stream with highest filesize if task unavailable
                if not dl_url:
                    hd_sz = int(tt_data.get("hd_size") or 0)
                    std_sz = int(tt_data.get("size") or 0)
                    if hd_sz >= std_sz and tt_data.get("hdplay"):
                        dl_url = tt_data.get("hdplay")
                    else:
                        dl_url = tt_data.get("play") or tt_data.get("hdplay")
            elif format_id == "tiktok_standard":
                dl_url = tt_data.get("play") or tt_data.get("hdplay")
            else:
                dl_url = options.get("direct_url") or tt_data.get("play") or tt_data.get("hdplay")

        if not dl_url:
            raise RuntimeError("URL media TikTok tidak ditemukan.")

        task["status"] = "downloading"
        if mode == "audio":
            task["eta"] = "Mengunduh audio TikTok (Music Track)..."
        else:
            task["eta"] = "Mengunduh media TikTok (Kualitas Asli / No Watermark)..."
        broadcast_progress(task_id, task)

        temp_file = os.path.join(temp_dir, raw_filename)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.tikwm.com/" if ("tokcdn.com" in dl_url or "tikwm.com" in dl_url) else "https://www.tiktok.com/"
        }
        req = urllib.request.Request(dl_url, headers=headers)

        speed_limit_kb = get_settings().get("download_speed_limit", 0)
        max_bytes_per_sec = int(speed_limit_kb) * 1024 if speed_limit_kb else 0

        with urllib.request.urlopen(req, timeout=25) as resp, open(temp_file, "wb") as f_out:
            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()
            last_update_time = start_time
            bytes_since_last = 0
            chunk_size = 65536

            while True:
                if cancel_ev and cancel_ev.is_set():
                    raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")

                pause_ev = pause_events.get(task_id)
                if pause_ev and not pause_ev.is_set():
                    while pause_ev and not pause_ev.is_set():
                        if cancel_ev and cancel_ev.is_set():
                            raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")
                        time.sleep(0.25)

                chunk_start = time.time()
                chunk = resp.read(chunk_size)
                if not chunk:
                    break

                f_out.write(chunk)
                downloaded += len(chunk)
                bytes_since_last += len(chunk)

                if max_bytes_per_sec > 0:
                    chunk_time = time.time() - chunk_start
                    expected_time = len(chunk) / max_bytes_per_sec
                    if expected_time > chunk_time:
                        time.sleep(expected_time - chunk_time)

                now = time.time()
                if now - last_update_time >= 0.35 or (total_size and downloaded >= total_size):
                    elapsed = now - last_update_time
                    speed_bps = bytes_since_last / elapsed if elapsed > 0 else 0
                    speed_str = format_speed(speed_bps)
                    progress = round((downloaded / total_size) * 100, 1) if total_size > 0 else 50.0

                    if total_size > 0 and speed_bps > 0:
                        eta_sec = int((total_size - downloaded) / speed_bps)
                        eta_str = format_time(eta_sec)
                    else:
                        eta_str = "--"

                    task["downloaded"] = format_bytes(downloaded)
                    task["total"] = format_bytes(total_size) if total_size > 0 else format_bytes(downloaded)
                    task["progress"] = progress
                    task["speed"] = speed_str
                    task["eta"] = eta_str
                    broadcast_progress(task_id, task)

                    last_update_time = now
                    bytes_since_last = 0

        author_name = tt_data.get("author", {}).get("unique_id") or "tiktok"
        tt_title = options.get("title") or tt_data.get("title") or f"TikTok_{author_name}"
        clean_title = clean_filename(tt_title)

        source_file = temp_file
        final_ext = req_format

        # Post-processing
        ffmpeg_bin = shutil.which("ffmpeg") or str(get_bundle_dir() / "ffmpeg.exe") or "ffmpeg"

        if mode == "audio":
            if req_format in ["mp3", "m4a"]:
                task["status"] = "muxing"
                task["eta"] = f"Mengonversi audio ke {req_format.upper()}..."
                broadcast_progress(task_id, task)

                conv_file = os.path.join(temp_dir, f"audio.{req_format}")
                if req_format == "mp3":
                    cmd = [ffmpeg_bin, "-y", "-i", temp_file, "-vn", "-b:a", f"{options.get('audio_quality', 320)}k", conv_file]
                else:
                    cmd = [ffmpeg_bin, "-y", "-i", temp_file, "-vn", "-c:a", "aac", "-b:a", "192k", conv_file]
                res = subprocess.run(cmd, capture_output=True)
                if res.returncode == 0 and os.path.exists(conv_file):
                    source_file = conv_file
        else:
            if req_format == "mkv":
                task["status"] = "muxing"
                task["eta"] = "Mengemas video ke kontainer MKV..."
                broadcast_progress(task_id, task)

                mkv_file = os.path.join(temp_dir, "media.mkv")
                cmd = [ffmpeg_bin, "-y", "-i", temp_file, "-c", "copy", mkv_file]
                res = subprocess.run(cmd, capture_output=True)
                if res.returncode == 0 and os.path.exists(mkv_file):
                    source_file = mkv_file

        # Multi-clip / time range slicing if requested
        sec_start = options.get("section_start")
        sec_end = options.get("section_end")
        if sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start):
            task["status"] = "muxing"
            task["eta"] = "Memotong durasi klip (FFmpeg)..."
            broadcast_progress(task_id, task)
            cut_file = os.path.join(temp_dir, f"cut_media.{final_ext}")
            cmd = [ffmpeg_bin, "-y", "-ss", str(sec_start), "-to", str(sec_end), "-i", source_file, "-c", "copy", "-avoid_negative_ts", "make_zero", cut_file]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and os.path.exists(cut_file) and os.path.getsize(cut_file) > 0:
                source_file = cut_file

        final_dest = get_unique_filepath(out_dir, clean_title, final_ext)
        shutil.move(source_file, final_dest)

        actual_size = os.path.getsize(final_dest)
        actual_size_mb = f"{actual_size / (1024 * 1024):.1f} MB"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        dur_sec = tt_data.get("duration", 0)
        dur_str = format_time(dur_sec) if dur_sec else "--"

        task["status"] = "completed"
        task["progress"] = 100.0
        task["speed"] = "Selesai"
        task["eta"] = "Siap Ditonton / Diedit"
        task["filepath"] = final_dest
        task["title"] = clean_title
        task["total"] = actual_size_mb
        task["downloaded"] = actual_size_mb
        task["filesize_bytes"] = actual_size
        task["duration"] = dur_str
        task["duration_seconds"] = dur_sec
        task["updated_at"] = now_str
        task["thumbnail"] = tt_data.get("cover") or tt_data.get("origin_cover") or task.get("thumbnail")

        update_history_entry(task_id, {
            "status": "completed",
            "filepath": final_dest,
            "title": task["title"],
            "thumbnail": task["thumbnail"],
            "total": actual_size_mb,
            "filesize_bytes": actual_size,
            "duration": dur_str,
            "duration_seconds": dur_sec,
            "updated_at": now_str
        })
        broadcast_progress(task_id, task)

    def _download_hls_fallback(self, task_id: str, url: str, options: dict, out_dir: str, temp_dir: str, custom_headers: dict, cancel_ev: threading.Event):
        from curl_cffi import requests
        from urllib.parse import urljoin
        import subprocess

        task = active_tasks.get(task_id)
        if not task:
            return

        try:
            task["status"] = "downloading"
            task["eta"] = "Menghubungkan stream via TLS Chrome..."
            task["speed"] = "--"
            broadcast_progress(task_id, task)

            session = requests.Session(impersonate="chrome120")
            headers = dict(custom_headers) if custom_headers else {}

            # 1. Fetch m3u8 playlist
            resp = session.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                raise RuntimeError(f"Gagal mengakses aliran stream: HTTP {resp.status_code}")

            m3u8_text = resp.text
            base_url = url

            # Check for variant stream (master playlist)
            if "#EXT-X-STREAM-INF" in m3u8_text:
                lines = m3u8_text.splitlines()
                best_variant = None
                for i, line in enumerate(lines):
                    if line.startswith("#EXT-X-STREAM-INF"):
                        for nl in lines[i+1:]:
                            nl_str = nl.strip()
                            if nl_str and not nl_str.startswith("#"):
                                best_variant = nl_str
                                break
                        if best_variant:
                            break
                if best_variant:
                    media_url = urljoin(base_url, best_variant)
                    base_url = media_url
                    resp = session.get(media_url, headers=headers, timeout=20)
                    if resp.status_code == 200:
                        m3u8_text = resp.text

            # 2. Extract segments
            segments = []
            for line in m3u8_text.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    segments.append(urljoin(base_url, line))

            if not segments:
                raise RuntimeError("Tidak ditemukan segmen video di dalam manifest stream.")

            total_segs = len(segments)
            raw_ts_path = os.path.join(temp_dir, "raw_stream.ts")
            title = task.get("title") or options.get("title") or "video_stream"
            requested_format = options.get("format", "mp4")

            start_time = time.time()
            downloaded_bytes = 0

            with open(raw_ts_path, "wb") as ts_file:
                for i, seg_url in enumerate(segments):
                    if cancel_ev and cancel_ev.is_set():
                        raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")

                    pause_ev = pause_events.get(task_id)
                    if pause_ev and not pause_ev.is_set():
                        while pause_ev and not pause_ev.is_set():
                            if cancel_ev and cancel_ev.is_set():
                                raise DownloadCancelledException("Unduhan dibatalkan oleh pengguna.")
                            time.sleep(0.25)

                    s_resp = session.get(seg_url, headers=headers, timeout=15)
                    if s_resp.status_code == 200:
                        ts_file.write(s_resp.content)
                        downloaded_bytes += len(s_resp.content)

                    # Update progress
                    elapsed = time.time() - start_time
                    speed_bps = (downloaded_bytes / elapsed) if elapsed > 0 else 0
                    pct = round(((i + 1) / total_segs) * 95.0, 1)

                    rem_segs = total_segs - (i + 1)
                    seg_time = elapsed / (i + 1) if (i + 1) > 0 else 0
                    eta_sec = int(rem_segs * seg_time)

                    task["status"] = "downloading"
                    task["progress"] = pct
                    task["speed"] = format_speed(speed_bps)
                    task["eta"] = format_time(eta_sec)
                    task["downloaded"] = f"{downloaded_bytes / (1024 * 1024):.1f} MB"
                    est_total = int(downloaded_bytes / (i + 1) * total_segs / (1024 * 1024)) if (i + 1) > 0 else 0
                    task["total"] = f"{est_total} MB"
                    
                    now = time.time()
                    last_b = task.get("_last_broadcast", 0)
                    if now - last_b >= 0.15 or i == total_segs - 1:
                        task["_last_broadcast"] = now
                        broadcast_progress(task_id, task)

            # 3. Remux to mp4 with ffmpeg
            task["status"] = "muxing"
            task["progress"] = 98.0
            task["eta"] = "Mengemas file MP4 (FFmpeg)..."
            broadcast_progress(task_id, task)

            final_dest = get_unique_filepath(out_dir, title, requested_format)
            sec_start = options.get("section_start")
            sec_end = options.get("section_end")
            if sec_start is not None and sec_end is not None and float(sec_end) > float(sec_start):
                cmd = ["ffmpeg", "-y", "-ss", str(sec_start), "-to", str(sec_end), "-i", raw_ts_path, "-c", "copy", "-avoid_negative_ts", "make_zero", final_dest]
            else:
                cmd = ["ffmpeg", "-y", "-i", raw_ts_path, "-c", "copy", final_dest]
            subprocess.run(cmd, capture_output=True)

            if not os.path.exists(final_dest) or os.path.getsize(final_dest) == 0:
                final_dest = get_unique_filepath(out_dir, title, "ts")
                shutil.move(raw_ts_path, final_dest)

            actual_size = os.path.getsize(final_dest)
            actual_size_mb = f"{actual_size / (1024 * 1024):.1f} MB"
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            task["status"] = "completed"
            task["progress"] = 100.0
            task["speed"] = "Selesai"
            task["eta"] = "Siap Ditonton / Diedit"
            task["filepath"] = final_dest
            task["total"] = actual_size_mb
            task["downloaded"] = actual_size_mb
            task["filesize_bytes"] = actual_size
            task["updated_at"] = now_str

            update_history_entry(task_id, {
                "status": "completed",
                "filepath": final_dest,
                "title": task["title"],
                "thumbnail": task["thumbnail"],
                "total": actual_size_mb,
                "filesize_bytes": actual_size,
                "duration": task.get("duration", "Stream HLS"),
                "duration_seconds": 0,
                "bitrate": "HLS Stream",
                "updated_at": now_str
            })
            broadcast_progress(task_id, task)

        except DownloadCancelledException as e:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            task["status"] = "cancelled"
            task["eta"] = "Dibatalkan"
            task["speed"] = "--"
            task["error"] = str(e)
            task["updated_at"] = now_str
            update_history_entry(task_id, {"status": "cancelled", "error": str(e), "updated_at": now_str})
            broadcast_progress(task_id, task)

        except Exception as e:
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")
            task["status"] = "error"
            task["error"] = str(e)
            task["eta"] = "Gagal"
            task["speed"] = "--"
            task["updated_at"] = now_str
            update_history_entry(task_id, {
                "status": "error",
                "error": str(e),
                "updated_at": now_str
            })
            broadcast_progress(task_id, task)

        finally:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception:
                    pass
            self._start_next_queued_task()

download_manager = DownloadManager()
