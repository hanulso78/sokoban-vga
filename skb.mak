# ============================================================================
#  SOKO-BAN (Spectrum HoloByte, 1988)  -  djgpp 빌드
# ----------------------------------------------------------------------------
#      make -f skb.mak            SOKOBAN.EXE
#      make -f skb.mak clean
#
#  SOKOBAN.EXE - 원판 SKB.EXE 를 C 로 옮긴 것 (CGA/Tandy 화면을 VGA 로 보인다)
#       필요한 파일 : CWSDPMI.EXE 와 원판 자료 파일들 (INTRO1, LOBBY11, TAB*, ...)
#  SOKOVGA.EXE - 개선판: 같은 게임 코드에 256색 그림자 (skbvga.c), 애드립 음악 (skbopl.c)
#       필요한 파일 : 위에 더해 SKBVGA.DAT (tools/mkvga.py), SOUND.DAT (tools/mkmusic.py)
# ============================================================================

CC      = gcc
CFLAGS  = -O2 -Wall -Wno-unused-label -Wno-unused-variable -fno-strict-aliasing

ORIG    = skbcode.o skbdata.o cpu.o sys_dos.o
VGA     = skbcode.vo skbdata.vo cpu.vo sys_dos.vo skbvga.vo skbopl.vo

all: sokoban.exe sokovga.exe

orig: sokoban.exe
vga:  sokovga.exe

sokovga.exe: $(VGA)
	$(CC) $(CFLAGS) -o sokovga.exe $(VGA)
	strip sokovga.exe

%.vo: %.c cpu.h skbcode.h skbvga.h skbvars.h
	$(CC) $(CFLAGS) -DSKBVGA -c $< -o $@

sokoban.exe: $(ORIG)
	$(CC) $(CFLAGS) -o sokoban.exe $(ORIG)
	strip sokoban.exe

%.o: %.c cpu.h skbcode.h skbvars.h
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	-del *.o
	-del *.vo
	-del sokoban.exe
	-del sokovga.exe
