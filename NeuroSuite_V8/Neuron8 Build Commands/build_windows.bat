@echo off
REM ────────────────────────────────────────────────────────────────────────────
REM  build_windows.bat  —  Build Neuron 8 for Windows
REM  Produces:  dist\Neuron8\  (zip and distribute)
REM
REM  Requirements: Python 3.10+ installed and on PATH
REM ────────────────────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ╔══════════════════════════════════╗
echo ║  Neuron 8 — Windows Build Script ║
echo ╚══════════════════════════════════╝

REM ── 1. Python check ──────────────────────────────────────────────────────────
where python >nul 2>&1 || (
    echo ERROR: Python not found on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo Using %%v

REM ── 2. Install / upgrade Python deps ─────────────────────────────────────────
echo Installing Python dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet numpy Pillow matplotlib pyinstaller
if errorlevel 1 (echo ERROR: pip install failed & pause & exit /b 1)

REM ── 3. ffplay binary ─────────────────────────────────────────────────────────
set FFPLAY_DIR=ffplay_bin\windows
set FFPLAY=%FFPLAY_DIR%\ffplay.exe

if not exist "%FFPLAY%" (
    echo.
    echo ffplay.exe not found at %FFPLAY%
    echo.
    echo  You need to download a static Windows ffplay build:
    echo  1. Go to:  https://www.gyan.dev/ffmpeg/builds/
    echo  2. Download the "release essentials" .zip
    echo  3. Extract it and copy ffplay.exe to:  %FFPLAY_DIR%\ffplay.exe
    echo  4. Re-run this script.
    echo.
    echo  Music will be silently disabled if ffplay.exe is missing,
    echo  but the rest of Neuron 8 will still work.
    echo.
    REM Don't abort — allow building without music
)

REM ── 4. Clean previous build ───────────────────────────────────────────────────
echo Cleaning previous build...
if exist build   rmdir /s /q build
if exist dist    rmdir /s /q dist

REM ── 5. Build ─────────────────────────────────────────────────────────────────
echo Running PyInstaller...
python -m PyInstaller neuron8.spec --noconfirm
if errorlevel 1 (echo ERROR: PyInstaller failed & pause & exit /b 1)

REM ── 6. Create a .zip for distribution ────────────────────────────────────────
echo Creating distributable ZIP...
powershell -Command "Compress-Archive -Path 'dist\Neuron8' -DestinationPath 'dist\Neuron8_windows.zip' -Force"
if exist "dist\Neuron8_windows.zip" (
    echo    OK  dist\Neuron8_windows.zip
) else (
    echo    WARNING: Could not create ZIP ^(PowerShell may be restricted^)
)

echo.
echo Done!  Distributable: dist\Neuron8_windows.zip
echo         Executable:    dist\Neuron8\Neuron8.exe
echo.
echo To run: extract the zip and double-click Neuron8.exe
pause
