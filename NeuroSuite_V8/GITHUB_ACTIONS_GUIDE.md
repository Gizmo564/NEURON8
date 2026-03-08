# Neuron 8 — GitHub Actions CI/CD Setup Guide

This guide walks you through every step needed to get automated builds running on GitHub,
producing a macOS DMG, Linux tar.gz, and Windows ZIP on every release — all with ffplay
bundled for music playback.

---

## How the whole thing works (big picture)

When you push a version tag like `v1.0.0` to GitHub:

1. GitHub starts three virtual machines simultaneously — one macOS, one Ubuntu, one Windows
2. Each machine checks out your code, downloads ffplay for its own platform, installs Python deps, and runs PyInstaller
3. The three built packages are attached to a GitHub Release as downloadable files
4. Users download the zip/dmg for their platform — no Python required on their end

```
You push tag v1.0.0
        │
        ├─► GitHub runner: macos-latest  → Neuron8_macOS.dmg
        ├─► GitHub runner: ubuntu-latest → Neuron8_linux.tar.gz
        └─► GitHub runner: windows-latest→ Neuron8_windows.zip
                                │
                        All three attached to
                        GitHub Release "v1.0.0"
```

---

## Part 1 — Set up the GitHub repository

### Step 1 — Create a GitHub account

If you don't have one, go to **github.com** and sign up. The free tier supports
unlimited public and private repos, and GitHub Actions is free for public repos
(2,000 minutes/month free for private repos).

### Step 2 — Create a new repository

1. Click the **+** button in the top-right corner of GitHub → **New repository**
2. Name it something like `neuron8`
3. Leave it **Private** if you don't want the source public, or **Public** if you do
4. Do **not** check "Add a README" — you'll push your own files
5. Click **Create repository**

### Step 3 — Install Git on your computer

- **macOS**: Git is already installed. Open Terminal and type `git --version` to confirm.
  If prompted to install Xcode Command Line Tools, do it.
- **Linux**: `sudo apt install git`
- **Windows**: Download from **git-scm.com** and install with default settings.
  When asked about line endings, choose "Checkout as-is, commit as-is".

### Step 4 — Set up your local repository

Open Terminal (or Command Prompt on Windows) in your Neuron 8 project folder — the one
that contains `launcher.py`, `neuron8_core.py`, etc.

```bash
# Navigate to your project folder
cd /path/to/your/neuron8-folder

# Initialise git
git init

# Tell git who you are (use the same email as your GitHub account)
git config user.name "Your Name"
git config user.email "you@example.com"
```

### Step 5 — Create a .gitignore file

Create a file called `.gitignore` in your project folder with this content.
This stops build output and junk from being uploaded:

```
# PyInstaller output
build/
dist/
*.spec.bak

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Virtual environments
venv/
env/
.venv/

# OS junk
.DS_Store
Thumbs.db
desktop.ini

# IDE settings
.vscode/
.idea/
*.sublime-project
*.sublime-workspace
```

Save the file, then:

```bash
git add .gitignore
```

### Step 6 — Add all your project files

Make sure your project folder looks like this before adding:

```
neuron8/
├── .github/               ← you'll create this in Part 2
├── music/                 ← your 6 .mp3 files
│   ├── Exploring_The_Crystal_Caves_-_Asher_Fulero.mp3
│   ├── Glitcher_-_Dyalla.mp3
│   ├── Rain_Over_Kyoto_Station_-_The_Mini_Vandals.mp3
│   ├── False_Vacuum_Decay_-_The_Grey_Room___Density___Time.mp3
│   ├── Rapid_Unscheduled_Disassembly_-_The_Grey_Room___Density___Time.mp3
│   └── Pulsar_-_The_Grey_Room___Density___Time.mp3
├── main.py
├── launcher.py
├── neuron8_core.py
├── neuro_sim.py
├── neuro_forge.py
├── neuro_lab.py
├── neuro_life.py
├── neuron8.spec
├── .gitignore
└── (build scripts are optional — CI won't use them)
```

> ⚠️ **Do NOT commit `ffplay_bin/`** — the CI workflow downloads ffplay
> automatically. Don't commit large binaries to Git.

```bash
git add .
git commit -m "Initial commit"
```

