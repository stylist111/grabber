#!/bin/bash
# macOS build: universal helper (Apple Silicon + Intel in one file) + extension → dist/Grabber-macOS.tar.gz
#
#   bash src/build-mac.sh
#
# Needs the universal2 Python from python.org (not Homebrew's: that one is single-arch) with PyInstaller:
#   /usr/local/bin/python3 -m pip install pyinstaller
# CI (.github/workflows/release.yml) installs both. PYTHON=... picks another interpreter.
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)"
root="$(dirname "$src")"
py="${PYTHON:-/Library/Frameworks/Python.framework/Versions/Current/bin/python3}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

"$py" -m PyInstaller --noconfirm --clean --onedir --target-arch universal2 --name grabber_host \
    --distpath "$work/dist" --workpath "$work/build" --specpath "$work" "$src/host.py"

stage="$work/Grabber"
mkdir -p "$stage"
cp -R "$work/dist/grabber_host" "$stage/app"
cp -R "$root/extension" "$stage/extension"
lipo -archs "$stage/app/grabber_host"   # expect: x86_64 arm64

mkdir -p "$root/dist"
# COPYFILE_DISABLE: no ._* resource-fork files in the archive.
COPYFILE_DISABLE=1 tar -czf "$root/dist/Grabber-macOS.tar.gz" -C "$work" Grabber
echo "OK: $root/dist/Grabber-macOS.tar.gz"
