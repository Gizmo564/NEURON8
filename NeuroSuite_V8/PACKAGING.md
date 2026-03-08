# Neuron 8 — Packaging & Distribution Guide

This guide explains how to turn the Neuron 8 Python source into a self-contained
application for **macOS**, **Linux**, and **Windows** using PyInstaller.

---

## How it works

PyInstaller freezes the Python interpreter, all dependencies (numpy, Pillow,
matplotlib, tkinter), your source files, the `music/` folder, and an `ffplay`
binary into a single folder called `dist/Neuron8/`.

The **launcher** (`Neuron8` / `Neuron8.exe`) is the only binary users need to
click. It opens the hub window and launches each sub-app by re-invoking itself
with a mode argument (`neuro_sim`, `neuro_forge`, etc.), so no separate
executables are needed.

```
dist/Neuron8/
├── Neuron8              ← the only thing users run (Neuron8.exe on Windows)
├── music/               ← bundled audio tracks
├── ffplay               ← bundled audio engine (ffplay.exe on Windows)
├── _internal/           ← Python runtime + all libs (don't touch)
└── ...
```

---

## File layout before building

```
your-project-folder/
├── main.py              ← unified entry point (required by PyInstaller)
├── launcher.py
├── neuron8_core.py
├── neuro_sim.py
├── neuro_forge.py
├── neuro_lab.py
├── neuro_life.py
├── neuron8.spec         ← PyInstaller spec
├── build_mac.sh
├── build_linux.sh
├── build_windows.bat
├── music/               ← all .mp3 files go here
│   ├── Exploring_The_Crystal_Caves_-_Asher_Fulero.mp3
│   └── ...
└── ffplay_bin/          ← platform binaries (see below)
    ├── macos/ffplay
    ├── linux/ffplay
    └── windows/ffplay.exe
```

> ⚠️ **You build on each platform separately.** PyInstaller cannot cross-compile.
> To distribute for all three platforms you need to run the build script once on
> each OS (or use CI — see the GitHub Actions section at the end).

---

## Step 1 — Install Python

| Platform | Requirement |
|----------|-------------|
| macOS    | Python 3.10+ from [python.org](https://www.python.org/downloads/) or via `brew install python` |
| Linux    | `sudo apt install python3 python3-pip python3-tk` (Ubuntu/Debian) |
| Windows  | Python 3.10+ from [python.org](https://www.python.org/downloads/) — check **"Add Python to PATH"** |

---

## Step 2 — Bundle ffplay

Neuron 8 uses `ffplay` (part of FFmpeg) for background music. You need to
provide the binary for each platform so it gets packaged inside the app.

### macOS
The build script tries to download ffplay automatically from
[evermeet.cx](https://evermeet.cx/ffmpeg/).

If that fails:
1. Go to <https://evermeet.cx/ffmpeg/>
2. Download the **ffplay** zip
3. Unzip it and move the `ffplay` binary to `ffplay_bin/macos/ffplay`
4. `chmod +x ffplay_bin/macos/ffplay`

### Linux
The build script tries to download a static build automatically from
[johnvansickle.com](https://johnvansickle.com/ffmpeg/releases/).

If that fails:
1. Go to <https://johnvansickle.com/ffmpeg/releases/>
2. Download `ffmpeg-release-amd64-static.tar.xz` (or `arm64`)
3. Extract it and copy `ffplay` to `ffplay_bin/linux/ffplay`
4. `chmod +x ffplay_bin/linux/ffplay`

### Windows
1. Go to <https://www.gyan.dev/ffmpeg/builds/>
2. Download **"release essentials"** `.zip`
3. Extract the zip; inside the `bin/` folder you'll find `ffplay.exe`
4. Copy it to `ffplay_bin\windows\ffplay.exe`

> **No ffplay?** Music will be silently skipped. Every other feature works fine.

---

## Step 3 — Run the build script

### macOS
```bash
chmod +x build_mac.sh
./build_mac.sh
```
Output: `dist/Neuron8.app` and `dist/Neuron8_macOS.dmg`

### Linux
```bash
chmod +x build_linux.sh
./build_linux.sh
```
Output: `dist/Neuron8_linux.tar.gz`

### Windows
Double-click `build_windows.bat`, or in a Command Prompt:
```cmd
build_windows.bat
```
Output: `dist\Neuron8_windows.zip` and `dist\Neuron8\Neuron8.exe`

---

## Step 4 — Distribute

| Platform | What to give users |
|----------|--------------------|
| macOS    | `Neuron8_macOS.dmg` — mount it, drag `Neuron8.app` to `/Applications` |
| Linux    | `Neuron8_linux.tar.gz` — extract, run `./Neuron8/Neuron8` |
| Windows  | `Neuron8_windows.zip` — extract, double-click `Neuron8.exe` |

---

## macOS Gatekeeper note

macOS will quarantine apps not signed with a paid Apple Developer ID. Users who
download the DMG will need to right-click → Open the first time, or you can
run:

```bash
xattr -cr dist/Neuron8.app
```

before distributing, which removes the quarantine flag (only works if you built
it yourself on the same machine).

If you have an **Apple Developer ID** certificate, uncomment and fill in the
`codesign` line in `build_mac.sh` to properly sign the app.

---

## Windows Defender / SmartScreen note

Unsigned Windows executables will trigger SmartScreen the first time. Users
click **"More info" → "Run anyway"**. To avoid this you can buy a
**code-signing certificate** from a CA and sign `Neuron8.exe` with
`signtool.exe`.

---

## Rebuilding after code changes

Just re-run the build script. You don't need to change `neuron8.spec` unless you
add new data files or modules.

To add a new data file (e.g. `assets/logo.png`):
```python
# in neuron8.spec, add to _datas:
_datas = [
    (os.path.join(HERE, 'music'), 'music'),
    (os.path.join(HERE, 'assets'), 'assets'),   # ← add this
]
```
And access it in Python via:
```python
_BASE = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(__file__)
logo_path = os.path.join(_BASE, 'assets', 'logo.png')
```

---

## Automated builds with GitHub Actions (optional)

If you push the source to a GitHub repo you can build all three platforms
automatically on every release. Create `.github/workflows/build.yml`:

```yaml
name: Build Neuron 8

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        include:
          - os: macos-latest
            script: ./build_mac.sh
            artifact: dist/Neuron8_macOS.dmg
          - os: ubuntu-latest
            script: ./build_linux.sh
            artifact: dist/Neuron8_linux.tar.gz
          - os: windows-latest
            script: build_windows.bat
            artifact: dist/Neuron8_windows.zip

    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - name: Build
        run: ${{ matrix.script }}
        shell: bash
      - uses: actions/upload-artifact@v4
        with:
          name: neuron8-${{ matrix.os }}
          path: ${{ matrix.artifact }}
```

> Note: the GitHub Actions build won't include ffplay unless you either commit
> the binaries to the repo or add a download step to the workflow for each OS.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: tkinter` on Linux | `sudo apt install python3-tk` |
| App opens then immediately closes | Remove `console=False` from spec temporarily to see error output |
| Music silent | Check `ffplay_bin/<platform>/ffplay` exists and is executable |
| Matplotlib blank / crashes | Hidden import already included; if still broken, add `'matplotlib.backends.backend_agg'` to `_hidden` in the spec |
| "App is damaged" on macOS | Run `xattr -cr Neuron8.app` then try again |
| Huge binary size | Normal — numpy + matplotlib + Python runtime = ~120–180 MB. Use `upx=True` (already set) to compress |
