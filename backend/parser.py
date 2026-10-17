import math
import re
import yt_dlp
from backend.config import get_ydl_cookie_opts

def format_duration(seconds):
    if not seconds:
        return "00:00"
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def format_duration_hms(seconds) -> str:
    """Guaranteed 3-part HH:MM:SS format (e.g. 00:00:00, 01:25:30, 04:27:00)."""
    if not seconds:
        return "00:00:00"
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def parse_time_str(val) -> int:
    """Parses timestamp strings (HH:MM:SS, MM:SS, or seconds) into integer seconds."""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return max(0, int(val))
    s = str(val).strip().strip("'\"")
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    parts = s.split(":")
    try:
        if len(parts) == 3:
            h, m, sec = parts
            return max(0, int(h) * 3600 + int(m) * 60 + int(float(sec)))
        elif len(parts) == 2:
            m, sec = parts
            return max(0, int(m) * 60 + int(float(sec)))
        elif len(parts) == 1:
            return max(0, int(float(parts[0])))
    except Exception:
        pass
    return 0

def format_time_label(seconds: int) -> str:
    """Formats seconds into filename-safe notation: MM.SS or HH.MM.SS."""
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}.{m:02d}.{s:02d}"
    return f"{m:02d}.{s:02d}"

def format_bytes(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "Estimasi N/A"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    i = min(i, len(size_name) - 1)
    p = math.pow(1024, i)
    s = size_bytes / p
    if i >= 3:  # GB or TB
        return f"{s:.2f} {size_name[i]}"
    elif i >= 1:  # KB or MB
        return f"{s:.1f} {size_name[i]}"
    else:
        return f"{int(s)} B"

def get_prores_bitrate_mbps(height: int, fps: int = 30) -> int:
    fps_mult = (fps / 30.0) if fps and fps > 0 else 1.0
    if height >= 4320:
        base = 1884
    elif height >= 2160:
        base = 471
    elif height >= 1440:
        base = 208
    elif height >= 1080:
        base = 117
    elif height >= 720:
        base = 59
    elif height >= 480:
        base = 27
    elif height >= 360:
        base = 15
    elif height >= 240:
        base = 8
    else:
        base = 4
    return int(base * fps_mult)

def is_youtube_url(url: str) -> bool:
    return bool(re.search(r'(?:youtube\.com|youtu\.be)', url, re.IGNORECASE))

def normalize_youtube_url(url: str) -> str:
    """
    Normalizes YouTube URLs containing query parameters (like &list=, &index=, ?si=, &t=)
    to a canonical single-video URL (https://www.youtube.com/watch?v=VIDEO_ID)
    whenever a specific video ID is present.
    Preserves pure playlist URLs (e.g. /playlist?list=...) that have no video ID.
    """
    if not url:
        return ""
    clean = url.strip()
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(clean)
        netloc = parsed.netloc.lower()
        if any(h in netloc for h in ("youtube.com", "youtu.be", "youtube-nocookie.com")):
            # 1. Shortened link: youtu.be/<video_id>
            if "youtu.be" in netloc:
                video_id = parsed.path.strip("/").split("/")[0]
                if video_id and len(video_id) == 11:
                    return f"https://www.youtube.com/watch?v={video_id}"

            # 2. Path-based video IDs: /shorts/<id>, /live/<id>, /embed/<id>, /v/<id>
            path_parts = [p for p in parsed.path.strip("/").split("/") if p]
            if len(path_parts) >= 2 and path_parts[0] in ("shorts", "live", "embed", "v"):
                video_id = path_parts[1]
                if video_id and len(video_id) == 11:
                    return f"https://www.youtube.com/watch?v={video_id}"

            # 3. Query-based video IDs: watch?v=<id> or any path with ?v=<id>
            qs = parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                video_id = qs["v"][0]
                if video_id and len(video_id) == 11:
                    return f"https://www.youtube.com/watch?v={video_id}"
    except Exception:
        pass
    return clean


def is_tiktok_url(url: str) -> bool:
    return bool(re.search(r'(?:tiktok\.com|vt\.tiktok\.com|vm\.tiktok\.com)', url, re.IGNORECASE))

def resolve_tiktok_url(url: str) -> str:
    """Resolve shortened TikTok links like vt.tiktok.com or vm.tiktok.com to canonical URL."""
    clean = url.strip()
    if any(k in clean.lower() for k in ('vt.tiktok.com', 'vm.tiktok.com', '/t/')):
        try:
            import urllib.request
            req = urllib.request.Request(clean, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            })
            with urllib.request.urlopen(req, timeout=8) as resp:
                return resp.geturl()
        except Exception:
            pass
    return clean

