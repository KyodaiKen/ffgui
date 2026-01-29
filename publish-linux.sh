#!/bin/bash
rm -rf ./publish-linux

echo "--- 1. Building ---"
dotnet publish -c Release -r linux-x64 --self-contained false -p:PublishSingleFile=true

echo "--- 2. Copying essentials ---"
rsync -av --exclude='ffmpeg' ./codecs/ ./publish-linux/codecs/
cp -r ./templates ./publish-linux/templates

echo "--- 3. Pack deployment ---"
tar cf - ./publish-linux | xz -vv -T8 -e --lzma2=preset=9,dict=256MiB,lc=3,lp=0,pb=2,mode=normal,nice=273,mf=bt4,depth=512 > ./publish-linux/ffgui-linux-x64.tar.xz

echo "--- 4. Cleanup ---"
rm -rf ./bin
rm -rf ./obj
