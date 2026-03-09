#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║  NEURON 8 — Auto-updater                                         ║
║  Checks GitHub releases and installs newer versions in-place.    ║
║                                                                  ║
║  GitHub asset naming convention (must match exactly):            ║
║    Windows : Neuron8-windows.zip   (keyword: 'windows' or 'win') ║
║    Linux   : Neuron8-linux.zip     (keyword: 'linux')            ║
║    macOS   : Neuron8-macos.zip     (keyword: 'macos','mac','osx')║
║                                                                  ║
║  The zip should contain a single top-level folder whose          ║
║  contents mirror the Neuron8 install directory exactly.          ║
╚══════════════════════════════════════════════════════════════════╝
"""
import sys, os, json, zipfile, shutil, tempfile, subprocess
from typing import Callable, Optional

# ── Configuration ────────────────────────────────────────────────────────────
GITHUB_OWNER = "Gizmo564"
GITHUB_REPO  = "NEURON8"
API_URL      = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
VERSION_FILE = "version.txt"

# Keywords used to match the correct zip from a release's assets list.
PLATFORM_KEYWORDS: dict = {
    "win32" : ["windows", "win"],
    "darwin": ["macos", "mac", "osx", "darwin"],
    "linux" : ["linux"],
}


# ── Version helpers ───────────────────────────────────────────────────────────
def _version_file_path() -> str:
    """Locate version.txt whether running frozen or from source."""
    base = sys._MEIPASS if getattr(sys, "frozen", False) else \
           os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, VERSION_FILE)


def current_version() -> str:
    """Return the installed version string (e.g. '1.2.3'), or '0.0.0' if unreadable."""
    try:
        with open(_version_file_path(), "r") as f:
            return f.read().strip().lstrip("v")
    except Exception:
        return "0.0.0"


def _parse(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.lstrip("v").split(".")[:3])
    except Exception:
        return (0, 0, 0)


def is_newer(remote: str, local: str) -> bool:
    """Return True if remote is strictly newer than local."""
    return _parse(remote) > _parse(local)


# ── GitHub API ────────────────────────────────────────────────────────────────
def fetch_latest_release(timeout: int = 10) -> Optional[dict]:
    """
    Query the GitHub releases API.
    Returns the latest release dict (tag_name, body, assets, …) or None on failure.
    """
    try:
        from urllib.request import urlopen, Request
        req = Request(
            API_URL,
            headers={
                "User-Agent": "Neuron8-Updater/1.0",
                "Accept":     "application/vnd.github+json",
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def find_platform_asset(release: dict) -> Optional[dict]:
    """
    Return the asset dict for the current OS, matched by keyword in the zip filename.
    Returns None if no matching asset is found.
    """
    keywords = PLATFORM_KEYWORDS.get(sys.platform, [sys.platform])
    for asset in release.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and any(k in name for k in keywords):
            return asset
    return None


# ── Install directory ─────────────────────────────────────────────────────────
def install_dir() -> str:
    """
    The directory that the updater treats as the root of the Neuron 8 install.

    Windows / Linux  →  the folder containing Neuron8.exe / Neuron8
                        (sys.executable lives there directly)

    macOS .app bundle →  Neuron8.app itself.
                         sys.executable is buried at
                         Neuron8.app/Contents/MacOS/Neuron8, so we walk
                         up the path until we find the .app component.
                         The macOS release zip is built from the *contents*
                         of Neuron8.app (no wrapper folder), so rsync copies
                         Contents/ etc. straight into the .app in place.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        if sys.platform == "darwin":
            parts = exe_dir.split(os.sep)
            for i, part in enumerate(parts):
                if part.endswith(".app"):
                    return os.sep.join(parts[: i + 1])
        return exe_dir
    return os.path.dirname(os.path.abspath(__file__))