def fetch_tiktok_original_task(url: str, max_retries: int = 4, delay: float = 1.2) -> dict | None:
    """
    Submits an HD/Original download task to TikWM Original Downloader API
    (as used in 1.1.1 handleHDProcess), which provides the true uncompressed
    original video (_original.mp4) without watermark and with full original filesize.
    """
    import urllib.request
    import urllib.parse
    import json
    import time

    clean_url = resolve_tiktok_url(url)
    try:
        post_data = urllib.parse.urlencode({'url': clean_url, 'web': '1'}).encode('utf-8')
        req = urllib.request.Request(
            'https://www.tikwm.com/api/video/task/submit',
            data=post_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': 'https://www.tikwm.com/originalDownloader.html',
                'Origin': 'https://www.tikwm.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            s_data = json.loads(resp.read().decode('utf-8'))
            if s_data.get('code') != 0 or not s_data.get('data', {}).get('task_id'):
                return None
            task_id = s_data['data']['task_id']

        for _ in range(max_retries):
            time.sleep(delay)
            r_req = urllib.request.Request(
                f'https://www.tikwm.com/api/video/task/result?task_id={task_id}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
                    'Referer': 'https://www.tikwm.com/originalDownloader.html'
                }
            )
            with urllib.request.urlopen(r_req, timeout=10) as r_resp:
                r_data = json.loads(r_resp.read().decode('utf-8'))
                if r_data.get('code') == 0 and r_data.get('data'):
                    detail = r_data['data'].get('detail') or r_data['data']
                    play_url = detail.get('play_url') or detail.get('download_url') or detail.get('play')
                    if play_url:
                        return {
                            'play_url': play_url,
                            'download_url': detail.get('download_url') or play_url,
                            'size': int(detail.get('size') or 0),
                            'task_id': task_id
                        }
    except Exception:
        try:
            from curl_cffi import requests
            res = requests.post(
                'https://www.tikwm.com/api/video/task/submit',
                data={'url': clean_url, 'web': '1'},
                headers={
                    'Referer': 'https://www.tikwm.com/originalDownloader.html',
                    'Origin': 'https://www.tikwm.com',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                timeout=12,
                impersonate='chrome120'
            )
            if res.status_code == 200:
                s_json = res.json()
                task_id = s_json.get('data', {}).get('task_id')
                if task_id:
                    for _ in range(max_retries):
                        time.sleep(delay)
                        r_res = requests.get(
                            f'https://www.tikwm.com/api/video/task/result?task_id={task_id}',
                            headers={'Referer': 'https://www.tikwm.com/originalDownloader.html'},
                            timeout=10,
                            impersonate='chrome120'
                        )
                        if r_res.status_code == 200:
                            r_json = r_res.json()
                            detail = r_json.get('data', {}).get('detail') or r_json.get('data', {})
                            play_url = detail.get('play_url') or detail.get('download_url')
                            if play_url:
                                return {
                                    'play_url': play_url,
                                    'download_url': detail.get('download_url') or play_url,
                                    'size': int(detail.get('size') or 0),
                                    'task_id': task_id
                                }
        except Exception:
            pass

    return None

def fetch_tiktok_tikwm(url: str) -> dict | None:
    """Fetch video metadata and direct no-watermark download links from TikWM API."""
    try:
        import urllib.request
        import urllib.parse
        import json
        clean_url = resolve_tiktok_url(url)
        encoded_url = urllib.parse.quote(clean_url, safe='')
        api_endpoint = f"https://www.tikwm.com/api/?url={encoded_url}&hd=1"
        req = urllib.request.Request(
            api_endpoint,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Referer": "https://www.tikwm.com/"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("code") == 0 and res_data.get("data"):
                return res_data["data"]
    except Exception as e:
        try:
            from curl_cffi import requests
            clean_url = resolve_tiktok_url(url)
            res = requests.get(f"https://www.tikwm.com/api/?url={clean_url}&hd=1", timeout=12, impersonate="chrome120")
            if res.status_code == 200:
                res_data = res.json()
                if res_data.get("code") == 0 and res_data.get("data"):
                    return res_data["data"]
        except Exception:
            pass
    return None

def clean_stream_title(raw: str) -> str:
    if not raw:
        return ""
    t = raw.strip()
    # Strip leading Watch / Nonton / Streaming
    t = re.sub(r'^(?:Watch|Nonton|Streaming)\s+', '', t, flags=re.I)
    # Strip common site ad tags and watermark suffixes
    t = re.sub(r'\s+(?:English\s+Sub(?:/Dub)?\s+)?online\s+Free(?:\s+on\s+[\w\.\-]+)?.*$', '', t, flags=re.I)
    t = re.sub(r'\s*-\s*(?:Anikoto|Otakudesu|Samehadaku|Kuramanime|Oploverz|AnimeIndo|Bilibili|Bstation).*$', '', t, flags=re.I)
    t = re.sub(r'\s*\|\s*(?:Anikoto|Otakudesu|Samehadaku|Kuramanime|Oploverz|AnimeIndo).*$', '', t, flags=re.I)
    # Replace colon with dash for clean filenames
    t = re.sub(r'\s*:\s*', ' - ', t)
    # Strip Windows reserved characters: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/*?:"<>|]', '', t).strip()
    cleaned = re.sub(r'[\s\.\-]+$', '', cleaned)
    return cleaned if cleaned else raw.strip()

def is_stream_url(url: str) -> bool:
    clean = url.split('?')[0].lower()
    return clean.endswith(('.m3u8', '.mpd', '.ts', '.mp4')) or any(k in url.lower() for k in ('/hls/', '.m3u8', '/manifest/'))

def parse_url(url: str, custom_headers: dict = None, stream_title: str = None):
    url = normalize_youtube_url(url)
    is_yt = is_youtube_url(url)
    is_tt = is_tiktok_url(url)
    is_stream = is_stream_url(url)

    # 1. Fast TikTok extraction via TikWM (No Watermark & Direct HD Original)
    if is_tt:
        canonical_url = resolve_tiktok_url(url)
        import concurrent.futures
        tt_data = None
        task_res = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_tt = executor.submit(fetch_tiktok_tikwm, canonical_url)
            future_task = executor.submit(fetch_tiktok_original_task, canonical_url)
            try:
                tt_data = future_tt.result(timeout=10)
            except Exception:
                tt_data = None
            try:
                task_res = future_task.result(timeout=4)
            except Exception:
                task_res = None

        if tt_data:
            author_info = tt_data.get("author") or {}
            author_id = author_info.get("unique_id") or author_info.get("nickname") or "tiktok_creator"
            author_display = f"@{author_id}"

            raw_title = tt_data.get("title") or stream_title or ""
            display_title = clean_stream_title(raw_title) if raw_title else f"TikTok VT by {author_display}"

            dur_sec = tt_data.get("duration") or 0
            cover = tt_data.get("cover") or tt_data.get("origin_cover") or ""
            play_count = tt_data.get("play_count")
            views_str = f"{play_count:,}" if play_count else "N/A"

            std_sz = int(tt_data.get("size") or 0)
            hd_sz = int(tt_data.get("hd_size") or 0)
            orig_sz = int(task_res.get("size") or 0) if task_res else 0
            best_orig_sz = orig_sz if orig_sz > 0 else max(std_sz, hd_sz)

            resolutions = []

            # 1. Kualitas Asli / Source HD (File Size Asli)
            # Default pre-selected di index #0
            resolutions.append({
                "height": 1080,
                "label": "Kualitas Asli (Source)",
                "badge": "Original Size",
                "codec": "H.264 / AAC",
                "fps": 30,
                "tbr": 0,
                "filesize": best_orig_sz,
                "filesize_formatted": format_bytes(best_orig_sz) if best_orig_sz else "File Size Asli",
                "format_id": "tiktok_original",
                "container": "mp4",
                "direct_url": task_res.get("play_url") if task_res else None
            })

            # 2. HD Transcode (jika ada hdplay)
            if tt_data.get("hdplay"):
                resolutions.append({
                    "height": 1080 if hd_sz >= std_sz else 720,
                    "label": "1080p HD (TikWM Transcode)",
                    "badge": "TikWM HD",
                    "codec": "H.264 / H.265",
                    "fps": 30,
                    "tbr": 0,
                    "filesize": hd_sz,
                    "filesize_formatted": format_bytes(hd_sz) if hd_sz else "Full HD",
                    "format_id": "tiktok_hd",
                    "container": "mp4",
                    "direct_url": tt_data.get("hdplay")
                })

            # 3. Standar No Watermark
            resolutions.append({
                "height": 720,
                "label": "720p Standar (No Watermark)",
                "badge": "No Watermark",
                "codec": "H.264 / AAC",
                "fps": 30,
                "tbr": 0,
                "filesize": std_sz,
                "filesize_formatted": format_bytes(std_sz) if std_sz else "Standar (No WM)",
                "format_id": "tiktok_standard",
                "container": "mp4",
                "direct_url": tt_data.get("play")
            })

            music_info = tt_data.get("music_info") or {}
            music_title = music_info.get("title") or "Original Sound"

            audio_presets = [
                {
                    "format": "mp3",
                    "quality": "320",
                    "label": f"MP3 Audio VT ({music_title[:28]})" if music_title else "MP3 Audio VT (Original Sound)",
                    "badge": "TikWM Audio",
                    "filesize_formatted": "Audio MP3",
                    "direct_url": tt_data.get("music")
                },
                {
                    "format": "m4a",
                    "quality": "original",
                    "label": "M4A (Original Sound)",
                    "badge": "Original AAC",
                    "filesize_formatted": "Audio M4A",
                    "direct_url": tt_data.get("music")
                }
            ]

            return {
                "type": "video",
                "id": str(tt_data.get("id") or "tiktok_video"),
                "title": display_title,
                "uploader": author_display,
                "duration": format_duration(dur_sec),
                "duration_seconds": dur_sec,
                "views": views_str,
                "thumbnail": cover,
                "webpage_url": canonical_url,
                "source_type": "tiktok",
                "is_stream": False,
                "preview_url": (task_res.get("play_url") if task_res else None) or tt_data.get("play") or tt_data.get("hdplay") or "",
                "preview_options": [
                    {"height": 1080, "label": "1080p HD (Original Source)", "url": task_res.get("play_url") if task_res else (tt_data.get("hdplay") or tt_data.get("play")), "format_id": "tiktok_orig"},
                    {"height": 720, "label": "720p Standar (Smooth Scrubbing)", "url": tt_data.get("play") or (tt_data.get("hdplay")), "format_id": "tiktok_std"}
                ],
                "resolutions": resolutions,
                "audio_presets": audio_presets,
                "tiktok_raw": {
                    "play": tt_data.get("play"),
                    "hdplay": tt_data.get("hdplay"),
                    "music": tt_data.get("music"),
                    "original_url": task_res.get("play_url") if task_res else None,
                    "original_size": best_orig_sz
                }
            }

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'extract_flat': 'in_playlist',
        'skip_download': True,
    }
    # Integrate cookie & JS runtime options
    ydl_opts.update(get_ydl_cookie_opts())

    # Add custom headers (Referer, Origin, etc.) if provided
    if custom_headers:
        ydl_opts['http_headers'] = custom_headers

    # Enable Chrome impersonation via curl_cffi to pass Cloudflare TLS checks
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        ydl_opts['impersonate'] = ImpersonateTarget.from_str('chrome')
        ydl_opts['extractor_args'] = {'generic': {'impersonate': ['chrome']}}
    except Exception:
        pass

    info = None
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        raw_err = str(e)
        # Fallback: if impersonate / curl_cffi hits any curl error (28 timeout, 77 bad CA, etc.) or TransportError, retry cleanly without impersonate
        if any(term in raw_err.lower() for term in ("curl:", "curl ", "transporterror", "trust anchors", "cafile", "timed out", "timeout")) and 'impersonate' in ydl_opts:
            retry_opts = ydl_opts.copy()
            retry_opts.pop('impersonate', None)
            retry_opts.pop('extractor_args', None)
            try:
                with yt_dlp.YoutubeDL(retry_opts) as retry_ydl:
                    info = retry_ydl.extract_info(url, download=False)
            except Exception as retry_e:
                raw_err = str(retry_e)

        if not info:
            clean_err = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_err).strip()
            if is_stream:
                info = None
            else:
                err_low = clean_err.lower()
                if "failed to decrypt with dpapi" in err_low or "dpapi" in err_low:
                    raise ValueError("CHROME_DPAPI_BLOCKED: Google Chrome versi terbaru di Windows memblokir pembacaan cookies langsung dari database (App-Bound DPAPI Encryption). Solusi: Gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG dengan ekstensi Studio Download.")
                if "could not copy" in err_low and "cookie database" in err_low:
                    raise ValueError("BROWSER_LOCKED: Database cookie browser terkunci oleh Windows karena browser sedang dibuka/berjalan. Tutup browser sepenuhnya terlebih dahulu, ATAU gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG agar browser tidak perlu ditutup.")
                if "sign in to confirm you're not a bot" in err_low or "not a bot" in err_low:
                    raise ValueError("BOT_CHECK_REQUIRED: YouTube mewajibkan verifikasi autentikasi (Sign in to confirm you're not a bot). Silakan gunakan file cookies.txt atau impor cookie browser di menu CONFIG.")
                if "private video" in err_low:
                    raise ValueError("Video ini bersifat privat (Private Video). Diperlukan login akun yang memiliki izin akses.")
                if "video unavailable" in err_low or "is unavailable" in err_low:
                    raise ValueError("Video tidak tersedia atau telah dihapus oleh pemiliknya.")
                raise ValueError(f"Gagal menganalisis link: {clean_err}")

    if not info:
        if is_stream:
            # Construct reliable stream metadata so the UI immediately displays the download card
            import time
            from urllib.parse import urlparse
            parsed_u = urlparse(url)
            host_name = parsed_u.netloc or "HLS Stream"
            clean_path = parsed_u.path.rstrip('/').split('/')[-1] or "media"
            clean_name = clean_path.replace('.m3u8', '').replace('.mpd', '')
            display_title = clean_stream_title(stream_title) if stream_title else f"Stream Video ({clean_name})"

            return {
                "type": "video",
                "id": f"stream_{int(time.time())}",
                "title": display_title,
                "uploader": host_name,
                "duration": "Live / Stream",
                "duration_seconds": 0,
                "views": "N/A",
                "thumbnail": "",
                "webpage_url": url,
                "source_type": "hls",
                "is_stream": True,
                "preview_url": url,
                "preview_options": [{"height": 1080, "label": "Stream Asli (Direct)", "url": url, "format_id": "hls"}],
                "resolutions": [
                    {
                        "height": 1080,
                        "label": "1080p Full HD (Direct Stream)",
                        "badge": "1080p HD",
                        "codec": "H.264 / AAC",
                        "fps": 30,
                        "tbr": 0,
                        "filesize": 0,
                        "filesize_formatted": "Stream HLS",
                        "format_id": "best",
                        "container": "mp4"
                    },
                    {
                        "height": 720,
                        "label": "720p HD",
                        "badge": "720p",
                        "codec": "H.264 / AAC",
                        "fps": 30,
                        "tbr": 0,
                        "filesize": 0,
                        "filesize_formatted": "Stream HLS",
                        "format_id": "best",
                        "container": "mp4"
                    },
                    {
                        "height": 480,
                        "label": "480p SD",
                        "badge": "480p SD",
                        "codec": "H.264 / AAC",
                        "fps": 30,
                        "tbr": 0,
                        "filesize": 0,
                        "filesize_formatted": "Stream HLS",
                        "format_id": "best",
                        "container": "mp4"
                    }
                ],
                "audio_presets": [
                    {
                        "format": "mp3",
                        "quality": "320",
                        "label": "MP3 (320 kbps High Quality)",
                        "badge": "Studio Audio",
                        "filesize_formatted": "Audio Stream"
                    },
                    {
                        "format": "m4a",
                        "quality": "original",
                        "label": "M4A (Original Container)",
                        "badge": "Lossless Container",
                        "filesize_formatted": "Audio Stream"
                    }
                ]
            }
        raise ValueError("Tidak dapat mengambil informasi dari link tersebut.")

    # Check if it's a playlist
    if 'entries' in info:
        entries = []
        for entry in info.get('entries', []):
            if not entry:
                continue
            entries.append({
                "id": entry.get("id"),
                "title": entry.get("title", "Unknown Title"),
                "url": entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}",
                "duration": format_duration(entry.get("duration")),
                "thumbnail": entry.get("thumbnail") or (entry.get("thumbnails")[-1].get("url") if entry.get("thumbnails") else ""),
                "uploader": entry.get("uploader", "Unknown Channel")
            })
        return {
            "type": "playlist",
            "id": info.get("id"),
            "title": info.get("title", "YouTube Playlist"),
            "uploader": info.get("uploader", "Various"),
            "video_count": len(entries),
            "videos": entries
        }

    duration_sec = info.get("duration") or 0
    formats = info.get("formats", [])

    # Calculate best audio size
    audio_formats = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") != "none"]
    best_audio_size = 0
    if audio_formats:
        # Prefer AAC (ext=m4a) for compatibility or highest bitrate
        audio_formats.sort(key=lambda x: (x.get("ext") == "m4a", x.get("abr") or 0), reverse=True)
        best_audio = audio_formats[0]
        best_audio_size = best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
        if not best_audio_size and (best_audio.get("abr") or best_audio.get("tbr")) and duration_sec:
            best_audio_size = int(((best_audio.get("abr") or best_audio.get("tbr")) * 1000 / 8) * duration_sec)

    # Standard YouTube video heights to keep (ignore storyboards, weird crops)
    allowed_heights = {4320, 2160, 1440, 1080, 720, 480, 360, 240, 144}

    # Group video formats by height and codec family (h264, vp9, av1)
    formats_by_height_and_codec = {}
    resolution_meta = {}

    for f in formats:
        h = f.get("height")
        vcodec = f.get("vcodec") or ""
        ext = f.get("ext") or ""
        protocol = f.get("protocol") or ""
        format_id_str = str(f.get("format_id") or "")

        # Filter out storyboards (mhtml, none vcodec, or height not standard or < 144)
        if ext == "mhtml":
            continue
        if is_yt and (not h or vcodec == "none" or h < 144):
            continue
        if is_yt and h not in allowed_heights and (h < 144 or h > 4320):
            continue
        if not is_yt and vcodec == "none" and f.get("acodec") != "none":
            # Audio-only stream on generic site, handled in audio presets
            continue

        # Filter out YouTube internal HLS manifests (m3u8) & 600-series chunk manifests with inflated burst bitrates
        if is_yt and (protocol.startswith("m3u8") or format_id_str.startswith("6")):
            continue

        # For non-YT streams without explicit height, assign an estimated height or fallback
        fmt_key = h if h else (f.get("tbr") or f.get("format_id") or 720)
        display_h = h if h else 720

        fps = f.get("fps") or 30
        tbr = f.get("tbr") or f.get("vbr") or 0

        # Calculate accurate filesize
        fs = f.get("filesize") or f.get("filesize_approx") or 0
        has_real_size = bool(fs)
        if not fs and tbr and duration_sec:
            # Sanity clamp for estimated bitrate to prevent inflated estimates from HLS burst rates
            max_bitrates = {
                144: 350, 240: 600, 360: 1200, 480: 2500,
                720: 6000, 1080: 12000, 1440: 25000, 2160: 60000, 4320: 120000
            }
            clamped_tbr = min(tbr, max_bitrates.get(display_h, 25000))
            fs = int((clamped_tbr * 1000 / 8) * duration_sec)

        total_filesize = fs
        if f.get("acodec") == "none" and best_audio_size:
            total_filesize += best_audio_size

        if "av01" in vcodec or "av1" in vcodec:
            cfam = "av1"
            cname = "AV1"
        elif "vp09" in vcodec or "vp9" in vcodec:
            cfam = "vp9"
            cname = "VP9"
        else:
            cfam = "h264"
            cname = "H.264"

        if fmt_key not in formats_by_height_and_codec:
            formats_by_height_and_codec[fmt_key] = {}
            if display_h >= 4320:
                badge = "8K Ultra HD"
            elif display_h >= 2160:
                badge = "4K Ultra HD"
            elif display_h >= 1440:
                badge = "2K QHD"
            elif display_h >= 1080:
                badge = "1080p Full HD"
            elif display_h >= 720:
                badge = "720p HD"
            elif display_h >= 480:
                badge = f"{display_h}p SD"
            elif h:
                badge = f"{display_h}p"
            else:
                badge = "Direct Stream"

            resolution_meta[fmt_key] = {
                "height": display_h,
                "label": f"{display_h}p" if h else (f.get("format_note") or "Original"),
                "badge": badge
            }

        curr_stream = formats_by_height_and_codec[fmt_key].get(cfam)
        should_replace = False
        if not curr_stream:
            should_replace = True
        else:
            if not curr_stream["has_real_size"] and has_real_size:
                should_replace = True
            elif curr_stream["has_real_size"] and not has_real_size:
                should_replace = False
            elif fps > curr_stream["fps"]:
                should_replace = True
            elif fps == curr_stream["fps"] and tbr > curr_stream["tbr"]:
                should_replace = True

        if should_replace:
            formats_by_height_and_codec[fmt_key][cfam] = {
                "format_id": f.get("format_id"),
                "codec": cname,
                "fps": fps,
                "tbr": tbr,
                "has_real_size": has_real_size,
                "total_filesize": total_filesize,
                "container": "mp4"
            }

    video_resolutions = {}
    for fmt_key, stream_dict in formats_by_height_and_codec.items():
        meta = resolution_meta[fmt_key]
        display_h = meta["height"]

        h264_st = stream_dict.get("h264")
        vp9_st = stream_dict.get("vp9")
        av1_st = stream_dict.get("av1")

        best_overall = h264_st or vp9_st or av1_st or next(iter(stream_dict.values()))

        codecs_dict = {}

        # 1. Compatible (H.264 preference)
        if h264_st:
            codecs_dict["compatible"] = {
                "codec": "H.264",
                "format_id": h264_st["format_id"],
                "filesize": h264_st["total_filesize"],
                "filesize_formatted": format_bytes(h264_st["total_filesize"]),
                "fps": h264_st["fps"],
                "is_native": True
            }
        elif vp9_st:
            est_sz = int(vp9_st["total_filesize"] * 1.05)
            codecs_dict["compatible"] = {
                "codec": "H.264 (Transcode)",
                "format_id": vp9_st["format_id"],
                "filesize": est_sz,
                "filesize_formatted": format_bytes(est_sz),
                "fps": vp9_st["fps"],
                "is_native": False
            }
        else:
            codecs_dict["compatible"] = {
                "codec": "H.264",
                "format_id": best_overall["format_id"],
                "filesize": best_overall["total_filesize"],
                "filesize_formatted": format_bytes(best_overall["total_filesize"]),
                "fps": best_overall["fps"],
                "is_native": True
            }

        # 2. Original / Source (AV1 preferred for modern bandwidth efficiency, then VP9, then H.264)
        if av1_st:
            codecs_dict["original"] = {
                "codec": "AV1",
                "format_id": av1_st["format_id"],
                "filesize": av1_st["total_filesize"],
                "filesize_formatted": format_bytes(av1_st["total_filesize"]),
                "fps": av1_st["fps"],
                "is_native": True
            }
        elif vp9_st:
            codecs_dict["original"] = {
                "codec": "VP9",
                "format_id": vp9_st["format_id"],
                "filesize": vp9_st["total_filesize"],
                "filesize_formatted": format_bytes(vp9_st["total_filesize"]),
                "fps": vp9_st["fps"],
                "is_native": True
            }
        else:
            codecs_dict["original"] = {
                "codec": codecs_dict["compatible"]["codec"],
                "format_id": codecs_dict["compatible"]["format_id"],
                "filesize": codecs_dict["compatible"]["filesize"],
                "filesize_formatted": codecs_dict["compatible"]["filesize_formatted"],
                "fps": codecs_dict["compatible"]["fps"],
                "is_native": True
            }

        # 3. ProRes 422 (Source stream download size that will be transcoded)
        prores_src_stream = vp9_st or h264_st or av1_st or best_overall
        prores_fps = prores_src_stream.get("fps", 30)
        prores_dl_bytes = prores_src_stream["total_filesize"]
        prores_src_fid = prores_src_stream["format_id"]

        codecs_dict["prores"] = {
            "codec": "ProRes 422",
            "format_id": prores_src_fid,
            "filesize": prores_dl_bytes,
            "filesize_formatted": format_bytes(prores_dl_bytes),
            "fps": prores_fps,
            "is_transcode": True
        }

        # Default representation uses "compatible"
        def_var = codecs_dict["compatible"]
        badge_text = meta["badge"]
        if def_var["fps"] and def_var["fps"] >= 50:
            badge_text += f" {int(def_var['fps'])}fps"

        video_resolutions[fmt_key] = {
            "height": display_h,
            "label": meta["label"],
            "badge": badge_text,
            "codec": def_var["codec"],
            "fps": def_var["fps"],
            "tbr": best_overall.get("tbr", 0),
            "has_real_size": best_overall.get("has_real_size", False),
            "filesize": def_var["filesize"],
            "filesize_formatted": def_var["filesize_formatted"],
            "format_id": def_var["format_id"],
            "container": "mp4",
            "codecs": codecs_dict
        }

    # Sort resolutions descending
    sorted_resolutions = sorted(video_resolutions.values(), key=lambda x: x["height"], reverse=True)

    # Fallback if no specific video resolution extracted (e.g. single direct stream)
    if not sorted_resolutions:
        raw_fs = info.get("filesize") or info.get("filesize_approx") or 0
        sorted_resolutions = [{
            "height": 720,
            "label": "Original Stream",
            "badge": "Web Stream",
            "codec": "H.264 / AAC",
            "fps": 30,
            "tbr": 0,
            "is_av1": False,
            "has_real_size": bool(raw_fs),
            "filesize": raw_fs,
            "filesize_formatted": format_bytes(raw_fs) if raw_fs else "Stream Direct",
            "format_id": "best",
            "container": "mp4",
            "codecs": {
                "compatible": {"codec": "H.264", "format_id": "best", "filesize": raw_fs, "filesize_formatted": format_bytes(raw_fs) if raw_fs else "Stream Direct", "fps": 30},
                "original": {"codec": "Original", "format_id": "best", "filesize": raw_fs, "filesize_formatted": format_bytes(raw_fs) if raw_fs else "Stream Direct", "fps": 30},
                "prores": {"codec": "ProRes 422", "format_id": "best", "filesize": raw_fs, "filesize_formatted": format_bytes(raw_fs) if raw_fs else "Stream Direct", "fps": 30, "is_transcode": True}
            }
        }]

    # Audio presets with accurate duration-based filesize
    est_mp3_320 = int((320 * 1000 / 8) * duration_sec) if duration_sec else (best_audio_size * 2)
    est_mp3_192 = int((192 * 1000 / 8) * duration_sec) if duration_sec else int(best_audio_size * 1.3)
    est_m4a = best_audio_size

    audio_presets = [
        {
            "format": "mp3",
            "quality": "320",
            "label": "MP3 (320 kbps High Quality)",
            "badge": "Studio Audio",
            "filesize": est_mp3_320,
            "filesize_formatted": format_bytes(est_mp3_320)
        },
        {
            "format": "mp3",
            "quality": "192",
            "label": "MP3 (192 kbps Standard)",
            "badge": "Standard Audio",
            "filesize": est_mp3_192,
            "filesize_formatted": format_bytes(est_mp3_192)
        },
        {
            "format": "m4a",
            "quality": "original",
            "label": "M4A (Original AAC 44.1kHz)",
            "badge": "Lossless Container",
            "filesize": est_m4a,
            "filesize_formatted": format_bytes(est_m4a)
        }
    ]

    # Robust thumbnail candidates with fallback chain
    candidate_thumbnails = []
    raw_thumb = (info.get("thumbnail") or "").strip()
    v_id = (info.get("id") or "").strip()

    if is_yt and v_id:
        if raw_thumb and raw_thumb not in candidate_thumbnails:
            candidate_thumbnails.append(raw_thumb)
        candidate_thumbnails.append(f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg")
        candidate_thumbnails.append(f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg")
        candidate_thumbnails.append(f"https://i.ytimg.com/vi/{v_id}/mqdefault.jpg")
        candidate_thumbnails.append(f"https://i.ytimg.com/vi/{v_id}/default.jpg")
    else:
        if raw_thumb:
            candidate_thumbnails.append(raw_thumb)
        for t_item in reversed(info.get("thumbnails") or []):
            t_url = t_item.get("url")
            if t_url and t_url not in candidate_thumbnails:
                candidate_thumbnails.append(t_url)

    best_thumbnail = candidate_thumbnails[0] if candidate_thumbnails else raw_thumb

    # Determine uploader display
    uploader_name = info.get("uploader") or info.get("extractor_key") or info.get("extractor")
    if not uploader_name:
        uploader_name = "YouTube" if is_yt else ("HLS Stream" if is_stream else "Web Stream")

    raw_title = info.get("title") or ""
    dummy_words = ["index", "master", "playlist", "manifest", "stream", "video", "unknown", "chunk", "fragment"]
    is_raw_dummy = (
        not raw_title or
        any(raw_title.lower().startswith(d) for d in dummy_words) or
        any(d in raw_title.lower() for d in ["index-", "master-", "playlist-", "f1.m3u8", "index_"])
    )

    if stream_title and (is_raw_dummy or len(stream_title) > len(raw_title)):
        display_title = clean_stream_title(stream_title)
    else:
        display_title = clean_stream_title(raw_title) if not is_raw_dummy else (clean_stream_title(stream_title) or "Video")

    # Find progressive & direct streams for preview across full spectrum:
    # 4320p (8K), 2160p (4K), 1440p (2K), 1080p (FHD), 720p (HD), 480p (SD), 360p (Fast Scrub), 240p (Low), 144p (Min)
    preview_stream_url = ""
    preview_options = []
    seen_heights = set()

    # Collect all playable video formats with direct URLs
    video_direct = [
        f for f in formats 
        if f.get("url") and f.get("vcodec") != "none" and f.get("height")
    ]

    # Target standard heights plus any existing distinct heights
    standard_heights = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
    found_heights = set(f.get("height") for f in video_direct if f.get("height"))
    all_target_heights = sorted(list(set(standard_heights) | found_heights), reverse=True)

    tag_map = {
        4320: "8K",
        2160: "4K",
        1440: "2K",
        1080: "FHD",
        720: "HD",
        480: "SD",
        360: "Fast Scrub",
        240: "Low",
        144: "Min"
    }

    for target_h in all_target_heights:
        matches = [f for f in video_direct if f.get("height") == target_h and f.get("url")]
        if matches:
            # Prioritize: 1. Audio present (progressive) 2. MP4 container 3. AVC/H.264 4. Higher bitrate
            def _format_priority(fmt):
                has_audio = 1 if fmt.get("acodec") != "none" else 0
                is_mp4 = 1 if fmt.get("ext") == "mp4" else 0
                vc = (fmt.get("vcodec") or "").lower()
                is_h264 = 1 if ("avc" in vc or "h264" in vc) else 0
                bitrate = fmt.get("tbr") or fmt.get("vbr") or 0
                return (has_audio, is_mp4, is_h264, bitrate)

            matches.sort(key=_format_priority, reverse=True)
            best_fmt = matches[0]

            tag = tag_map.get(target_h, "")
            label = f"{target_h}p ({tag})" if tag else f"{target_h}p"
            preview_options.append({
                "height": target_h,
                "label": label,
                "url": best_fmt.get("url"),
                "format_id": best_fmt.get("format_id"),
                "has_audio": best_fmt.get("acodec") != "none"
            })
            seen_heights.add(target_h)

    # Sort descending by height (Max to 144p Low)
    preview_options.sort(key=lambda x: (x.get("height") or 0), reverse=True)

    # Determine default stream: 360p (Fast Scrub) or format 18 for instant bufferless scrubbing
    p360 = [p for p in preview_options if p["height"] == 360]
    p480 = [p for p in preview_options if p["height"] == 480]
    if p360:
        preview_stream_url = p360[0]["url"]
    elif p480:
        preview_stream_url = p480[0]["url"]
    elif preview_options:
        preview_stream_url = preview_options[0].get("url") or ""
    else:
        preview_stream_url = info.get("url") or ""

    return {
        "type": "video",
        "id": info.get("id"),
        "title": display_title,
        "uploader": uploader_name,
        "duration": format_duration(duration_sec) if duration_sec else "Live / Stream",
        "duration_seconds": duration_sec,
        "views": f"{info.get('view_count', 0):,}" if info.get('view_count') else "N/A",
        "thumbnail": best_thumbnail,
        "thumbnail_candidates": candidate_thumbnails,
        "webpage_url": info.get("webpage_url", url),
        "source_type": "youtube" if is_yt else ("hls" if is_stream else "web"),
        "is_stream": not is_yt,
        "preview_url": preview_stream_url,
        "preview_options": preview_options,
        "resolutions": sorted_resolutions,
        "audio_presets": audio_presets,
        "raw_formats": formats
    }


def extract_video_id(url: str) -> str:
    """Extract 11-char YouTube video ID from URL if present."""
    if not url or not isinstance(url, str):
        return ""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        if "youtu.be" in netloc:
            parts = parsed.path.strip("/").split("/")
            if parts and len(parts[0]) == 11:
                return parts[0]
        qs = parse_qs(parsed.query)
        if "v" in qs and qs["v"] and len(qs["v"][0]) == 11:
            return qs["v"][0]
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) >= 2 and path_parts[0] in ("shorts", "live", "embed", "v") and len(path_parts[1]) == 11:
            return path_parts[1]
    except Exception:
        pass
    return ""


def is_pure_playlist_url(url: str) -> bool:
    """Returns True if the URL points strictly to a playlist collection without an individual video ID."""
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        qs = parse_qs(parsed.query)

        if any(h in netloc for h in ("youtube.com", "youtu.be")):
            has_vid = bool(extract_video_id(url))
            has_list = "list" in qs
            if has_list and not has_vid:
                return True
            if "playlist" in path and not has_vid:
                return True
            return False

        if "soundcloud.com" in netloc and "/sets/" in path:
            return True
        if "/collection/" in path or "/series/" in path:
            return True
    except Exception:
        pass
    return False


def is_video_in_playlist_url(url: str) -> bool:
    """Returns True if the URL points to a specific video that is embedded inside a playlist queue."""
    if not url or not isinstance(url, str):
        return False
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url.strip())
        netloc = parsed.netloc.lower()
        qs = parse_qs(parsed.query)

        if any(h in netloc for h in ("youtube.com", "youtu.be")):
            has_vid = bool(extract_video_id(url))
            has_list = "list" in qs
            return bool(has_vid and has_list)
    except Exception:
        pass
    return False


