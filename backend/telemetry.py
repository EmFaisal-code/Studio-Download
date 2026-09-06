import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger("studio_download.telemetry")

SUPABASE_BASE = "https://ygelxeqeuwadutzwyebe.supabase.co"
SUPABASE_URL = f"{SUPABASE_BASE}/rest/v1/studio_users"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlnZWx4ZXFldXdhZHV0end5ZWJlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg3MTg2NDMsImV4cCI6MjEwNDI5NDY0M30.X_fMFljw4gPnbzezerEpfemeq3juZ9tIuKKCeh2ZUuI"

def _get_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def sync_user_to_cloud(profile: dict) -> dict:
    """
    Synchronizes the local user identity to the new Studio Download Supabase database.
    Runs safely in a non-blocking background thread.
    """
    if not profile or not profile.get("username"):
        return {"status": "skipped", "reason": "No username provided"}

    raw_username = profile.get("username", "").strip()
    username = f"@{raw_username}" if not raw_username.startswith("@") else raw_username
    role = profile.get("role") or "Video Editor (Universal)"
    contact = profile.get("contact") or ""
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
                "role": role,
                "contact": contact,
                "version_used": version,
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
                "role": role,
                "contact": contact,
                "version_used": version,
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

def fetch_cloud_config() -> dict:
    """
    Fetches the remote system config from Supabase studio_config.
    Returns latest_version, min_version, download_url, update_message, announcement, maintenance_mode, etc.
    """
    config_url = f"{SUPABASE_BASE}/rest/v1/studio_config?select=key,value,enabled"
    try:
        req = urllib.request.Request(config_url, headers=_get_headers(), method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
            cfg = {}
            for r in rows:
                cfg[r["key"]] = {
                    "value": r.get("value"),
                    "enabled": r.get("enabled", True)
                }
            return cfg
    except Exception as e:
        logger.debug(f"[Telemetry] fetch_cloud_config failed: {e}")
        return {}
