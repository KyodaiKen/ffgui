#!/bin/bash
tar cf - ./publish-linux | xz -vv -T16 -e --lzma2=preset=9,dict=256MiB,lc=3,lp=0,pb=2,mode=normal,nice=273,mf=bt4,depth=512 > /mnt/nas/install/ffgui-linux-x64.tar.xz
