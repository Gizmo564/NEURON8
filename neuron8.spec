# -*- mode: python ; coding: utf-8 -*-
"""
neuron8.spec  —  PyInstaller spec for Neuron 8
Bundles all modules, music folder, and the platform ffplay binary into a
single executable file (onefile mode).

Build on each platform:
    pyinstaller neuron8.spec

Output:
    Windows / Linux  →  dist/Neuron8   (or Neuron8.exe)
    macOS            →  dist/Neuron8.app
"""

import sys
import os

block_cipher = None

# ── Paths ────────────────────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(SPEC))

# Platform-specific ffplay binary bundled with the project.
# Download static builds and place them here before building:
#   Windows : ffplay_bin/windows/ffplay.exe
#   macOS   : ffplay_bin/macos/ffplay
#   Linux   : ffplay_bin/linux/ffplay
_plat       = 'windows' if sys.platform == 'win32' else ('macos' if sys.platform == 'darwin' else 'linux')
_ffplay_src = os.path.join(HERE, 'ffplay_bin', _plat, 'ffplay' + ('.exe' if sys.platform == 'win32' else ''))
_ffplay_dst = 'ffplay.exe' if sys.platform == 'win32' else 'ffplay'

# ── Collected binaries & data ────────────────────────────────────────────────
_binaries = []
if os.path.exists(_ffplay_src):
    _binaries.append((_ffplay_src, '.'))
else:
    print(f"\n⚠  WARNING: ffplay binary not found at {_ffplay_src}")
    print("   Music will not play in the packaged app.")
    print("   Place the correct static ffplay build in ffplay_bin/{platform}/\n")

_datas = [
    # Music folder — extracted to sys._MEIPASS/music/ at runtime
    (os.path.join(HERE, 'music'), 'music'),
    # Version file — read by updater.py via sys._MEIPASS
    (os.path.join(HERE, 'version.txt'), '.'),
]

# ── Hidden imports (matplotlib / PIL backends not auto-detected) ─────────────
_hidden = [
    'matplotlib.backends.backend_tkagg',
    'matplotlib.backends._backend_tk',
    'matplotlib.figure',
    'PIL._tkinter_finder',
    'PIL.ImageTk',
    'numpy',
    'numpy.core._methods',
    'numpy.lib.format',
    # certifi: provides CA bundle for SSL in frozen macOS apps where the
    # system certificate store is not accessible to urllib
    'certifi',
]

# ── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(HERE, 'main.py')],
    pathex=[HERE],
    binaries=_binaries,
    datas=_datas,
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'pandas', 'IPython', 'jupyter', 'notebook', 'PyQt5', 'wx'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Icon path — platform picks the right format ──────────────────────────────
if sys.platform == 'win32':
    _icon = os.path.join(HERE, 'assets', 'neuron8.ico')
elif sys.platform == 'darwin':
    _icon = os.path.join(HERE, 'assets', 'neuron8.icns')
else:
    _icon = os.path.join(HERE, 'assets', 'neuron8.png')

# ── Version string for macOS Info.plist ──────────────────────────────────────
try:
    with open(os.path.join(HERE, 'version.txt')) as _vf:
        _version = _vf.read().strip()
except Exception:
    _version = '1.0.0'

# ── Onefile EXE ──────────────────────────────────────────────────────────────
# In onefile mode all binaries, zipfiles, and datas are passed directly into
# EXE (no separate COLLECT step). PyInstaller compresses everything into the
# executable itself; at launch it self-extracts to a temp dir (sys._MEIPASS).
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    exclude_binaries=False,
    name='Neuron8',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

# ── macOS .app bundle (only active on macOS) ─────────────────────────────────
# With onefile, BUNDLE wraps the single exe into a standard .app structure.
# The result is dist/Neuron8.app — drag-and-drop ready for Applications/.
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Neuron8.app',
        icon=_icon,
        bundle_identifier='com.volvi.neuron8',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': _version,
            'CFBundleVersion': _version,
            'CFBundleName': 'Neuron 8',
            'CFBundleDisplayName': 'Neuron 8',
        },
    )
