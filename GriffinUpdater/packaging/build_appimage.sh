#!/usr/bin/env bash
# Build GriffinUpdater-<version>-x86_64.AppImage that runs on glibc 2.34+
# (Ubuntu 22.04+, Debian 12+, Fedora 35+ ...).
#
# Why this is not just "pyinstaller on my laptop": a binary needs at least the
# glibc of the machine that built it. Building on a current distro silently
# raises the floor (Ubuntu 24.04 -> 2.39). So the script
#   1. uses a python-build-standalone interpreter (built against glibc 2.17)
#      via `uv`, not the distro python,
#   2. swaps in an older libxcb-cursor (the 24.04 build needs glibc 2.38),
#   3. scans every ELF file in the bundle and FAILS if any needs > MAX_GLIBC.
#
# Build host needs: curl, objdump (binutils), and these runtime libs that Qt's
# xcb plugin links against (PyInstaller bundles them from the host):
#   sudo apt install libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
#        libxcb-render-util0 libxcb-shape0 libxcb-xkb1 libxcb-xinerama0 \
#        libxkbcommon-x11-0 libxcb-util1
#
# Usage:  packaging/build_appimage.sh            -> dist/GriffinUpdater-<ver>-x86_64.AppImage
#         MAX_GLIBC=2.35 packaging/build_appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MAX_GLIBC="${MAX_GLIBC:-2.34}"
PY_VERSION="${PY_VERSION:-3.12}"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' griffin_updater/__init__.py)"
[ -n "$VERSION" ] || { echo "could not read __version__"; exit 1; }

BUILD="$ROOT/build"
VENV="$BUILD/venv"
APPDIR="$BUILD/AppDir"
OUT="$ROOT/dist"
ARCH=x86_64
OUT_FILE="$OUT/GriffinUpdater-${VERSION}-${ARCH}.AppImage"

# Old libxcb-cursor (Ubuntu 22.04 "jammy"): needs only glibc 2.8.
XCB_CURSOR_DEB_URL="http://archive.ubuntu.com/ubuntu/pool/universe/x/xcb-util-cursor/libxcb-cursor0_0.1.1-4ubuntu1_amd64.deb"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"

echo "==> Griffin Updater $VERSION  (target: glibc >= $MAX_GLIBC)"
rm -rf "$BUILD/AppDir" "$BUILD/pyi" "$OUT/griffin-updater"
mkdir -p "$BUILD" "$OUT"

# ---------------------------------------------------------------- python env
if ! command -v uv >/dev/null 2>&1; then
    echo "==> installing uv"
    python3 -m pip install --user --break-system-packages uv 2>/dev/null \
        || python3 -m pip install --user uv
    export PATH="$HOME/.local/bin:$PATH"
fi
if [ ! -x "$VENV/bin/python" ]; then
    echo "==> creating venv with standalone Python $PY_VERSION (old-glibc build)"
    uv python install "$PY_VERSION"
    uv venv --python "$PY_VERSION" --managed-python "$VENV"
fi
uv pip install --python "$VENV/bin/python" --quiet PyQt6 pyinstaller requests pillow
PY="$VENV/bin/python"

# --------------------------------------------------------------- pyinstaller
echo "==> PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean --name griffin-updater \
    --distpath "$BUILD/pyi/dist" --workpath "$BUILD/pyi/work" --specpath "$BUILD/pyi" \
    --paths "$ROOT" \
    --add-data "$ROOT/resources:resources" \
    --collect-submodules griffin_updater \
    --exclude-module tkinter \
    "$ROOT/run_griffin_updater.py"
BUNDLE="$BUILD/pyi/dist/griffin-updater"

# Replace whatever libxcb-cursor PyInstaller picked up from the host.
echo "==> bundling old libxcb-cursor"
TMPX="$(mktemp -d)"
curl -fsSL -o "$TMPX/cursor.deb" "$XCB_CURSOR_DEB_URL"
dpkg-deb -x "$TMPX/cursor.deb" "$TMPX/x"
CURSOR_SO="$(find "$TMPX/x" -name 'libxcb-cursor.so.0.0.0' | head -1)"
DEST_DIR="$BUNDLE/_internal"; [ -d "$DEST_DIR" ] || DEST_DIR="$BUNDLE"
find "$BUNDLE" -name 'libxcb-cursor.so*' -delete
cp "$CURSOR_SO" "$DEST_DIR/libxcb-cursor.so.0"
rm -rf "$TMPX"

