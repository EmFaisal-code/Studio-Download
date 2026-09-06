@echo off
title Studio Download Launcher
cd /d "%~dp0"
echo ========================================================
echo        STUDIO DOWNLOAD - YouTube Media Downloader
echo ========================================================
echo Memeriksa dan menjalankan Studio Download...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi masalah saat menjalankan Studio Download.
    pause
)
