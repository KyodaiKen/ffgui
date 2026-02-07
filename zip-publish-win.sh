#!/bin/bash
PUBLISH_DIR="./publish-win"

7z a -sfx7z-win.sfx -t7z -m0=lzma2 -mx=9 -md=256m -mfb=64 -ms=on -mqs=on -mmt=on -sccUTF-8 "/mnt/nas/install/ffgui-win-x64-installer.exe" "$PUBLISH_DIR/*"
