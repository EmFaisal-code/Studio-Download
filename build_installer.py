import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def find_iscc_compiler() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    for c in candidates:
        if c.exists():
            return c
    # Check PATH
    p = shutil.which("ISCC.exe") or shutil.which("iscc")
    if p:
        return Path(p)
    return None

def build():
    print("=" * 65)
    print("   BUILDING STUDIO DOWNLOAD WINDOWS INSTALLER (SETUP.EXE)")
    print("=" * 65)

    # 1. Locate Inno Setup Compiler
    iscc_path = find_iscc_compiler()
    if not iscc_path:
        print("[!] ERROR: Inno Setup 6 (ISCC.exe) tidak ditemukan di sistem!")
        sys.exit(1)
    print(f"[+] Inno Setup Compiler ditemukan di: {iscc_path}")

    # 2. Check system FFmpeg
    ffmpeg_bin = Path(r"C:\ffmpeg-master-latest-win64-gpl-shared\bin")
    ffmpeg_src = ffmpeg_bin / "ffmpeg.exe"
    ffprobe_src = ffmpeg_bin / "ffprobe.exe"
    if not ffmpeg_src.exists():
        p = shutil.which("ffmpeg")
        if p:
            ffmpeg_src = Path(p)
            ffprobe_src = ffmpeg_src.parent / "ffprobe.exe"

    print(f"[*] FFmpeg source: {ffmpeg_src}")
    if not ffmpeg_src.exists():
        print("[!] Warning: ffmpeg.exe tidak ditemukan di lokasi standar!")

    # 3. Clean and prepare directories
    dist_dir = BASE_DIR / "dist" / "StudioDownload"
    installer_out_dir = BASE_DIR / "dist" / "installer"
    installer_out_dir.mkdir(parents=True, exist_ok=True)

    frontend_dir = BASE_DIR / "frontend"
    ui_dir = BASE_DIR / "ui"
    backend_dir = BASE_DIR / "backend"

    hidden_imports = [
        "main_qt",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "ui",
        "ui.styles",
        "ui.main_window",
        "ui.components.title_bar",
        "ui.components.format_cards",
        "ui.components.task_item",
        "ui.dialogs.settings_dialog",
        "ui.dialogs.history_dialog",
        "ui.dialogs.profile_dialog",
        "ui.dialogs.who_are_you_dialog",
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
        "backend.parser",
        "backend.telemetry",
        "backend.i18n"
    ]

    pyinstaller_cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=StudioDownload",
        "--noconsole",
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--icon={BASE_DIR / 'app_icon.ico'}",
        f"--add-data={frontend_dir};frontend",
        f"--add-data={ui_dir};ui",
        f"--add-data={backend_dir};backend",
        f"--add-data={BASE_DIR / 'app_icon.ico'};.",
        "--collect-all=PySide6",
        "--collect-all=certifi",
        "--collect-all=curl_cffi",
    ]

    for h in hidden_imports:
        pyinstaller_cmd.extend(["--hidden-import", h])

    pyinstaller_cmd.append(str(BASE_DIR / "main.py"))

    print("\n[*] Menjalankan PyInstaller untuk membundel aplikasi...")
    ret = subprocess.run(pyinstaller_cmd, cwd=str(BASE_DIR))
    if ret.returncode != 0:
        print(f"[!] PyInstaller gagal dengan returncode {ret.returncode}")
        sys.exit(1)

    print(f"\n[+] Bundling aplikasi selesai di: {dist_dir}")

    # 4. Copy app_icon.ico to app root
    if (BASE_DIR / "app_icon.ico").exists():
        print("[*] Menyalin app_icon.ico...")
        shutil.copy2(BASE_DIR / "app_icon.ico", dist_dir / "app_icon.ico")
    if (BASE_DIR / "app_icon.png").exists():
        shutil.copy2(BASE_DIR / "app_icon.png", dist_dir / "app_icon.png")

    # 5. Ensure SSL cacert.pem is present
    try:
        import certifi
        ca_source = Path(certifi.where())
        if ca_source.exists():
            for target_ca in [
                dist_dir / "_internal" / "certifi" / "cacert.pem",
                dist_dir / "certifi" / "cacert.pem",
                dist_dir / "cacert.pem"
            ]:
                target_ca.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ca_source, target_ca)
            print("[*] Menyalin SSL certificate cacert.pem...")
    except Exception as e:
        print(f"[!] Gagal menyalin cacert.pem: {e}")

    # 6. Copy FFmpeg binaries & DLLs
    if ffmpeg_src.exists():
        print("[*] Menyalin ffmpeg.exe ke direktori aplikasi...")
        shutil.copy2(ffmpeg_src, dist_dir / "ffmpeg.exe")
    if ffprobe_src.exists():
        print("[*] Menyalin ffprobe.exe ke direktori aplikasi...")
        shutil.copy2(ffprobe_src, dist_dir / "ffprobe.exe")

    if ffmpeg_bin.exists():
        dll_count = 0
        for dll in ffmpeg_bin.glob("*.dll"):
            shutil.copy2(dll, dist_dir / dll.name)
            dll_count += 1
        if dll_count > 0:
            print(f"[*] Menyalin {dll_count} library DLL FFmpeg...")

    # 7. Copy Companion Extension
    ext_src = BASE_DIR / "extra"
    ext_dest = dist_dir / "Extension"
    if ext_src.exists():
        print("[*] Menyalin Companion Browser Extension...")
        if ext_dest.exists():
            shutil.rmtree(ext_dest)
        shutil.copytree(ext_src, ext_dest)
        old_extra = dist_dir / "extra"
        if old_extra.exists():
            shutil.rmtree(old_extra)

    # 8. Ensure clean default settings.json (English default)
    clean_settings = {
        "default_resolution": "best",
        "default_format": "mkv",
        "download_subtitles": False,
        "embed_thumbnail": True,
        "port": 8080,
        "cookie_source": "auto",
        "cookie_browser": "chrome",
        "cookie_file": "",
        "theme": "developer-zinc",
        "max_concurrent_downloads": 3,
        "download_speed_limit": 0,
        "language": "en",
        "user_profile": None
    }
    import json
    settings_target = dist_dir / "settings.json"
    with open(settings_target, "w", encoding="utf-8") as f:
        json.dump(clean_settings, f, indent=4)
    print("[*] Menulis default settings.json (Language: English)...")

    # 9. Clean any personal/sensitive files from dist
    for sensitive_file in ["cookies.txt", "history.json", "users.json", "server_error.log"]:
        sf = dist_dir / sensitive_file
        if sf.exists():
            sf.unlink()
            print(f"[!] Menghapus file pribadi: {sensitive_file}")

    # Create README.txt in application directory
    readme_path = dist_dir / "README.txt"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(
            "STUDIO DOWNLOAD - Universal Media Engine v1.0\n"
            "=============================================\n\n"
            "Made by @em.n.ef: https://www.tiktok.com/@em.n.ef\n"
            "Dukungan / Donasi: https://sociabuzz.com/emef/tribe\n"
            "GitHub Releases & Update: https://github.com/EmFaisal-code/Studio-Download/releases\n\n"
            "Fitur & Panduan Penggunaan:\n"
            "1. Jalankan StudioDownload.exe untuk membuka aplikasi.\n"
            "2. FFmpeg sudah terintegrasi langsung di folder ini.\n"
            "3. Riwayat unduhan (history.json) dan konfigurasi (settings.json) tersimpan otomatis.\n"
            "4. Ekstensi browser tersedia di folder 'Extension' (chrome://extensions -> Load Unpacked).\n"
            "5. Ekstensi otomatis menyinkronkan cookies YouTube & stream URL ke aplikasi.\n"
        )

    # 10. Generate Inno Setup Script (.iss)
    iss_content = f"""#define MyAppName "Studio Download"
#define MyAppVersion "1.0"
#define MyAppPublisher "EmFaisal"
#define MyAppURL "https://github.com/EmFaisal-code/Studio-Download"
#define MyAppExeName "StudioDownload.exe"

[Setup]
AppId={{{{E8F55C92-0C82-4113-BDEB-0839D6FF9A81}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}/releases
DefaultDirName={{autopf}}\\{{#MyAppName}}
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=commandline dialog
OutputDir={str(installer_out_dir)}
OutputBaseFilename=StudioDownload_v1.0_Setup
SetupIconFile={str(BASE_DIR / 'app_icon.ico')}
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{str(dist_dir)}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{autoprograms}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\app_icon.ico"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent
"""

    iss_file = BASE_DIR / "dist" / "installer.iss"
    with open(iss_file, "w", encoding="utf-8") as f:
        f.write(iss_content)
    print(f"[*] Inno Setup script dibuat di: {iss_file}")

    # 11. Compile Installer using Inno Setup
    print("\n[*] Mengompilasi Installer Windows dengan Inno Setup 6...")
    iscc_cmd = [str(iscc_path), str(iss_file)]
    res = subprocess.run(iscc_cmd, cwd=str(BASE_DIR))
    if res.returncode != 0:
        print(f"[!] Inno Setup gagal mengompilasi installer (returncode {res.returncode})")
        sys.exit(1)

    setup_exe = installer_out_dir / "StudioDownload_v1.0_Setup.exe"
    if setup_exe.exists():
        size_mb = setup_exe.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 65)
        print("   SUKSES! WINDOWS INSTALLER BERHASIL DIBUAT!")
        print(f"   File: {setup_exe}")
        print(f"   Ukuran: {size_mb:.2f} MB")
        print("=" * 65)
        print("\n[NOTE] Build ini dilakukan secara lokal dan TIDAK di-push sesuai instruksi.")
    else:
        print("[!] File installer tidak ditemukan setelah kompilasi.")
        sys.exit(1)

if __name__ == "__main__":
    build()