### Step 7 — Connect your local repo to GitHub

On your GitHub repository page, copy the URL shown under "Quick setup".
It looks like `https://github.com/yourusername/neuron8.git`.

```bash
git remote add origin https://github.com/yourusername/neuron8.git
git branch -M main
git push -u origin main
```

Refresh your GitHub page — your files should now appear there.

---

## Part 2 — Create the GitHub Actions workflow

### Step 8 — Create the workflow directory

```bash
# From inside your project folder:
mkdir -p .github/workflows
```

### Step 9 — Create the workflow file

Create the file `.github/workflows/build.yml` with exactly this content:

```yaml
name: Build and Release Neuron 8

# ── Triggers ──────────────────────────────────────────────────────────────────
# Runs when you push a tag starting with "v" (e.g. v1.0.0, v1.2.3)
on:
  push:
    tags:
      - 'v*'

# ── Jobs ──────────────────────────────────────────────────────────────────────
jobs:

  # ── macOS build ─────────────────────────────────────────────────────────────
  build-macos:
    runs-on: macos-latest
    steps:
      - name: Check out source
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install numpy Pillow matplotlib pyinstaller

      - name: Install tkinter (macOS)
        run: |
          # tkinter comes with the python.org build used by setup-python,
          # but brew Python sometimes needs this:
          brew install python-tk@3.12 || true

      - name: Download ffplay for macOS
        run: |
          mkdir -p ffplay_bin/macos
          # Download static ffplay build from evermeet.cx
          curl -fsSL "https://evermeet.cx/ffmpeg/getrelease/ffplay/zip" \
               -o /tmp/ffplay_mac.zip
          unzip -o /tmp/ffplay_mac.zip -d ffplay_bin/macos/
          chmod +x ffplay_bin/macos/ffplay
          # Verify it works
          ffplay_bin/macos/ffplay -version 2>&1 | head -1

      - name: Build with PyInstaller
        run: |
          python -m PyInstaller neuron8.spec --noconfirm

      - name: Create DMG
        run: |
          hdiutil create \
            -volname "Neuron 8" \
            -srcfolder dist/Neuron8.app \
            -ov -format UDZO \
            dist/Neuron8_macOS.dmg

      - name: Upload DMG artifact
        uses: actions/upload-artifact@v4
        with:
          name: Neuron8-macOS
          path: dist/Neuron8_macOS.dmg
          retention-days: 7

  # ── Linux build ─────────────────────────────────────────────────────────────
  build-linux:
    runs-on: ubuntu-latest
    steps:
      - name: Check out source
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install system dependencies
        run: |
          sudo apt-get update -qq
          sudo apt-get install -y python3-tk xvfb

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install numpy Pillow matplotlib pyinstaller

      - name: Download static ffplay for Linux
        run: |
          mkdir -p ffplay_bin/linux
          ARCH=$(uname -m)   # x86_64 or aarch64
          URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${ARCH}-static.tar.xz"
          echo "Downloading static FFmpeg from $URL"
          curl -fsSL "$URL" -o /tmp/ffmpeg_static.tar.xz
          # Extract just ffplay from the archive
          tar -xJf /tmp/ffmpeg_static.tar.xz -C /tmp
          cp /tmp/ffmpeg-*-static/ffplay ffplay_bin/linux/ffplay
          chmod +x ffplay_bin/linux/ffplay
          ffplay_bin/linux/ffplay -version 2>&1 | head -1

      - name: Build with PyInstaller
        run: |
          python -m PyInstaller neuron8.spec --noconfirm

      - name: Create tar.gz archive
        run: |
          cd dist
          tar -czf Neuron8_linux.tar.gz Neuron8/

      - name: Upload Linux artifact
        uses: actions/upload-artifact@v4
        with:
          name: Neuron8-Linux
          path: dist/Neuron8_linux.tar.gz
          retention-days: 7

  # ── Windows build ────────────────────────────────────────────────────────────
  build-windows:
    runs-on: windows-latest
    steps:
      - name: Check out source
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install numpy Pillow matplotlib pyinstaller

      - name: Download ffplay for Windows
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path "ffplay_bin\windows"
          # Download the gyan.dev "release essentials" build
          $url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
          Write-Host "Downloading FFmpeg from $url"
          Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\ffmpeg_win.zip"
          # Extract and locate ffplay.exe
          Expand-Archive -Path "$env:TEMP\ffmpeg_win.zip" -DestinationPath "$env:TEMP\ffmpeg_win" -Force
          $ffplay = Get-ChildItem -Path "$env:TEMP\ffmpeg_win" -Recurse -Filter "ffplay.exe" | Select-Object -First 1
          Copy-Item $ffplay.FullName -Destination "ffplay_bin\windows\ffplay.exe"
          # Verify
          & "ffplay_bin\windows\ffplay.exe" -version 2>&1 | Select-Object -First 1

      - name: Build with PyInstaller
        run: |
          python -m PyInstaller neuron8.spec --noconfirm

      - name: Create ZIP archive
        shell: pwsh
        run: |
          Compress-Archive -Path "dist\Neuron8" -DestinationPath "dist\Neuron8_windows.zip" -Force

      - name: Upload Windows artifact
        uses: actions/upload-artifact@v4
        with:
          name: Neuron8-Windows
          path: dist\Neuron8_windows.zip
          retention-days: 7

  # ── Create GitHub Release with all three artifacts ───────────────────────────
  release:
    needs: [build-macos, build-linux, build-windows]
    runs-on: ubuntu-latest
    permissions:
      contents: write   # needed to create releases and upload assets

    steps:
      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: artifacts/

      - name: List downloaded files
        run: find artifacts/ -type f

      - name: Create GitHub Release and upload assets
        uses: softprops/action-gh-release@v2
        with:
          name: "Neuron 8 ${{ github.ref_name }}"
          body: |
            ## Neuron 8 ${{ github.ref_name }}

            ### Download for your platform:
            | Platform | File | Instructions |
            |----------|------|--------------|
            | 🍎 macOS | `Neuron8_macOS.dmg` | Mount the DMG, drag Neuron8.app to Applications |
            | 🐧 Linux | `Neuron8_linux.tar.gz` | Extract and run `./Neuron8/Neuron8` |
            | 🪟 Windows | `Neuron8_windows.zip` | Extract and double-click `Neuron8.exe` |

            > **macOS note:** If macOS says the app is damaged, right-click → Open, or run:
            > `xattr -cr /Applications/Neuron8.app`

            > **Windows note:** Windows Defender may show a SmartScreen warning.
            > Click "More info" → "Run anyway".
          files: |
            artifacts/Neuron8-macOS/Neuron8_macOS.dmg
            artifacts/Neuron8-Linux/Neuron8_linux.tar.gz
            artifacts/Neuron8-Windows/Neuron8_windows.zip
          draft: false
          prerelease: false
```

