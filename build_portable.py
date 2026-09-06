import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 60)
    print("   BUILDING STUDIO DOWNLOAD PORTABLE DESKTOP SOFTWARE")
    print("=" * 60)

    # 1. Check system ffmpeg
    ffmpeg_bin = Path(r"C:\ffmpeg-master-latest-win64-gpl-shared\bin")
    ffmpeg_src = ffmpeg_bin / "ffmpeg.exe"
    ffprobe_src = ffmpeg_bin / "ffprobe.exe"
    if not ffmpeg_src.exists():
        # Fallback to PATH
        p = shutil.which("ffmpeg")
        if p:
            ffmpeg_src = Path(p)
            ffprobe_src = ffmpeg_src.parent / "ffprobe.exe"

    print(f"[*] FFmpeg source: {ffmpeg_src}")

    # 2. Prepare PyInstaller command
    frontend_dir = BASE_DIR / "frontend"
    
    hidden_imports = [
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespans",
        "uvicorn.lifespans.on",
        "curl_cffi",
        "curl_cffi.requests",
        "yt_dlp",
        "webview",
        "webview.platforms.winforms",
        "clr",
        "pythonnet",
        "fastapi",
        "starlette",
        "pydantic",
        "backend",
        "backend.app",
        "backend.config",
        "backend.downloader",
        "backend.history",
        "backend.parser"
    ]

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=StudioDownload",
        "--noconsole",
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--icon={BASE_DIR / 'app_icon.ico'}",
        f"--add-data={frontend_dir};frontend",
        f"--add-data={BASE_DIR / 'app_icon.ico'};.",
    ]

    for h in hidden_imports:
        cmd.extend(["--hidden-import", h])

    cmd.append(str(BASE_DIR / "main.py"))

    print("\n[*] Menjalankan PyInstaller...")
    ret = subprocess.run(cmd, cwd=str(BASE_DIR))
    if ret.returncode != 0:
        print(f"[!] Build gagal dengan returncode {ret.returncode}")
        return False

    dist_dir = BASE_DIR / "dist" / "StudioDownload"
    print(f"\n[+] Build selesai di: {dist_dir}")

    # Copy app_icon.ico to portable root directory
    if (BASE_DIR / "app_icon.ico").exists():
        print("[*] Menyalin app_icon.ico ke direktori portable...")
        shutil.copy2(BASE_DIR / "app_icon.ico", dist_dir / "app_icon.ico")

    # 3. Copy FFmpeg binaries into the portable directory
    if ffmpeg_src.exists():
        print("[*] Menyalin ffmpeg.exe ke direktori portable...")
        shutil.copy2(ffmpeg_src, dist_dir / "ffmpeg.exe")
    if ffprobe_src.exists():
        print("[*] Menyalin ffprobe.exe ke direktori portable...")
        shutil.copy2(ffprobe_src, dist_dir / "ffprobe.exe")

    # 4. Copy FFmpeg DLLs if needed (for shared builds)
    if ffmpeg_bin.exists():
        dll_count = 0
        for dll in ffmpeg_bin.glob("*.dll"):
            shutil.copy2(dll, dist_dir / dll.name)
            dll_count += 1
        if dll_count > 0:
            print(f"[*] Menyalin {dll_count} library DLL FFmpeg ke direktori portable...")

    # 5. Copy Companion Extension to portable directory
    ext_src = BASE_DIR / "extra"
    if not ext_src.exists():
        ext_src = BASE_DIR / "Extension"
    ext_dest = dist_dir / "Extension"
    ext_dest_extra = dist_dir / "extra"
    if ext_src.exists():
        print("[*] Menyalin Studio Download Extension ke direktori portable...")
        if ext_dest.exists():
            shutil.rmtree(ext_dest)
        shutil.copytree(ext_src, ext_dest)
        if ext_dest_extra.exists():
            shutil.rmtree(ext_dest_extra)
        shutil.copytree(ext_src, ext_dest_extra)

    # 6. Create Portable README
    readme_path = dist_dir / "README.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "STUDIO DOWNLOAD - Portable Desktop Edition v1.0\n"
            "================================================\n\n"
            "Made by @em.n.ef: https://www.tiktok.com/@em.n.ef\n"
            "Dukungan / Donasi: https://sociabuzz.com/emef/tribe\n"
            "GitHub Releases & Update: https://github.com/EmFaisal-code/Studio-Download/releases\n\n"
            "Aplikasi ini bersifat 100% PORTABLE tanpa perlu install:\n"
            "1. Cukup double-click 'StudioDownload.exe' untuk menjalankan software.\n"
            "2. FFmpeg sudah terintegrasi langsung di folder ini.\n"
            "3. Riwayat unduhan (history.json) dan pengaturan (settings.json) tersimpan otomatis di folder ini.\n"
            "4. Ekstensi browser ada di folder 'Extension' (atau 'extra'). Pasang di Chrome via chrome://extensions (Developer Mode -> Load Unpacked).\n"
            "5. Ekstensi browser otomatis terhubung ke aplikasi saat aplikasi sedang terbuka.\n"
            "6. Untuk mengecek pembaruan versi terbaru, kunjungi: https://github.com/EmFaisal-code/Studio-Download/releases\n"
        )

    print("=" * 60)
    print("   SUKSES! StudioDownload.exe Portable siap digunakan!")
    print(f"   Lokasi: {dist_dir / 'StudioDownload.exe'}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    build()
