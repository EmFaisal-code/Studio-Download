import os
import sys
import time
import shutil
import logging
import threading
import subprocess
from pathlib import Path
from backend.config import get_app_dir

logger = logging.getLogger("studio_download.conversion_guard")

# Minimum safe disk headroom to leave on the system drive (avoid Windows system freezing)
MIN_SYSTEM_HEADROOM_BYTES = 300 * 1024 * 1024  # 300 MB
DEFAULT_SAFETY_BUFFER_BYTES = 200 * 1024 * 1024  # 200 MB

# Thread-safe lock for audit log and active records
_guard_lock = threading.RLock()
_low_disk_records: dict[str, dict] = {}
_audit_log_path: Path | None = None
_watcher_thread: threading.Thread | None = None
_watcher_running = False

def get_audit_log_path() -> Path:
    global _audit_log_path
    if _audit_log_path is None:
        _audit_log_path = get_app_dir() / "conversion_audit.log"
    return _audit_log_path

def log_conversion_audit(task_id: str, event: str, message: str, details: dict = None):
    """
    Appends a timestamped audit record for conversion suspension, resumption,
    space checks, and completions to conversion_audit.log and standard logger.
    """
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    det_str = ""
    if details:
        items = [f"{k}={v}" for k, v in details.items() if v is not None]
        if items:
            det_str = " | " + " | ".join(items)

    log_line = f"[{now_str}] [TASK:{task_id}] [EVENT:{event}] {message}{det_str}\n"

    with _guard_lock:
        try:
            log_file = get_audit_log_path()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
        except Exception as e:
            logger.debug(f"Failed to write to conversion_audit.log: {e}")

    logger.info(f"[{event}] (Task {task_id}): {message}")

def get_path_disk_free(path: str) -> int:
    """Returns available free disk space in bytes for the filesystem containing path."""
    if not path:
        return 0
    try:
        p = Path(path).resolve()
        while not p.exists() and p != p.parent:
            p = p.parent
        return shutil.disk_usage(str(p)).free
    except Exception:
        try:
            drive = os.path.splitdrive(path)[0]
            if drive:
                return shutil.disk_usage(drive + "\\").free
        except Exception:
            pass
    return 0

def get_drive_name(path: str) -> str:
    """Returns the drive letter or root path for human-readable reporting."""
    if not path:
        return "System Drive"
    try:
        dr = os.path.splitdrive(os.path.abspath(path))[0]
        if dr:
            return f"Drive {dr.upper()}"
    except Exception:
        pass
    return "Drive Penyimpanan"

def format_bytes_human(n: int) -> str:
    """Formats bytes to human-readable string (KB, MB, GB)."""
    if not n or n <= 0:
        return "0 MB"
    if n >= 1024**3:
        return f"{n / (1024**3):.2f} GB"
    if n >= 1024**2:
        return f"{n / (1024**2):.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"

def suspend_process(pid: int) -> bool:
    """Suspends the execution of a process at the OS kernel level without killing it."""
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
            if handle:
                res = ctypes.windll.ntdll.NtSuspendProcess(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                return res == 0
        else:
            import signal
            os.kill(pid, signal.SIGSTOP)
            return True
    except Exception as e:
        logger.debug(f"Error suspending PID {pid}: {e}")
        return False

def resume_process(pid: int) -> bool:
    """Resumes a previously suspended process so it continues executing seamlessly."""
    if not pid:
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, pid)
            if handle:
                res = ctypes.windll.ntdll.NtResumeProcess(handle)
                ctypes.windll.kernel32.CloseHandle(handle)
                return res == 0
        else:
            import signal
            os.kill(pid, signal.SIGCONT)
            return True
    except Exception as e:
        logger.debug(f"Error resuming PID {pid}: {e}")
        return False

def register_low_disk_paused_conversion(
    task_id: str,
    target_dir: str,
    required_bytes: int,
    proc: subprocess.Popen | None,
    checkpoint: dict,
    resume_callback: callable = None
) -> threading.Event:
    """
    Registers a conversion task that was stopped because of low disk space.
    Returns a threading.Event that will be set when disk space becomes sufficient.
    """
    resume_event = threading.Event()
    drive = get_drive_name(target_dir)

    record = {
        "task_id": task_id,
        "target_dir": target_dir,
        "drive": drive,
        "required_bytes": required_bytes,
        "proc": proc,
        "pid": proc.pid if proc else None,
        "checkpoint": checkpoint,
        "resume_event": resume_event,
        "resume_callback": resume_callback,
        "paused_at": time.time()
    }

    with _guard_lock:
        _low_disk_records[task_id] = record

    ensure_watcher_started()
    return resume_event

