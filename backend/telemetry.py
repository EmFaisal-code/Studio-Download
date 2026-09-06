import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger("studio_download.telemetry")

SUPABASE_URL = "https://movecexnjyeaipkklijv.supabase.co/rest/v1/pixora_users"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1vdmVjZXhuanllYWlwa2tsaWp2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY4OTYzMDUsImV4cCI6MjA5MjQ3MjMwNX0.LdytPpEvTDapFfh_OxxOwSf3i8af4XVSe9mdy3QDkhE"

def _get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def sync_user_to_cloud(profile: dict) -> dict:
    """
    Synchronizes the local user identity to the cloud database (Supabase).
    Runs safely without blocking the application.
    """
    if not profile or not profile.get("username"):
        return {"status": "skipped", "reason": "No username provided"}

    raw_username = profile.get("username", "").strip()
    username = f"@{raw_username}" if not raw_username.startswith("@") else raw_username
    role = profile.get("role") or "Video Editor (Adobe / DaVinci / dll)"
    version = profile.get("app_version") or "1.0"
    now_iso = datetime.now(timezone.utc).isoformat()

    encoded_username = urllib.parse.quote(username)
    check_url = f"{SUPABASE_URL}?username=eq.{encoded_username}&select=id,is_banned"

    try:
        # 1. Check if user already exists
        check_req = urllib.request.Request(check_url, headers=_get_headers(), method="GET")
        with urllib.request.urlopen(check_req, timeout=6) as resp:
            existing = json.loads(resp.read().decode("utf-8"))

        if existing and len(existing) > 0:
            user_id = existing[0].get("id")
            is_banned = existing[0].get("is_banned", False)
            patch_url = f"{SUPABASE_URL}?id=eq.{user_id}"
            payload = json.dumps({
                "version_used": version,
                "password_hint": role,
                "last_seen": now_iso,
                "updated_at": now_iso
            }).encode("utf-8")
            patch_req = urllib.request.Request(patch_url, data=payload, headers=_get_headers(), method="PATCH")
            with urllib.request.urlopen(patch_req, timeout=6) as patch_resp:
                return {"status": "updated", "is_banned": is_banned}
        else:
            # 2. Insert new user record
            payload = json.dumps({
                "username": username,
                "password": "",
                "version_used": version,
                "password_hint": role,
                "last_seen": now_iso,
                "created_at": now_iso,
                "updated_at": now_iso,
                "is_banned": False
            }).encode("utf-8")
            post_req = urllib.request.Request(SUPABASE_URL, data=payload, headers=_get_headers(), method="POST")
            with urllib.request.urlopen(post_req, timeout=6) as post_resp:
                return {"status": "created", "is_banned": False}
    except Exception as e:
        logger.debug(f"[Telemetry] Cloud sync skipped: {e}")
        return {"status": "error", "error": str(e)}