# ── Download ──────────────────────────────────────────────────────────────────
def download_asset(
    asset: dict,
    dest_path: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> bool:
    """
    Stream-download a GitHub release asset to dest_path.
    progress_cb(fraction 0–1, status_text) is called periodically.
    Returns True on success.
    """
    try:
        from urllib.request import urlopen, Request
        url   = asset["browser_download_url"]
        total = asset.get("size", 0)
        done  = 0
        req   = Request(url, headers={"User-Agent": "Neuron8-Updater/1.0"})
        with urlopen(req) as resp, open(dest_path, "wb") as f:
            while True:
                chunk = resp.read(65536)          # 64 KB chunks
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total:
                    progress_cb(done / total * 0.70,
                                f"Downloading… {done // 1024:,} / {total // 1024:,} KB")
        if progress_cb:
            progress_cb(0.70, "Download complete.")
        return True
    except Exception as exc:
        if progress_cb:
            progress_cb(0.0, f"Download error: {exc}")
        return False


# ── Extract ───────────────────────────────────────────────────────────────────
def extract_zip(
    zip_path: str,
    out_dir: str,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> Optional[str]:
    """
    Extract zip_path into out_dir.
    If the zip wraps a single top-level folder (common with GitHub releases),
    return the path to that folder so the installer sees the actual app files.
    Returns the content path on success, or None on failure.
    """
    if progress_cb:
        progress_cb(0.72, "Extracting…")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(out_dir)
    except Exception as exc:
        if progress_cb:
            progress_cb(0.0, f"Extraction error: {exc}")
        return None

    # Unwrap a single top-level directory if present
    entries = [e for e in os.listdir(out_dir) if not e.startswith(".")]
    if len(entries) == 1:
        candidate = os.path.join(out_dir, entries[0])
        if os.path.isdir(candidate):
            return candidate
    return out_dir


# ── Platform-specific helper scripts ─────────────────────────────────────────
#
# The helper script is written to the system temp directory and launched
# as a detached process.  It waits a few seconds for all Neuron8 instances
# to exit, then copies the new files over the install directory and restarts.
#
# Windows notes:
#   - robocopy exit codes 0-7 are all "success" (7 = files copied + extras skipped)
#   - taskkill /f is used to guarantee the exe lock is released before robocopy runs
#
# Linux / macOS notes:
#   - POSIX does not lock running executables at the file level, so the swap is safe
#   - rsync is preferred; cp -Rf is the fallback if rsync is absent

def _write_windows_helper(new_dir: str, dst_dir: str, exe_name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), "n8_update.bat")
    restart = os.path.join(dst_dir, exe_name)
    lines = [
        "@echo off",
        "title Neuron 8 Updater",
        "echo Neuron 8 Updater — please wait...",
        "timeout /t 5 /nobreak >nul",
        # Force-kill any remaining Neuron8 processes to release the exe lock
        f"taskkill /f /im {exe_name} >nul 2>&1",
        "timeout /t 2 /nobreak >nul",
        "echo Installing update...",
        # /e = include subdirs, /is = include same files, /it = include tweaked files
        f'robocopy "{new_dir}" "{dst_dir}" /e /is /it /ndl /nfl /nc /ns /njs /njh',
        # robocopy codes 0-7 all indicate at least partial success
        "if %errorlevel% leq 7 (",
        "    echo Update complete. Launching Neuron 8...",
        f'    rmdir /s /q "{new_dir}" >nul 2>&1',
        f'    start "" "{restart}"',
        ") else (",
        "    echo Update failed. Error code: %errorlevel%",
        "    echo You can download the latest release manually from GitHub.",
        "    pause",
        ")",
    ]
    with open(path, "w", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    return path


def _write_posix_helper(new_dir: str, dst_dir: str, exe_name: str) -> str:
    path = os.path.join(tempfile.gettempdir(), "n8_update.sh")

    # macOS: dst_dir IS the .app bundle — use 'open' to relaunch correctly.
    # Linux: dst_dir is the Neuron8/ folder — run the binary directly.
    if sys.platform == "darwin" and dst_dir.endswith(".app"):
        restart_cmd = f'open "{dst_dir}"'
    else:
        _exe = os.path.join(dst_dir, exe_name)
        restart_cmd = f'chmod +x "{_exe}" 2>/dev/null\n    "{_exe}" &'

    script = f"""#!/bin/sh
echo "Neuron 8 Updater — please wait..."
sleep 5
echo "Installing update..."
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "{new_dir}/" "{dst_dir}/"
    RC=$?
else
    cp -Rf "{new_dir}/." "{dst_dir}/"
    RC=$?
fi
if [ "$RC" -eq 0 ]; then
    echo "Update complete. Launching Neuron 8..."
    rm -rf "{new_dir}"
    {restart_cmd}
else
    echo "Update failed — exit code $RC"
    echo "You can download the latest release manually from GitHub."
    printf "Press Enter to close..."; read -r _
fi
"""
    with open(path, "w", newline="\n") as f:
        f.write(script)
    os.chmod(path, 0o755)
    return path


# ── Full install pipeline ─────────────────────────────────────────────────────
def launch_update(
    release: dict,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> tuple:
    """
    Full update pipeline: find asset → download → extract → write helper → launch helper.

    Returns (success: bool, message: str).
    On success the caller should close the application — the helper will restart it.
    """
    # 1. Locate the right zip for this platform
    asset = find_platform_asset(release)
    if asset is None:
        return False, (
            "No download asset found for your platform.\n\n"
            "Visit the GitHub releases page to download manually:\n"
            f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        )

    # 2. Download
    tmp_root = tempfile.mkdtemp(prefix="n8_update_")
    zip_path = os.path.join(tmp_root, asset["name"])
    if not download_asset(asset, zip_path, progress_cb):
        shutil.rmtree(tmp_root, ignore_errors=True)
        return False, "Download failed.\nCheck your internet connection and try again."

    # 3. Extract
    extract_out = os.path.join(tmp_root, "_extracted")
    os.makedirs(extract_out, exist_ok=True)
    new_dir = extract_zip(zip_path, extract_out, progress_cb)
    if new_dir is None:
        shutil.rmtree(tmp_root, ignore_errors=True)
        return False, "Extraction failed — the downloaded file may be corrupt."

    # 4. Write platform helper
    dst_dir  = install_dir()
    exe_name = "Neuron8.exe" if sys.platform == "win32" else "Neuron8"
    if progress_cb:
        progress_cb(0.90, "Writing update script…")

    helper = (_write_windows_helper if sys.platform == "win32"
              else _write_posix_helper)(new_dir, dst_dir, exe_name)

    # 5. Launch helper detached so it outlives this process
    if progress_cb:
        progress_cb(1.00, "Launching helper…")
    try:
        if sys.platform == "win32":
            # CREATE_NEW_CONSOLE: helper opens its own visible window so the user
            # can see progress.  DETACHED_PROCESS keeps it alive after we exit.
            flags = subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS
            subprocess.Popen(["cmd", "/c", helper],
                             creationflags=flags, close_fds=True)
        else:
            subprocess.Popen(
                ["sh", helper],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
    except Exception as exc:
        shutil.rmtree(tmp_root, ignore_errors=True)
        return False, f"Could not launch update helper:\n{exc}"

    # Clean up the zip (the extracted dir is kept — the helper still needs it)
    try:
        os.remove(zip_path)
    except Exception:
        pass

    return True, "Update helper launched successfully."
