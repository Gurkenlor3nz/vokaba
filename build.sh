#!/usr/bin/env bash
set -euo pipefail

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

rm -rf "$OUTDIR" "$APPDIR" "$DEBDIR" build dist venv
mkdir -p "$OUTDIR"

# -------------------------------------------------
# 1️⃣ Virtualenv + Dependencies
# -------------------------------------------------
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt pyinstaller

# -------------------------------------------------
# 2️⃣ PyInstaller (Assets explizit einbinden!)
# -------------------------------------------------
pyinstaller \
  --name "$APP" \
  --noconfirm \
  --clean \
  --add-data "assets:assets" \
  "$MAIN"

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
Categories=Education;Utility;
Terminal=false
Website=$WEBSITE
EOF

cp "$ICON" "$DEBDIR/usr/share/icons/hicolor/256x256/apps/$APP.png"

dpkg-deb --build "$DEBDIR" \
  "$OUTDIR/vokaba-$VERSION-amd64.deb"

echo
echo "✅ Build finished"
echo "📦 Output in: $OUTDIR"