def is_playlist_url(url: str) -> bool:
    """Returns True if the URL points to a playlist, series, or collection (pure or video-in-playlist)."""
    return is_pure_playlist_url(url) or is_video_in_playlist_url(url)


def parse_playlist(url: str, custom_headers: dict = None, max_items: int = 150) -> dict:
    """Quickly extracts playlist metadata and item list without downloading manifests."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': False,
        'extract_flat': 'in_playlist',
        'skip_download': True,
        'playlistend': max_items,
    }
    opts.update(get_ydl_cookie_opts())
    if custom_headers:
        opts['http_headers'] = custom_headers

    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        opts['impersonate'] = ImpersonateTarget.from_str('chrome')
        opts['extractor_args'] = {'generic': {'impersonate': ['chrome']}}
    except Exception:
        pass

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Failed to extract playlist metadata from URL.")

    entries_raw = list(info.get("entries") or [])
    clean_entries = []
    for item in entries_raw:
        if not item:
            continue
        item_id = item.get("id")
        item_url = item.get("url") or item.get("webpage_url")
        if item_url and not item_url.startswith("http"):
            item_url = f"https://www.youtube.com/watch?v={item_url}"
        elif not item_url and item_id:
            item_url = f"https://www.youtube.com/watch?v={item_id}"

        duration_sec = item.get("duration") or 0
        thumbs = item.get("thumbnails") or []
        thumb_url = thumbs[-1].get("url") if thumbs else (item.get("thumbnail") or "")

        clean_entries.append({
            "id": item_id,
            "title": item.get("title") or "Untitled Media",
            "url": item_url,
            "duration": format_duration(duration_sec) if duration_sec else "--:--",
            "duration_seconds": duration_sec,
            "uploader": item.get("uploader") or item.get("channel") or "",
            "thumbnail": thumb_url
        })

    return {
        "type": "playlist",
        "id": info.get("id"),
        "title": info.get("title") or "Playlist",
        "uploader": info.get("uploader") or info.get("channel") or "Various Creators",
        "count": len(clean_entries),
        "entries": clean_entries
    }

