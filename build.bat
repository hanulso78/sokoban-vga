@echo off
rem Build SOKOBAN.EXE with djgpp (arguments go to make)
call "%~dp0..\..\djgpp\setenv.bat"
cd /d "%~dp0"
make -f skb.mak %*
