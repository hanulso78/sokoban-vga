#!/bin/sh
# PC(MSYS2 mingw)용 대조 시험판 hosttest.exe
export PATH=/c/MSYS2/mingw64/bin:$PATH
cd "$(dirname "$0")"
gcc -O2 -w -o hosttest.exe tools/hosttest.c cpu.c skbcode.c skbdata.c "$@"
# 개선판 미리보기 (같은 게임 코드 + 256색 그림자, SKBSHOT=경로접두 면 화면을 BMP 로)
gcc -O2 -w -DSKBVGA -o hostvga.exe tools/hosttest.c cpu.c skbcode.c skbdata.c skbvga.c "$@"
