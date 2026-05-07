@echo off
:: setup.bat — FLOAT AI Desktop Assistant — Windows One-Command Installer
:: Run this once from the project directory: setup.bat

title FLOAT Setup
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         FLOAT AI — Windows Installer         ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not available.
    pause
    exit /b 1
)

echo [1/5] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo [2/5] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt

echo [3/5] Checking for FFmpeg (needed for YouTube audio)...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo [WARN] FFmpeg not found. YouTube audio playback may not work.
    echo        Download from https://www.gyan.dev/ffmpeg/builds/
    echo        and add ffmpeg\bin to your PATH.
) else (
    echo        FFmpeg found. OK.
)

echo [4/5] Creating .env from template (if not exists)...
if not exist ".env" (
    copy ".env.template" ".env" >nul
    echo        .env created. EDIT IT NOW before running FLOAT.
) else (
    echo        .env already exists — skipping.
)

echo [5/5] Creating logs and assets directories...
if not exist "logs"   mkdir logs
if not exist "assets" mkdir assets

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║         Setup Complete!                      ║
echo  ║                                              ║
echo  ║  Next steps:                                 ║
echo  ║  1. Edit .env and add your API keys          ║
echo  ║  2. Run: python float.py                     ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