Save this file exactly as `.github/workflows/build.yml`.

### Step 10 — Commit and push the workflow

```bash
git add .github/workflows/build.yml
git commit -m "Add GitHub Actions build workflow"
git push origin main
```

Nothing will run yet — the workflow only fires on a version tag, not on a push to main.

---

## Part 3 — Trigger your first build

### Step 11 — Create and push a release tag

When you're ready to publish a release:

```bash
# Make sure all your changes are committed first
git add .
git commit -m "Release v1.0.0"
git push origin main

# Create the version tag
git tag v1.0.0

# Push the tag — this is what triggers the GitHub Actions build
git push origin v1.0.0
```

> The tag name must start with `v` to match the trigger (`'v*'`).
> Use standard version numbers: `v1.0.0`, `v1.1.0`, `v2.0.0`, etc.

### Step 12 — Watch the build run

1. Go to your repository on GitHub
2. Click the **Actions** tab at the top
3. You'll see a workflow run called **"Build and Release Neuron 8"** with your tag name
4. Click on it to see all three jobs running in parallel

Each job shows a live log. The full build takes about 10–15 minutes — most of that time
is downloading the FFmpeg static build and running PyInstaller.

### Step 13 — Find your release

Once all three jobs show a green ✓:

1. Go to your repository's main page on GitHub
2. Click **Releases** on the right sidebar (or go to `github.com/yourusername/neuron8/releases`)
3. You'll see **"Neuron 8 v1.0.0"** with three files attached:
   - `Neuron8_macOS.dmg`
   - `Neuron8_linux.tar.gz`
   - `Neuron8_windows.zip`

