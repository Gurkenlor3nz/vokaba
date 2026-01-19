#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

APP="vokaba"
MAIN="main.py"
ICON="assets/vokaba_logo.png"

# --- OUTBASE immer im echten User-Home, auch wenn Script per sudo läuft ---
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

# bevorzugt XDG Documents, sonst Fallback auf "$REAL_HOME/Dokumente"
DOCS_DIR="$(sudo -u "$REAL_USER" xdg-user-dir DOCUMENTS 2>/dev/null || true)"
if [ -z "${DOCS_DIR:-}" ] || [ ! -d "$DOCS_DIR" ]; then
  DOCS_DIR="$REAL_HOME/Dokumente"
fi

OUTBASE="$DOCS_DIR/Vokaba-releases"

WEBSITE="https://vokaba.firecast.de"

APPDIR="AppDir"
DEBDIR="deb-build"

# Docker (Android)
DOCKER_IMAGE="kivy/buildozer:latest"   # alternativ: ghcr.io/kivy/buildozer:latest (steht auch in der Doku) :contentReference[oaicite:3]{index=3}
DOCKER_CACHE_DIR="$PWD/.docker-cache"
DOCKER_BUILDOZER_CACHE="$DOCKER_CACHE_DIR/buildozer"
DOCKER_GRADLE_CACHE="$DOCKER_CACHE_DIR/gradle"

# -------------------------------------------------
# Args
# -------------------------------------------------
SKIP_APPIMAGE=0
SKIP_DEB=0
SKIP_SRC=0

BUILD_APK=0
BUILD_AAB=0
ANDROID_RELEASE=0
CLEAN_ANDROID=0
SKIP_LINUX=0

while [ $# -gt 0 ]; do
  case "${1:-}" in
    --skip-appimage) SKIP_APPIMAGE=1 ;;
    --skip-deb)      SKIP_DEB=1 ;;
    --skip-src)      SKIP_SRC=1 ;;

    --apk)             BUILD_APK=1 ;;
    --aab)             BUILD_AAB=1 ;;
    --android-release) ANDROID_RELEASE=1 ;;
    --clean-android)   CLEAN_ANDROID=1 ;;
    --skip-linux)      SKIP_LINUX=1 ;;

    -h|--help)
      echo "Usage: ./build.sh [--skip-appimage] [--skip-deb] [--skip-src] [--apk] [--aab] [--android-release] [--clean-android] [--skip-linux]"
      exit 0
      ;;
    --) shift; break ;;
    "") ;;
    *)
      echo "Unknown arg: '$1'"
      exit 2
      ;;
  esac
  shift
done

# -------------------------------------------------
# Version auslesen
# -------------------------------------------------
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
)" || { echo "❌ __version__ not found in main.py"; exit 1; }

OUTDIR="$OUTBASE/vokaba-$VERSION"

# Clean (Projekt-Artefakte)
rm -rf "$OUTDIR" "$APPDIR" "$DEBDIR" build dist venv build-win dist-win
mkdir -p "$OUTDIR"

# -------------------------------------------------
# Source code zip
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
  "AppDir", "deb-build",
  ".buildozer", "bin",
  ".docker-cache",
}
exclude_files = {"appimagetool.AppImage"}
def should_exclude(path):
  rel = os.path.relpath(path, root)
  parts = rel.split(os.sep)
  if any(p in exclude_dirs for p in parts):
    return True
  if os.path.basename(path) in exclude_files:
    return True
  if rel.endswith((".pyc", ".pyo")):
    return True
  rel_norm = rel.replace(chr(92), "/")
  if "/.buildozer/" in rel_norm:
    return True
  return False
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
  for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
    for fn in filenames:
      p = os.path.join(dirpath, fn)
      if should_exclude(p):
        continue
      z.write(p, os.path.relpath(p, root))
print(out)
PY
  ls -lh "$SRCZIP"
fi

