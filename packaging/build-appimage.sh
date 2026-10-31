#!/bin/bash
# Builds Griffin-Updater-x86_64.AppImage.
#
# Run this from the project root on a real Linux machine with internet
# access (it downloads appimagetool the first time). It won't work inside
# a sandboxed/offline build environment.
#
# Usage:
#   bash packaging/build-appimage.sh
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BUILD_DIR="$PROJECT_ROOT/build"
APPDIR="$BUILD_DIR/AppDir"
VENV_DIR="$BUILD_DIR/venv"
TOOLS_DIR="$BUILD_DIR/tools"
APPIMAGETOOL="$TOOLS_DIR/appimagetool-x86_64.AppImage"

echo "==> Cleaning previous build"
rm -rf "$BUILD_DIR" dist
mkdir -p "$APPDIR/usr/bin" "$TOOLS_DIR"

echo "==> Creating build venv"
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install pyinstaller -q

echo "==> Running PyInstaller"
pyinstaller packaging/griffin-updater.spec --noconfirm --distpath dist --workpath "$BUILD_DIR/pyinstaller-work"

echo "==> Assembling AppDir"
cp -r dist/griffin-updater/* "$APPDIR/usr/bin/"
cp packaging/AppRun "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp packaging/griffin-updater.desktop "$APPDIR/griffin-updater.desktop"
cp resources/griffin-updater.png "$APPDIR/griffin-updater.png"
cp resources/griffin-updater.png "$APPDIR/.DirIcon"

deactivate

echo "==> Fetching appimagetool (first run only)"
if [ ! -f "$APPIMAGETOOL" ]; then
    curl -fsSL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
fi

echo "==> Building AppImage"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$PROJECT_ROOT/Griffin-Updater-x86_64.AppImage"

echo "==> Done: Griffin-Updater-x86_64.AppImage"
