#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

APP="vokaba"
MAIN="main.py"
ICON="assets/vokaba_logo.png"
OUTBASE="$HOME/Dokumente/Vokaba-releases"
WEBSITE="https://vokaba.firecast.de"

APPDIR="AppDir"
DEBDIR="deb-build"

SKIP_APPIMAGE=0
SKIP_DEB=0
SKIP_SRC=0

for arg in "${@:-}"; do
  case "$arg" in
    --skip-appimage) SKIP_APPIMAGE=1 ;;
    --skip-deb)      SKIP_DEB=1 ;;
    --skip-src)      SKIP_SRC=1 ;;
    *) echo "Unknown arg: $arg"; exit 2 ;;
  esac
done

echo "==> Reading version"
VERSION="$(python3 - <<'PY'
import re
with open("main.py", encoding="utf-8") as f:
    for line in f:
        if "__version__" in line:
            m = re.findall(r'["\'](.*?)["\']', line)
            if m:
                print(m[0])
                raise SystemExit(0)
raise SystemExit(1)
PY
)" || { echo "❌ __version__ not found"; exit 1; }

OUTDIR="$OUTBASE/vokaba-$VERSION"

rm -rf "$OUTDIR" "$APPDIR" "$DEBDIR" build dist venv build-win dist-win
mkdir -p "$OUTDIR"

# -------------------------------------------------
# Source code zip (platform-neutral)
# -------------------------------------------------
if [ "$SKIP_SRC" -eq 0 ]; then
  echo "==> Building source zip"
  SRCZIP="$OUTDIR/vokaba-$VERSION-source.zip"
  python3 - <<PY
import os, zipfile

root = os.path.abspath(".")
out  = os.path.abspath(r"$SRCZIP")

exclude_dirs = {
  ".git", ".idea", "__pycache__",
  "venv", ".venv", ".venv-win",
  "build", "dist", "build-win", "dist-win",
  "AppDir", "deb-build"
}
exclude_files = {
  "appimagetool.AppImage",
}

def should_exclude(path):
  rel = os.path.relpath(path, root)
  parts = rel.split(os.sep)
  if any(p in exclude_dirs for p in parts):
    return True
  if os.path.basename(path) in exclude_files:
    return True
  if rel.endswith((".pyc", ".pyo")):
    return True
  return False

with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
  for dirpath, dirnames, filenames in os.walk(root):
    # prune excluded dirs
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    for fn in filenames:
      p = os.path.join(dirpath, fn)
      if should_exclude(p):
        continue
      rel = os.path.relpath(p, root)
      z.write(p, rel)

print(out)
PY
  ls -lh "$SRCZIP"
fi

# -------------------------------------------------
# 1️⃣ Virtualenv + Dependencies (Linux Build)
# -------------------------------------------------
echo "==> Installing deps (Linux venv)"
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt pyinstaller

# -------------------------------------------------
# 2️⃣ PyInstaller (Linux, one-folder)
# -------------------------------------------------
echo "==> PyInstaller (Linux)"
pyinstaller \
  --name "$APP" \
  --noconfirm \
  --clean \
  --add-data "assets:assets" \
  "$MAIN"

# -------------------------------------------------
# 3️⃣ AppImage
# -------------------------------------------------
if [ "$SKIP_APPIMAGE" -eq 0 ]; then
  echo "==> Building AppImage"

  mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/icons/hicolor/256x256/apps"

  cp -r "dist/$APP" "$APPDIR/usr/lib/"
  ln -s "../lib/$APP/$APP" "$APPDIR/usr/bin/$APP"

  # AppRun
  cat > "$APPDIR/AppRun" <<EOF
#!/bin/sh
HERE=\$(dirname "\$(readlink -f "\$0")")
export LD_LIBRARY_PATH="\$HERE/usr/lib:\$HERE/usr/lib/$APP:\$LD_LIBRARY_PATH"
exec "\$HERE/usr/bin/$APP"
EOF
  chmod +x "$APPDIR/AppRun"

  # Desktop
  cat > "$APPDIR/$APP.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vokaba
Exec=$APP
Icon=$APP
Categories=Education;Utility;
Terminal=false
X-Website=$WEBSITE
EOF

  cp "$ICON" "$APPDIR/$APP.png"
  cp "$ICON" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP.png"

  # optional runtime libs
  cp -n /usr/lib/x86_64-linux-gnu/libGL.so*  "$APPDIR/usr/lib/" 2>/dev/null || true
  cp -n /usr/lib/x86_64-linux-gnu/libEGL.so* "$APPDIR/usr/lib/" 2>/dev/null || true

  TOOL="$PWD/appimagetool.AppImage"
  if [ ! -f "$TOOL" ]; then
    wget -q "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$TOOL"
    chmod +x "$TOOL"
  fi

  TMPDIR="$(mktemp -d)"
  cp -a "$APPDIR" "$TMPDIR/AppDir"
  (
    cd "$TMPDIR"
    ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" AppDir
  )

  GEN="$(find "$TMPDIR" -maxdepth 1 -type f -name '*.AppImage' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
  [ -f "$GEN" ] || { echo "❌ AppImage not found"; exit 1; }

  APPIMAGE_OUT="$OUTDIR/vokaba-$VERSION-x86_64.AppImage"
  mv -f "$GEN" "$APPIMAGE_OUT"
  chmod +x "$APPIMAGE_OUT"
  rm -rf "$TMPDIR"

  ls -lh "$APPIMAGE_OUT"
fi

# -------------------------------------------------
# 4️⃣ Debian Package
# -------------------------------------------------
if [ "$SKIP_DEB" -eq 0 ]; then
  echo "==> Building .deb"

  mkdir -p "$DEBDIR/DEBIAN" \
           "$DEBDIR/usr/bin" \
           "$DEBDIR/usr/lib/$APP" \
           "$DEBDIR/usr/share/applications" \
           "$DEBDIR/usr/share/icons/hicolor/256x256/apps"

  cat > "$DEBDIR/DEBIAN/control" <<EOF
Package: vokaba
Version: $VERSION
Section: education
Priority: optional
Architecture: amd64
Depends: libc6, libgl1, libglib2.0-0
Maintainer: Theo aka Gurkenlor3nz
Description: Vokaba – ultra-minimalistic Kivy based vocabulary application
EOF

  cp -r "dist/$APP/"* "$DEBDIR/usr/lib/$APP/"
  ln -s "/usr/lib/$APP/$APP" "$DEBDIR/usr/bin/$APP"

  cat > "$DEBDIR/usr/share/applications/$APP.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Vokaba
Exec=$APP
Icon=$APP
Categories=Education;
Terminal=false
Website=$WEBSITE
EOF

  cp "$ICON" "$DEBDIR/usr/share/icons/hicolor/256x256/apps/$APP.png"

  dpkg-deb --build "$DEBDIR" "$OUTDIR/vokaba-$VERSION-amd64.deb"
  ls -lh "$OUTDIR/vokaba-$VERSION-amd64.deb"
fi

echo
echo "✅ Linux build finished"
echo "📦 Output in: $OUTDIR"