# -------------------------------------------------
# Android helpers
# -------------------------------------------------
ensure_buildozer_spec() {
  if [ -f "buildozer.spec" ]; then
    return
  fi

  echo "==> buildozer.spec not found -> generating spec"
  cat > buildozer.spec <<EOF
[app]
title = Vokaba
package.name = vokaba
package.domain = de.firecast
version = $VERSION

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,wav,mp3,csv,yml,yaml,json,txt
source.exclude_dirs = .git,venv,.venv,build,dist,AppDir,deb-build,.buildozer,bin,build-win,dist-win,.docker-cache
source.exclude_patterns = */__pycache__/*,*.pyc,*.pyo,*/.buildozer/*

# WICHTIG: Android + pyjnius + plyer (du nutzt die in deinem Code)
requirements = python3,kivy,android,pyjnius,plyer,pyyaml

orientation = portrait
fullscreen = 0

android.archs = arm64-v8a,armeabi-v7a
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.accept_sdk_license = True
android.private_storage = True
android.permissions = INTERNET
EOF
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "❌ docker not found. Install Docker first."
    exit 1
  fi
}

build_android_docker() {
  local mode="debug"
  if [ "$ANDROID_RELEASE" -eq 1 ]; then
    mode="release"
  fi

  if [ "$CLEAN_ANDROID" -eq 1 ]; then
    echo "==> Android clean (.buildozer, bin, docker cache)"
    rm -rf .buildozer bin "$DOCKER_CACHE_DIR"
  fi

  ensure_buildozer_spec
  require_docker

  mkdir -p "$DOCKER_BUILDOZER_CACHE" "$DOCKER_GRADLE_CACHE"

  echo "==> Docker pull: $DOCKER_IMAGE"
  docker pull "$DOCKER_IMAGE" >/dev/null || true

  if [ "$BUILD_APK" -eq 1 ]; then
    echo "==> Docker Buildozer: android $mode (APK)"
    LOG="$OUTDIR/buildozer-docker-android-$mode-apk.log"
    set +e

    REAL_USER="${SUDO_USER:-$USER}"

    docker run --rm \
      -v "$PWD":/home/user/hostcwd \
      -v "$DOCKER_BUILDOZER_CACHE":/home/user/.buildozer \
      -v "$DOCKER_GRADLE_CACHE":/home/user/.gradle \
      "$DOCKER_IMAGE" android "$mode" 2>&1 | tee "$LOG"
    rc=${PIPESTATUS[0]}
    set -e
    if [ $rc -ne 0 ]; then
      echo "❌ Android APK build failed. Log: $LOG"
      tail -n 120 "$LOG" || true
      exit 1
    fi
  fi

  if [ "$BUILD_AAB" -eq 1 ]; then
    echo "==> Docker Buildozer: android $mode aab (AAB)"
    LOG="$OUTDIR/buildozer-docker-android-$mode-aab.log"
    set +e

    REAL_USER="${SUDO_USER:-$USER}"

    docker run --rm \
      -v "$PWD":/home/user/hostcwd \
      -v "$DOCKER_BUILDOZER_CACHE":/home/user/.buildozer \
      -v "$DOCKER_GRADLE_CACHE":/home/user/.gradle \
      "$DOCKER_IMAGE" android "$mode" aab 2>&1 | tee "$LOG"
    rc=${PIPESTATUS[0]}
    set -e
    if [ $rc -ne 0 ]; then
      echo "❌ Android AAB build failed. Log: $LOG"
      tail -n 120 "$LOG" || true
      exit 1
    fi
  fi

  # Outputs nach OUTDIR kopieren
  if [ -d "bin" ]; then
    echo "==> Copying Android artifacts to: $OUTDIR"
    shopt -s nullglob
    for f in bin/*"$mode"*.apk bin/*"$mode"*.aab bin/*.apk bin/*.aab; do
      [ -f "$f" ] || continue
      bn="$(basename "$f")"
      if [[ "$bn" == *"$VERSION"* ]]; then
        outname="$bn"
      else
        outname="vokaba-$VERSION-$bn"
      fi
      cp -f "$f" "$OUTDIR/$outname"
      echo "  -> $OUTDIR/$outname"
    done
    shopt -u nullglob
  fi
}

# -------------------------------------------------
# Android-only? (ohne Host-venv)
# -------------------------------------------------
if [ "$BUILD_APK" -eq 1 ] || [ "$BUILD_AAB" -eq 1 ]; then
  if [ "$SKIP_LINUX" -eq 1 ]; then
    build_android_docker
    echo
    echo "✅ Android build finished"
    echo "📦 Output in: $OUTDIR"
    exit 0
  fi
fi

# -------------------------------------------------
# Linux venv + PyInstaller
# -------------------------------------------------
if [ "$SKIP_LINUX" -eq 0 ]; then
  echo "==> Installing deps (Linux venv)"
  python3 -m venv venv
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install --upgrade pip wheel
  pip install -r requirements.txt pyinstaller

  echo "==> PyInstaller (Linux)"
  pyinstaller \
    --name "$APP" \
    --noconfirm \
    --clean \
    --add-data "assets:assets" \
    "$MAIN"
fi

# -------------------------------------------------
# AppImage
# -------------------------------------------------
if [ "$SKIP_LINUX" -eq 0 ] && [ "$SKIP_APPIMAGE" -eq 0 ]; then
  echo "==> Building AppImage"
  mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
  cp -r "dist/$APP" "$APPDIR/usr/lib/"
  ln -s "../lib/$APP/$APP" "$APPDIR/usr/bin/$APP"

  cat > "$APPDIR/AppRun" <<EOF
#!/bin/sh
HERE=\$(dirname "\$(readlink -f "\$0")")
export LD_LIBRARY_PATH="\$HERE/usr/lib:\$HERE/usr/lib/$APP:\$LD_LIBRARY_PATH"
exec "\$HERE/usr/bin/$APP"
EOF
  chmod +x "$APPDIR/AppRun"

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

  TOOL="$PWD/appimagetool.AppImage"
  if [ ! -f "$TOOL" ]; then
    wget -q "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" -O "$TOOL"
    chmod +x "$TOOL"
  fi

  TMPDIR="$(mktemp -d)"
  cp -a "$APPDIR" "$TMPDIR/AppDir"
  ( cd "$TMPDIR"; ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" AppDir )

  GEN="$(find "$TMPDIR" -maxdepth 1 -type f -name '*.AppImage' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
  [ -n "${GEN:-}" ] && [ -f "$GEN" ] || { echo "❌ Could not find generated AppImage"; exit 1; }

  APPIMAGE_OUT="$OUTDIR/vokaba-$VERSION-x86_64.AppImage"
  mv -f "$GEN" "$APPIMAGE_OUT"
  chmod +x "$APPIMAGE_OUT"
  rm -rf "$TMPDIR"
  ls -lh "$APPIMAGE_OUT"
fi

# -------------------------------------------------
# Debian Package
# -------------------------------------------------
if [ "$SKIP_LINUX" -eq 0 ] && [ "$SKIP_DEB" -eq 0 ]; then
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

# -------------------------------------------------
# Android + Linux in einem Run (wenn nicht skip-linux)
# -------------------------------------------------
if [ "$BUILD_APK" -eq 1 ] || [ "$BUILD_AAB" -eq 1 ]; then
  build_android_docker
fi

if [ "$(id -u)" -eq 0 ] && [ -n "${SUDO_USER:-}" ]; then
  chown -R "$REAL_USER":"$REAL_USER" "$OUTBASE" 2>/dev/null || true
fi

echo
echo "✅ Build finished"
echo "📦 Output in: $OUTDIR"
