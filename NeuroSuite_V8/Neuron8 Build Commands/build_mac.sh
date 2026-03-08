#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  build_mac.sh  —  Build Neuron 8 for macOS
#  Produces:  dist/Neuron8.app  (drag to /Applications to install)
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

echo "╔══════════════════════════════════╗"
echo "║  Neuron 8 — macOS Build Script   ║"
echo "╚══════════════════════════════════╝"

# ── 1. Python check ───────────────────────────────────────────────────────────
PY=$(which python3)
echo "→ Using Python: $PY ($($PY --version))"

# ── 2. Install / upgrade build deps ──────────────────────────────────────────
echo "→ Installing dependencies…"
$PY -m pip install --quiet --upgrade pip
$PY -m pip install --quiet numpy Pillow matplotlib pyinstaller

# ── 3. ffplay binary ─────────────────────────────────────────────────────────
FFPLAY_DIR="ffplay_bin/macos"
FFPLAY="$FFPLAY_DIR/ffplay"

if [ ! -f "$FFPLAY" ]; then
    echo ""
    echo "⚠  ffplay not found at $FFPLAY"
    echo "   Attempting to download a static build from evermeet.cx…"
    mkdir -p "$FFPLAY_DIR"
    # Try downloading a pre-built static ffplay for macOS (arm64 + x86_64)
    FFPLAY_URL="https://evermeet.cx/ffmpeg/getrelease/ffplay/zip"
    if curl -fsSL "$FFPLAY_URL" -o /tmp/ffplay_mac.zip; then
        unzip -o /tmp/ffplay_mac.zip -d "$FFPLAY_DIR"
        chmod +x "$FFPLAY"
        echo "   ✓ Downloaded ffplay"
    else
        echo "   ✗ Auto-download failed."
        echo "     Download ffplay manually from https://evermeet.cx/ffmpeg/"
        echo "     and place it at $FFPLAY, then re-run this script."
        echo "     (Music will be silently disabled if ffplay is missing.)"
    fi
fi

# ── 4. Clean previous build ───────────────────────────────────────────────────
echo "→ Cleaning previous build…"
rm -rf build dist

# ── 5. Build ─────────────────────────────────────────────────────────────────
echo "→ Running PyInstaller…"
$PY -m PyInstaller neuron8.spec --noconfirm

# ── 6. Code sign (optional — needed for Gatekeeper on other Macs) ────────────
# Uncomment and replace IDENTITY with your Developer ID if you have one:
# IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"
# echo "→ Code-signing…"
# codesign --deep --force --verify --sign "$IDENTITY" dist/Neuron8.app

# ── 7. Create distributable DMG ───────────────────────────────────────────────
if command -v hdiutil &>/dev/null; then
    echo "→ Creating DMG…"
    hdiutil create -volname "Neuron 8" \
                   -srcfolder dist/Neuron8.app \
                   -ov -format UDZO \
                   dist/Neuron8_macOS.dmg
    echo "   ✓ dist/Neuron8_macOS.dmg"
fi

echo ""
echo "✅ Done!  App bundle: dist/Neuron8.app"
echo "   Drag Neuron8.app to /Applications to install."
