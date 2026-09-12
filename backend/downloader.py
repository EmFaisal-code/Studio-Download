import os
import re
import uuid
import shutil
import threading
import time
from pathlib import Path
import yt_dlp

from backend.config import get_settings, get_ydl_cookie_opts, get_bundle_dir
from backend.history import add_history_entry, update_history_entry
from backend.parser import format_bytes, is_tiktok_url, fetch_tiktok_tikwm

# Global active downloads dictionary: {task_id: task_data}
active_tasks = {}
# Cancellation events: {task_id: threading.Event}
cancel_events = {}
# Queue for tasks waiting for concurrency slot: [(task_id, url, options, out_dir)]
download_queue = []
# Concurrency tracking lock
running_tasks_lock = threading.Lock()
# Listeners for real-time progress events: [callable]
progress_subscribers = []

class DownloadCancelledException(Exception):
    pass

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
        task_id = str(uuid.uuid4())[:8]
        settings = get_settings()
        out_dir = options.get("custom_dir") or settings.get("download_dir")
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        cancel_events[task_id] = threading.Event()

        max_concurrent = settings.get("max_concurrent_downloads", 2)
        if max_concurrent is None:
            max_concurrent = 2

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        duration = options.get("duration", "--")
        duration_seconds = options.get("duration_seconds", 0)
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
            "filesize_bytes": 0,
            "duration": duration,
            "duration_seconds": duration_seconds,
            "bitrate": bitrate,
            "filepath": "",
            "error": "",
            "created_at": now_str,
            "updated_at": now_str,
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

    def dismiss_task(self, task_id: str):
        if task_id in active_tasks:
            del active_tasks[task_id]
        if task_id in cancel_events:
            del cancel_events[task_id]
        return True

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

        cancel_ev = cancel_events.get(task_id)
        # Dedicated isolated temporary directory for this task to avoid Windows file locks
        temp_dir = os.path.join(out_dir, f".studio_temp_{task_id}")

        try:
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
                    task["downloaded"] = f"{total_downloaded / (1024 * 1024):.1f} MB"
                    task["total"] = f"{total_bytes / (1024 * 1024):.1f} MB" if total_bytes > 0 else "Unknown"

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

            ydl_opts = {
                'outtmpl': out_template,
                'progress_hooks': [ytdl_hook],
                'postprocessor_hooks': [postprocessor_hook],
                'quiet': True,
                'no_warnings': True,
                'windowsfilenames': True,
                'restrictfilenames': False,
                'http_chunk_size': 10485760,  # 10 MB chunks
                'hls_prefer_native': True,
                'concurrent_fragment_downloads': 4,
            }
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

            # Enable Chrome impersonation via curl_cffi for anti-bot bypass
            try:
                from yt_dlp.networking.impersonate import ImpersonateTarget
                ydl_opts['impersonate'] = ImpersonateTarget.from_str('chrome')
                ydl_opts['extractor_args'] = {'generic': {'impersonate': ['chrome']}}
            except Exception:
                pass

            # Speed limit configuration
            speed_limit_kb = settings.get("download_speed_limit", 0)
            if speed_limit_kb and int(speed_limit_kb) > 0:
                ydl_opts['ratelimit'] = int(speed_limit_kb) * 1024  # bytes per second

            format_id = options.get("format_id")
            is_yt = ("youtube.com" in url.lower() or "youtu.be" in url.lower())

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

                # If a specific stream format_id was chosen (non-YouTube)
                if not is_yt and format_id and format_id != "best":
                    ydl_opts['format'] = f"{format_id}+bestaudio/{format_id}/best"
                # Codec strategy:
                # "compatible" = Avoid AV1, prefer VP9/H.264 and AAC (m4a) audio.
                elif codec_pref == "compatible":
                    if height:
                        ydl_opts['format'] = (
                            f"bestvideo[height<={height}][vcodec!^=av01][vcodec!^=av1]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}][vcodec!^=av01][vcodec!^=av1]+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio[ext=m4a]/"
                            f"bestvideo[height<={height}]+bestaudio/best"
                        )
                    else:
                        ydl_opts['format'] = (
                            "bestvideo[vcodec!^=av01][vcodec!^=av1]+bestaudio[ext=m4a]/"
                            "bestvideo[vcodec!^=av01][vcodec!^=av1]+bestaudio/"
                            "bestvideo+bestaudio/best"
                        )
                else:
                    # "av1" preference:
                    if height:
                        ydl_opts['format'] = (
                            f"bestvideo[height<={height}][vcodec^=av01]+bestaudio/"
                            f"bestvideo[height<={height}]+bestaudio/best"
                        )
                    else:
                        ydl_opts['format'] = "bestvideo+bestaudio/best"

                ydl_opts['merge_output_format'] = merge_fmt

            info = None
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
            except Exception as ydl_err:
                err_str = str(ydl_err)
                if any(t in err_str.lower() for t in ("curl: (77)", "transporterror", "trust anchors", "cafile")) and 'impersonate' in ydl_opts:
                    retry_opts = ydl_opts.copy()
                    retry_opts.pop('impersonate', None)
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

            # Generate clean unique destination filepath in out_dir
            final_dest = get_unique_filepath(out_dir, title, target_ext)
            shutil.move(source_file, final_dest)

            # Read actual finished file size
            actual_size = os.path.getsize(final_dest)
            actual_size_mb = f"{actual_size / (1024 * 1024):.1f} MB"
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
            if "Failed to decrypt with DPAPI" in clean_err or "DPAPI" in clean_err:
                clean_err = "CHROME_DPAPI_BLOCKED: Google Chrome versi terbaru di Windows memblokir pembacaan cookies langsung dari database (App-Bound DPAPI Encryption). Solusi: Gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG dengan ekstensi 'Get cookies.txt LOCALLY'."
            elif "Could not copy" in clean_err and "cookie database" in clean_err:
                clean_err = "BROWSER_LOCKED: Database cookie browser terkunci karena browser sedang berjalan di Windows. Tutup browser terlebih dahulu, atau gunakan opsi 'AUTO // File cookies.txt'."
            elif "Sign in to confirm you're not a bot" in clean_err or "not a bot" in clean_err:
                clean_err = "BOT_CHECK_REQUIRED: YouTube mewajibkan verifikasi autentikasi (Sign in to confirm you're not a bot). Silakan atur cookies di menu CONFIG."
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
            # Clean up the isolated temp directory
            if os.path.exists(temp_dir):
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

        tt_data = fetch_tiktok_tikwm(url)
        if not tt_data:
            raise RuntimeError("Gagal mengambil data TikTok dari TikWM.")

        mode = options.get("mode", "video")
        req_format = options.get("format", "mp4").lower()
        format_id = options.get("format_id", "tiktok_standard")

        # Select target URL
        if mode == "audio":
            dl_url = tt_data.get("music")
            if not dl_url:
                dl_url = tt_data.get("play") or tt_data.get("hdplay")
            raw_filename = "audio_raw.mp3"
        else:
            if format_id == "tiktok_hd" and tt_data.get("hdplay"):
                dl_url = tt_data.get("hdplay")
            else:
                dl_url = tt_data.get("play") or tt_data.get("hdplay")
            raw_filename = "video_raw.mp4"

        if not dl_url:
            raise RuntimeError("URL media TikTok tidak ditemukan.")

        task["status"] = "downloading"
        task["eta"] = "Mengunduh media TikTok (No Watermark)..."
        broadcast_progress(task_id, task)

        temp_file = os.path.join(temp_dir, raw_filename)
        req = urllib.request.Request(dl_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        })

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
        tt_title = tt_data.get("title") or options.get("title") or f"TikTok_{author_name}"
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
                    broadcast_progress(task_id, task)

            # 3. Remux to mp4 with ffmpeg
            task["status"] = "muxing"
            task["progress"] = 98.0
            task["eta"] = "Mengemas file MP4 (FFmpeg)..."
            broadcast_progress(task_id, task)

            final_dest = get_unique_filepath(out_dir, title, requested_format)
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
