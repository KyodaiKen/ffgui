#!/bin/bash
rm -rf ./publish-linux

echo "--- 1. Building ---"
dotnet publish -c Release -r linux-x64 -p:SelfContained=false -p:PublishSingleFile=true

echo "--- 2. Copying essentials ---"
rsync -av --exclude='ffmpeg' ./codecs/ ./publish-linux/codecs/
