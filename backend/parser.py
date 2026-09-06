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

def format_bytes(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "Estimasi N/A"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 1)
    return f"{s} {size_name[i]}"

def is_youtube_url(url: str) -> bool:
    return bool(re.search(r'(?:youtube\.com|youtu\.be)', url, re.IGNORECASE))

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
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
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

    is_yt = is_youtube_url(url)
    is_stream = is_stream_url(url)

    info = None
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            raw_err = str(e)
            clean_err = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', raw_err).strip()
            if is_stream:
                # Do not crash on stream URLs (e.g. Cloudflare protected CDNs)
                # Fall back gracefully to direct stream metadata
                info = None
            else:
                if "Failed to decrypt with DPAPI" in clean_err or "DPAPI" in clean_err:
                    raise ValueError("CHROME_DPAPI_BLOCKED: Google Chrome versi terbaru di Windows memblokir pembacaan cookies langsung dari database (App-Bound DPAPI Encryption). Solusi: Gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG dengan ekstensi 'Get cookies.txt LOCALLY'.")
                if "Could not copy" in clean_err and "cookie database" in clean_err:
                    raise ValueError("BROWSER_LOCKED: Database cookie browser terkunci oleh Windows karena browser sedang dibuka/berjalan. Tutup browser sepenuhnya terlebih dahulu, ATAU gunakan opsi 'AUTO // File cookies.txt' di menu CONFIG agar browser tidak perlu ditutup.")
                if "Sign in to confirm you're not a bot" in clean_err or "not a bot" in clean_err:
                    raise ValueError("BOT_CHECK_REQUIRED: YouTube mewajibkan verifikasi autentikasi (Sign in to confirm you're not a bot). Silakan gunakan file cookies.txt atau impor cookie browser di menu CONFIG.")
                if "Private video" in clean_err:
                    raise ValueError("Video ini bersifat privat (Private Video). Diperlukan login akun yang memiliki izin akses.")
                if "Video unavailable" in clean_err:
                    raise ValueError("Video tidak tersedia atau telah dihapus.")
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

    # Group video formats by height
    video_resolutions = {}
    for f in formats:
        h = f.get("height")
        vcodec = f.get("vcodec") or ""
        ext = f.get("ext") or ""

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

        # For non-YT streams without explicit height, assign an estimated height or fallback
        fmt_key = h if h else (f.get("tbr") or f.get("format_id") or 720)
        display_h = h if h else 720

        fps = f.get("fps") or 30
        tbr = f.get("tbr") or f.get("vbr") or 0

        # Calculate accurate filesize
        fs = f.get("filesize") or f.get("filesize_approx") or 0
        if not fs and tbr and duration_sec:
            fs = int((tbr * 1000 / 8) * duration_sec)

        total_filesize = fs
        if f.get("acodec") == "none" and best_audio_size:
            total_filesize += best_audio_size

        # Badge text
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

        if fps and fps >= 50:
            badge += f" {int(fps)}fps"

        # Codec friendly name
        codec_name = "H.264"
        if "av01" in vcodec or "av1" in vcodec:
            codec_name = "AV1"
        elif "vp09" in vcodec or "vp9" in vcodec:
            codec_name = "VP9"
        elif "hls" in (f.get("protocol") or ""):
            codec_name = "HLS Stream"

        # Prioritize VP9/H.264 over AV1 for default representation, or pick highest bitrate
        is_av1 = "av01" in vcodec
        current_res = video_resolutions.get(fmt_key)

        should_replace = False
        if not current_res:
            should_replace = True
        else:
            curr_is_av1 = "AV1" in current_res["codec"]
            # Prefer non-AV1 (VP9/H.264) for compatibility
            if curr_is_av1 and not is_av1:
                should_replace = True
            elif not curr_is_av1 and is_av1:
                should_replace = False
            elif tbr > current_res["tbr"]:
                should_replace = True

        if should_replace:
            video_resolutions[fmt_key] = {
                "height": display_h,
                "label": f"{display_h}p" if h else (f.get("format_note") or "Original"),
                "badge": badge,
                "codec": codec_name,
                "fps": fps,
                "tbr": tbr,
                "filesize": total_filesize,
                "filesize_formatted": format_bytes(total_filesize) if total_filesize else "Stream HLS",
                "format_id": f.get("format_id"),
                "container": "mp4"
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
            "filesize": raw_fs,
            "filesize_formatted": format_bytes(raw_fs) if raw_fs else "Stream Direct",
            "format_id": "best",
            "container": "mp4"
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
            "filesize_formatted": format_bytes(est_mp3_320)
        },
        {
            "format": "mp3",
            "quality": "192",
            "label": "MP3 (192 kbps Standard)",
            "badge": "Standard Audio",
            "filesize_formatted": format_bytes(est_mp3_192)
        },
        {
            "format": "m4a",
            "quality": "original",
            "label": "M4A (Original AAC 44.1kHz)",
            "badge": "Lossless Container",
            "filesize_formatted": format_bytes(est_m4a)
        }
    ]

    # Best thumbnail
    thumbnails = info.get("thumbnails", [])
    best_thumbnail = info.get("thumbnail") or ""
    if thumbnails:
        best_thumbnail = thumbnails[-1].get("url", best_thumbnail)

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

    return {
        "type": "video",
        "id": info.get("id"),
        "title": display_title,
        "uploader": uploader_name,
        "duration": format_duration(duration_sec) if duration_sec else "Live / Stream",
        "duration_seconds": duration_sec,
        "views": f"{info.get('view_count', 0):,}" if info.get('view_count') else "N/A",
        "thumbnail": best_thumbnail,
        "webpage_url": info.get("webpage_url", url),
        "source_type": "youtube" if is_yt else ("hls" if is_stream else "web"),
        "is_stream": not is_yt,
        "resolutions": sorted_resolutions,
        "audio_presets": audio_presets
    }
