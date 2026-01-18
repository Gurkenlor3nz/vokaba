#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------
# Docker (mit/ohne sudo) als Array, damit "sudo docker" sauber funktioniert
# -------------------------------------------------
DOCKER=(docker)
HOST_UID="${SUDO_UID:-$(id -u)}"
HOST_GID="${SUDO_GID:-$(id -g)}"

if ! docker info >/dev/null 2>&1; then
  if sudo docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    echo "❌ Docker ist nicht nutzbar (keine Rechte auf /var/run/docker.sock)."
    echo "   Fix: sudo usermod -aG docker \$USER && newgrp docker"
    exit 1
  fi
fi

APP="vokaba"
MAIN="main.py"
ICON="assets/vokaba_logo.png"
OUTBASE="$HOME/Dokumente/Vokaba-releases"
WEBSITE="https://vokaba.firecast.de"

APPDIR="AppDir"
DEBDIR="deb-build"

# -------------------------------------------------
# Version auslesen
# -------------------------------------------------
echo "==> Reading version"
VERSION=$(python3 - <<EOF
import re
with open("$MAIN") as f:
    for line in f:
        if "__version__" in line:
            print(re.findall(r'["\\'](.*?)["\\']', line)[0])
            break
EOF
)

[ -z "$VERSION" ] && echo "❌ __version__ not found" && exit 1

OUTDIR="$OUTBASE/vokaba-$VERSION"

rm -rf "$OUTDIR" "$APPDIR" "$DEBDIR" build dist venv build-win dist-win
mkdir -p "$OUTDIR"

# -------------------------------------------------
# 1️⃣ Virtualenv + Dependencies (Linux Build)
# -------------------------------------------------
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt pyinstaller

# -------------------------------------------------
# 2️⃣ PyInstaller (Linux, one-folder)
# -------------------------------------------------
pyinstaller \
  --name "$APP" \
  --noconfirm \
  --clean \
  --add-data "assets:assets" \
  "$MAIN"

# -------------------------------------------------
# 2️⃣b Windows Portable EXE (ONEFILE) via Docker+Wine
# -------------------------------------------------
echo "==> Building Windows portable .exe (ONEFILE) via Docker+Wine"

WIN_IMAGE="mymi14s/ubuntu-wine:24.04-3.11"
"${DOCKER[@]}" pull "$WIN_IMAGE" >/dev/null 2>&1 || true

"${DOCKER[@]}" run --rm \
  -v "$PWD:/src" \
  -w /src \
  -e WINEDEBUG=-all \
  -e XDG_RUNTIME_DIR=/tmp/xdg-runtime \
  -e HOST_UID="$HOST_UID" \
  -e HOST_GID="$HOST_GID" \
  "$WIN_IMAGE" \

bash -lc "$(cat <<'EOS'
set -euo pipefail
cd /src

mkdir -p /tmp/xdg-runtime
chmod 700 /tmp/xdg-runtime
export XDG_RUNTIME_DIR=/tmp/xdg-runtime

# laut Image-Doku liegt Windows-Python hier:
WINPY="C://Python311/python.exe"

# Check
if ! wine cmd /c "\"$WINPY\" -V" >/dev/null 2>&1; then
  echo "❌ $WINPY nicht gefunden."
  echo "   Ursache ist fast immer: falsches WINEPREFIX oder Image-Tag."
  exit 1
fi

# pip + deps + pyinstaller (im Wine-Python)
wine cmd /c "\"$WINPY\" -m pip install --upgrade pip wheel"
wine cmd /c "\"$WINPY\" -m pip install -r requirements.txt"
wine cmd /c "\"$WINPY\" -m pip install pyinstaller"

rm -rf build-win dist-win

# Build (ONEFILE)
wine cmd /c "\"$WINPY\" -m PyInstaller --name vokaba --noconfirm --clean --onefile --windowed --distpath dist-win --workpath build-win --specpath build-win --add-data \"assets;assets\" main.py"

ls -lah dist-win || true
chown -R "$HOST_UID:$HOST_GID" dist-win build-win || true
EOS
)"


WIN_EXE="dist-win/${APP}.exe"
if [ ! -f "$WIN_EXE" ]; then
  WIN_EXE="$(find dist-win -maxdepth 2 -type f -name "${APP}.exe" | head -n 1 || true)"
fi

if [ -z "${WIN_EXE:-}" ] || [ ! -f "$WIN_EXE" ]; then
  echo "❌ Windows .exe not found in dist-win/"
  echo "   Debug: ls -lah dist-win && find dist-win -maxdepth 3 -type f | sed -n '1,200p'"
  exit 1
fi

WIN_OUT="$OUTDIR/vokaba-$VERSION-win64.exe"
mv -f "$WIN_EXE" "$WIN_OUT"
ls -lh "$WIN_OUT"

# -------------------------------------------------
# 3️⃣ AppImage
# -------------------------------------------------
echo "==> Building AppImage"

mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/lib"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

cp -r "dist/$APP" "$APPDIR/usr/lib/"
ln -s "../lib/$APP/$APP" "$APPDIR/usr/bin/$APP"

# AppRun
cat <<EOF > "$APPDIR/AppRun"
#!/bin/sh
HERE=\$(dirname "\$(readlink -f "\$0")")
export LD_LIBRARY_PATH="\$HERE/usr/lib:\$HERE/usr/lib/$APP:\$LD_LIBRARY_PATH"
exec "\$HERE/usr/bin/$APP"
EOF
chmod +x "$APPDIR/AppRun"

# Desktop-Datei
cat <<EOF > "$APPDIR/$APP.desktop"
[Desktop Entry]
Type=Application
Name=Vokaba
Exec=$APP
Icon=$APP
Categories=Education;Utility;
Terminal=false
X-Website=$WEBSITE
EOF

# Icon fürs appimagetool
cp "$ICON" "$APPDIR/$APP.png"
cp "$ICON" "$APPDIR/usr/share/icons/hicolor/256x256/apps/$APP.png"

# Kivy / OpenGL Runtime libs (optional)
cp -n /usr/lib/x86_64-linux-gnu/libGL.so*  "$APPDIR/usr/lib/" 2>/dev/null || true
cp -n /usr/lib/x86_64-linux-gnu/libEGL.so* "$APPDIR/usr/lib/" 2>/dev/null || true

# appimagetool besorgen
TOOL="$PWD/appimagetool.AppImage"
if [ ! -f "$TOOL" ]; then
  wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage \
    -O "$TOOL"
  chmod +x "$TOOL"
fi

# WICHTIG: In temp dir bauen, damit kein *.AppImage-Glob appimagetool selbst erwischt
TMPDIR="$(mktemp -d)"
cp -a "$APPDIR" "$TMPDIR/AppDir"

(
  cd "$TMPDIR"
  # Umgeht FUSE-Probleme beim Build:
  ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" AppDir
)

# generiertes AppImage finden (ohne appimagetool selbst)
GEN="$(find "$TMPDIR" -maxdepth 1 -type f -name '*.AppImage' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
if [ -z "${GEN:-}" ] || [ ! -f "$GEN" ]; then
  echo "❌ Could not find generated AppImage in $TMPDIR"
  exit 1
fi

APPIMAGE_OUT="$OUTDIR/vokaba-$VERSION-x86_64.AppImage"
mv -f "$GEN" "$APPIMAGE_OUT"
chmod +x "$APPIMAGE_OUT"
ls -l "$APPIMAGE_OUT"
rm -rf "$TMPDIR"

echo "==> AppImage written to:"
ls -lh "$OUTDIR"

# -------------------------------------------------
# 4️⃣ Debian Package
# -------------------------------------------------
echo "==> Building .deb"

mkdir -p "$DEBDIR/DEBIAN"
mkdir -p "$DEBDIR/usr/bin"
mkdir -p "$DEBDIR/usr/lib/$APP"
mkdir -p "$DEBDIR/usr/share/applications"
mkdir -p "$DEBDIR/usr/share/icons/hicolor/256x256/apps"

cat <<EOF > "$DEBDIR/DEBIAN/control"
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

cat <<EOF > "$DEBDIR/usr/share/applications/$APP.desktop"
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

dpkg-deb --build "$DEBDIR" \
  "$OUTDIR/vokaba-$VERSION-amd64.deb"

echo
echo "✅ Build finished"
echo "📦 Output in: $OUTDIR"