def unregister_low_disk_paused_conversion(task_id: str):
    """Removes a task from low disk monitoring once resumed or cancelled."""
    with _guard_lock:
        _low_disk_records.pop(task_id, None)

def get_low_disk_record(task_id: str) -> dict | None:
    with _guard_lock:
        return _low_disk_records.get(task_id)

def trigger_resume_for_task(task_id: str, is_manual: bool = False) -> tuple[bool, str]:
    """
    Verifies if disk space is now sufficient for task_id, and if so,
    un-pauses the conversion process and signals the waiting thread.
    """
    with _guard_lock:
        record = _low_disk_records.get(task_id)
        if not record:
            return False, "Tugas tidak ditemukan dalam daftar antrean disk penuh."

        target_dir = record["target_dir"]
        required_bytes = record["required_bytes"]
        free_bytes = get_path_disk_free(target_dir)
        drive = record["drive"]

    # Minimum threshold: must cover remaining bytes plus minimum safety headroom
    needed_threshold = required_bytes + MIN_SYSTEM_HEADROOM_BYTES

    if free_bytes >= needed_threshold:
        with _guard_lock:
            # Re-fetch under lock
            record = _low_disk_records.pop(task_id, None)

        if record:
            # 1. Resume OS process if suspended
            proc = record.get("proc")
            pid = record.get("pid")
            if proc and pid:
                resume_process(pid)

            # 2. Fire callback if provided
            cb = record.get("resume_callback")
            if cb:
                try:
                    cb(task_id)
                except Exception as e:
                    logger.debug(f"Error in resume callback for {task_id}: {e}")

            # 3. Signal waiting thread
            ev = record.get("resume_event")
            if ev:
                ev.set()

            event_type = "MANUAL_RECHECK_SUCCESS" if is_manual else "AUTO_SPACE_RESTORED"
            msg = f"Ruang penyimpanan mencukupi ({format_bytes_human(free_bytes)}). Konversi dilanjutkan!"
            log_conversion_audit(
                task_id,
                event_type,
                msg,
                {
                    "drive": drive,
                    "free_bytes": format_bytes_human(free_bytes),
                    "required_bytes": format_bytes_human(required_bytes)
                }
            )
            return True, msg
    else:
        shortfall = needed_threshold - free_bytes
        msg = (
            f"Ruang penyimpanan {drive} masih kurang. "
            f"Tersisa {format_bytes_human(free_bytes)}, "
            f"dibutuhkan minimal {format_bytes_human(needed_threshold)} "
            f"(kurang {format_bytes_human(shortfall)})."
        )
        if is_manual:
            log_conversion_audit(
                task_id,
                "MANUAL_RECHECK_STILL_LOW",
                msg,
                {
                    "drive": drive,
                    "free_bytes": format_bytes_human(free_bytes),
                    "needed_threshold": format_bytes_human(needed_threshold)
                }
            )
        return False, msg

def _disk_watcher_loop():
    global _watcher_running
    logger.info("Continuous conversion disk space watcher started.")
    while _watcher_running:
        time.sleep(2.0)
        with _guard_lock:
            current_task_ids = list(_low_disk_records.keys())

        for task_id in current_task_ids:
            try:
                success, msg = trigger_resume_for_task(task_id, is_manual=False)
                if success:
                    logger.info(f"Auto-resumed task {task_id}: {msg}")
            except Exception as e:
                logger.debug(f"Error in disk watcher for task {task_id}: {e}")

def ensure_watcher_started():
    global _watcher_thread, _watcher_running
    with _guard_lock:
        if not _watcher_running or _watcher_thread is None or not _watcher_thread.is_alive():
            _watcher_running = True
            _watcher_thread = threading.Thread(target=_disk_watcher_loop, daemon=True, name="ConversionDiskWatcher")
            _watcher_thread.start()
