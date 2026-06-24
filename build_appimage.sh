#!/bin/bash
set -e

echo "=== Step 1: Preparing build workspace ==="
BUILD_DIR="build_workspace"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "=== Step 2: Ensuring PyInstaller is installed ==="
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pyinstaller

echo "=== Step 3: Compiling with PyInstaller ==="
.venv/bin/pyinstaller --noconfirm --clean --onedir --name=ShadowGram \
    --add-data "resources:resources" \
    ShadowGram.py

echo "=== Step 4: Constructing AppDir structure ==="
APPDIR="$BUILD_DIR/AppDir"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/applications"

# Copy PyInstaller bundle to AppDir/usr/bin/
cp -r dist/ShadowGram/* "$APPDIR/usr/bin/"

# Copy AppRun launcher
cp AppRun "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"

# Copy desktop entries
cp shadowgram.desktop "$APPDIR/shadowgram.desktop"
cp shadowgram.desktop "$APPDIR/usr/share/applications/shadowgram.desktop"

# Copy application icon
cp resources/icons/green/GrobTyan_logo.png "$APPDIR/shadowgram.png"

echo "=== Step 5: Downloading appimagetool ==="
APPIMAGE_TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
wget -O "$BUILD_DIR/appimagetool" "$APPIMAGE_TOOL_URL" || curl -Lo "$BUILD_DIR/appimagetool" "$APPIMAGE_TOOL_URL"
chmod +x "$BUILD_DIR/appimagetool"

echo "=== Step 6: Packaging AppImage ==="
# Remove old file first to avoid 'Text file busy' if it is currently running
rm -f ShadowGram-x86_64.AppImage
# We run with --appimage-extract-and-run to avoid FUSE issues in container/virtual environments
ARCH=x86_64 "$BUILD_DIR/appimagetool" --appimage-extract-and-run "$APPDIR" ShadowGram-x86_64.AppImage

echo "=== Step 7: Cleaning up temporary directories ==="
rm -rf "$BUILD_DIR"
rm -rf dist build ShadowGram.spec

echo "=== Success! AppImage built as ShadowGram-x86_64.AppImage ==="