# ------------------------------------------------------ prune + glibc check
# PyInstaller copies every host library the Qt plugins link against. Those come
# from the build machine's distro (glibc 2.38+ on current Ubuntu) and would lift
# the AppImage's glibc floor, so:
#   * the GTK3 platform-theme plugin (which drags in GTK/cairo/pango/...) is
#     dropped - Qt falls back to its own styling, the app is fully themed by
#     griffin_updater/theme.py anyway;
#   * any remaining top-level host library that is too new is removed and left
#     to the target system (libX11, libdbus, fontconfig, glib, libstdc++ ...
#     exist on every desktop that has glibc >= MAX_GLIBC);
#   * anything else that is too new (Python, PyQt6/Qt wheel libs) fails the build.
echo "==> pruning host libraries that would raise the glibc floor"
find "$BUNDLE" -name 'libqgtk3.so' -delete
# ...and the GTK-only libraries PyInstaller collected for it (never loaded without that plugin).
for lib in libatk-1.0 libatspi libcairo-gobject libgdk_pixbuf-2.0 libpangocairo-1.0 \
           libpangoft2-1.0 libepoxy libpixman-1 libthai libdatrie; do
    rm -f "$BUNDLE"/_internal/"$lib".so* "$BUNDLE"/"$lib".so* 2>/dev/null || true
done

elf_glibc() {  # highest GLIBC_x.y symbol version an ELF file needs (empty if none)
    objdump -T "$1" 2>/dev/null | grep -o 'GLIBC_[0-9][0-9.]*' | sed 's/GLIBC_//' | sort -uV | tail -1 || true
}
too_new() {  # true if $1 > $MAX_GLIBC
    [ "$(printf '%s\n%s\n' "$1" "$MAX_GLIBC" | sort -V | tail -1)" != "$MAX_GLIBC" ]
}
is_elf() { head -c4 "$1" | grep -q $'\x7fELF'; }

pruned=0; bad=0; worst="0"
while IFS= read -r -d '' f; do
    is_elf "$f" || continue
    v="$(elf_glibc "$f")"; [ -n "$v" ] || continue
    if too_new "$v"; then
        rel="${f#$BUNDLE/}"
        case "$rel" in
            _internal/lib*.so*|lib*.so*)
                case "$(basename "$rel")" in
                    libpython*) echo "   TOO NEW (needs glibc $v): $rel"; bad=1 ;;
                    *) rm -f "$f"; pruned=$((pruned+1)) ;;
                esac ;;
            *) echo "   TOO NEW (needs glibc $v): $rel"; bad=1 ;;
        esac
    fi
done < <(find "$BUNDLE" -type f -print0)
echo "   pruned $pruned host librar$( [ "$pruned" = 1 ] && echo y || echo ies ) (provided by the target system instead)"

echo "==> scanning bundle for glibc symbol versions"
while IFS= read -r -d '' f; do
    is_elf "$f" || continue
    v="$(elf_glibc "$f")"; [ -n "$v" ] || continue
    if [ "$(printf '%s\n%s\n' "$v" "$worst" | sort -V | tail -1)" = "$v" ]; then worst="$v"; fi
    if too_new "$v"; then echo "   TOO NEW (needs glibc $v): ${f#$BUNDLE/}"; bad=1; fi
done < <(find "$BUNDLE" -type f -print0)
echo "   highest glibc requirement in bundle: $worst"
if [ "$bad" -ne 0 ]; then
    echo "ERROR: some bundled files need glibc newer than $MAX_GLIBC (see above)."
    exit 1
fi

# ------------------------------------------------------------------- AppDir
echo "==> assembling AppDir"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/applications"
cp -a "$BUNDLE" "$APPDIR/usr/bin/griffin-updater"
cp "$ROOT/packaging/griffin-updater.desktop" "$APPDIR/griffin-updater.desktop"
cp "$ROOT/packaging/griffin-updater.desktop" "$APPDIR/usr/share/applications/"
"$PY" - "$ROOT/resources/griffin-updater.png" "$APPDIR" <<'PYEOF'
import sys
from PIL import Image
src, appdir = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGBA")
im.thumbnail((256, 256), Image.LANCZOS)
im.save(f"{appdir}/griffin-updater.png")
im.save(f"{appdir}/usr/share/icons/hicolor/256x256/apps/griffin-updater.png")
PYEOF
ln -sf griffin-updater.png "$APPDIR/.DirIcon"
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/griffin-updater/griffin-updater" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# ------------------------------------------------------------- appimagetool
TOOL="$BUILD/appimagetool"
[ -x "$TOOL" ] || { echo "==> downloading appimagetool"; curl -fsSL -o "$TOOL" "$APPIMAGETOOL_URL"; chmod +x "$TOOL"; }
echo "==> building AppImage"
rm -f "$OUT_FILE"
ARCH=$ARCH "$TOOL" --appimage-extract-and-run --no-appstream "$APPDIR" "$OUT_FILE"
chmod +x "$OUT_FILE"
echo "==> done: $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