Share the release page URL with anyone you want to distribute to.

---

## Part 4 — Making future releases

Every time you want to release a new version:

```bash
# 1. Make your code changes and commit them
git add .
git commit -m "Fix: describe what you changed"
git push origin main

# 2. Tag the new version
git tag v1.1.0
git push origin v1.1.0
```

That's it — GitHub Actions rebuilds everything automatically.

---

## Part 5 — If something goes wrong

### Reading build logs

1. Go to **Actions** tab → click the failed run → click the failed job
2. Expand the failed step to see the full error output
3. Common issues and fixes:

| Error | What it means | Fix |
|-------|---------------|-----|
| `ModuleNotFoundError: No module named '_tkinter'` | tkinter not installed on the runner | The `python3-tk` apt step should fix this; check it ran |
| `curl: (22) The requested URL returned error: 404` | ffplay download URL changed | Update the URL in the workflow; check the source website for the new path |
| `FileNotFoundError: ffplay_bin/...` | ffplay download failed silently | Add `set -e` or check the download step's exit code |
| `UPX is not available` | UPX compressor missing on the runner | Change `upx=True` to `upx=False` in `neuron8.spec` |
| PyInstaller finds wrong Python | Multiple Python versions on runner | Pin the version more specifically in `setup-python` |
| `ERROR: 'NoneType' has no attribute...` | A hidden import is missing | Add the missing module to `_hidden` in `neuron8.spec` |
| Release job fails with 403 | Permissions issue | Make sure `permissions: contents: write` is in the release job |

### Re-running a failed build

If a job fails due to a network blip (download timeout, etc.) rather than a code error:

1. Go to **Actions** → click the failed run
2. Click **Re-run failed jobs** in the top-right corner

You don't need to create a new tag just to retry a transient failure.

### Deleting a bad tag and starting over

If you need to redo a release:

```bash
# Delete the tag locally
git tag -d v1.0.0

# Delete it from GitHub
git push origin --delete v1.0.0

# Fix whatever was wrong, commit, re-tag, and push
git add .
git commit -m "Fix build issue"
git push origin main
git tag v1.0.0
git push origin v1.0.0
```

---

## Part 6 — Optional improvements

### Make builds faster with caching

Add this step before "Install Python dependencies" in each job to cache pip packages
between runs (saves ~2 minutes per build):

```yaml
      - name: Cache pip packages
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
```

### Create a requirements.txt for cleaner dependency management

```bash
# In your project folder:
echo "numpy
Pillow
matplotlib
pyinstaller" > requirements.txt
```

Then in the workflow replace the `pip install` lines with:

```yaml
          pip install -r requirements.txt
```

### Build on every push (not just tags) for testing

Add a second trigger to catch broken builds before you release:

```yaml
on:
  push:
    tags:
      - 'v*'
    branches:
      - main        # ← add this
```

When triggered by a branch push (not a tag), the `release` job will fail gracefully
because `github.ref_name` won't be a tag — you can guard it with:

```yaml
  release:
    needs: [build-macos, build-linux, build-windows]
    if: startsWith(github.ref, 'refs/tags/v')   # ← only runs for tags
    runs-on: ubuntu-latest
```

### Send yourself a notification when a build finishes

Add this at the end of the `release` job to get an email-style summary:

```yaml
      - name: Notify on success
        run: |
          echo "✅ Neuron 8 ${{ github.ref_name }} built and released successfully."
          echo "Release URL: https://github.com/${{ github.repository }}/releases/tag/${{ github.ref_name }}"
```

GitHub also sends you an email notification by default when an Actions run completes
(you can configure this under Settings → Notifications on GitHub).

---

## Quick reference — commands you'll use repeatedly

```bash
# Check what tags you've already created
git tag

# Release a new version
git add . && git commit -m "Release v1.x.x" && git push origin main
git tag v1.x.x && git push origin v1.x.x

# Check if the workflow is running
# → go to github.com/yourusername/neuron8/actions

# Delete a tag (if you need to redo it)
git tag -d v1.x.x && git push origin --delete v1.x.x
```
