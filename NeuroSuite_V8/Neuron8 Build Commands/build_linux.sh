#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  build_linux.sh  —  Build Neuron 8 for Linux
#  Produces:  dist/Neuron8/  (zip and distribute, or create an AppImage)
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "╔══════════════════════════════════╗"
echo "║  Neuron 8 — Linux Build Script   ║"
echo "╚══════════════════════════════════╝"

# ── 1. System deps check ──────────────────────────────────────────────────────
echo "→ Checking system dependencies…"
MISSING=()
for pkg in python3 python3-pip python3-tk ffmpeg; do
    if ! dpkg -s "$pkg" &>/dev/null 2>&1 && ! command -v "${pkg%%[0-9]*}" &>/dev/null; then
        MISSING+=("$pkg")
    fi
done
if [ ${#MISSING[@]} -gt 0 ]; then
    echo "  Installing: ${MISSING[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${MISSING[@]}"
fi

PY=$(which python3)
echo "→ Using Python: $PY ($($PY --version))"

# ── 2. Install / upgrade Python deps ─────────────────────────────────────────
echo "→ Installing Python dependencies…"
$PY -m pip install --quiet --upgrade pip
$PY -m pip install --quiet numpy Pillow matplotlib pyinstaller

# ── 3. Bundle ffplay binary ───────────────────────────────────────────────────
# On Linux we prefer to bundle a static ffplay so the app works on distros
# without ffmpeg installed.
FFPLAY_DIR="ffplay_bin/linux"
FFPLAY="$FFPLAY_DIR/ffplay"

if [ ! -f "$FFPLAY" ]; then
    echo "→ Bundling static ffplay for Linux…"
    mkdir -p "$FFPLAY_DIR"
    ARCH=$(uname -m)
    STATIC_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${ARCH}-static.tar.xz"
    TMP=$(mktemp -d)
    echo "   Downloading from johnvansickle.com…"
    if curl -fsSL "$STATIC_URL" -o "$TMP/ffmpeg.tar.xz"; then
        tar -xJf "$TMP/ffmpeg.tar.xz" -C "$TMP"
        cp "$TMP"/ffmpeg-*-static/ffplay "$FFPLAY"
        chmod +x "$FFPLAY"
        rm -rf "$TMP"
        echo "   ✓ Bundled static ffplay ($ARCH)"
    else
        # Fall back to system ffplay (won't work on machines without ffmpeg)
        SYSTEM_FFPLAY=$(which ffplay 2>/dev/null || true)
        if [ -n "$SYSTEM_FFPLAY" ]; then
            cp "$SYSTEM_FFPLAY" "$FFPLAY"
            chmod +x "$FFPLAY"
            echo "   ✓ Copied system ffplay (may not be portable)"
        else
            echo "   ✗ Could not find or download ffplay."
            echo "     Music will be silently disabled in the packaged app."
        fi
    fi
fi

# ── 4. Clean previous build ───────────────────────────────────────────────────
echo "→ Cleaning previous build…"
rm -rf build dist

# ── 5. Build ─────────────────────────────────────────────────────────────────
echo "→ Running PyInstaller…"
$PY -m PyInstaller neuron8.spec --noconfirm

# ── 6. Create AppImage (optional — requires appimagetool) ─────────────────────
if command -v appimagetool &>/dev/null; then
    echo "→ Creating AppImage…"
    mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps
    cp -r dist/Neuron8/* AppDir/usr/bin/
    cat > AppDir/neuron8.desktop <<EOF
[Desktop Entry]
Name=Neuron 8
Exec=Neuron8
Icon=neuron8
Type=Application
Categories=Science;Education;
EOF
    ln -sf usr/bin/Neuron8 AppDir/AppRun 2>/dev/null || true
    ARCH=$(uname -m) appimagetool AppDir dist/Neuron8_linux.AppImage
    rm -rf AppDir
    echo "   ✓ dist/Neuron8_linux.AppImage"
fi

# ── 7. Create .tar.gz ─────────────────────────────────────────────────────────
echo "→ Creating distributable archive…"
cd dist
tar -czf Neuron8_linux.tar.gz Neuron8/
cd ..
echo "   ✓ dist/Neuron8_linux.tar.gz"

echo ""
echo "✅ Done!  Distributable: dist/Neuron8_linux.tar.gz"
echo "   To run: tar -xzf Neuron8_linux.tar.gz && ./Neuron8/Neuron8"
