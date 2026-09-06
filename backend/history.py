import json
import os
import time
from pathlib import Path
from backend.config import get_app_dir

BASE_DIR = get_app_dir()
HISTORY_FILE = BASE_DIR / "history.json"

def get_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                fp = item.get("filepath")
                item["file_exists"] = bool(fp and os.path.exists(fp))
            return data
    except Exception:
        return []

def save_history(history_list):
    try:
        # Don't persist transient file_exists key
        cleaned_list = []
        for item in history_list:
            c = item.copy()
            c.pop("file_exists", None)
            cleaned_list.append(c)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(cleaned_list, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def add_history_entry(entry):
    history = get_history()
    # Prepend newest
    history.insert(0, entry)
    # Keep last 100 entries
    history = history[:100]
    save_history(history)

def update_history_entry(task_id, updates):
    history = get_history()
    updated = False
    for item in history:
        if item.get("id") == task_id:
            item.update(updates)
            updated = True
            break
    if updated:
        save_history(history)

def delete_history_entry(task_id: str, delete_file: bool = False):
    history = get_history()
    deleted_item = None
    new_history = []
    file_deleted = False

    for item in history:
        if item.get("id") == task_id:
            deleted_item = item
        else:
            new_history.append(item)

    if deleted_item and delete_file:
        fp = deleted_item.get("filepath")
        if fp and os.path.exists(fp):
            try:
                os.remove(fp)
                file_deleted = True
            except Exception as e:
                print(f"Error removing physical file {fp}: {e}")

    save_history(new_history)
    return {"status": "deleted", "file_deleted": file_deleted}

def clear_all_history(delete_files: bool = False):
    history = get_history()
    deleted_count = 0
    if delete_files:
        for item in history:
            fp = item.get("filepath")
            if fp and os.path.exists(fp):
                try:
                    os.remove(fp)
                    deleted_count += 1
                except Exception as e:
                    print(f"Error removing physical file {fp}: {e}")
    save_history([])
    return {"status": "cleared", "deleted_files_count": deleted_count}
