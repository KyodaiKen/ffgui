#!/bin/bash
TARGET_EXE="/mnt/nas/install/ffgui-win-x64-installer.exe"
PUBLISH_DIR="/mnt/data/GIT/ffgui/publish-win"
SFX_PATH="/mnt/data/GIT/ffgui/7z-win.sfx"

7z a -sfx"$SFX_PATH" -t7z -m0=lzma2 -mx=9 -md=256m -mfb=64 -ms=on -mqs=on -mmt=on -sccUTF-8 \
     "$TARGET_EXE" \
     -ir!"$PUBLISH_DIR/*"
