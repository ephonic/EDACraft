@echo off
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
echo cl:
where cl.exe
echo link:
where link.exe
echo msvcrt:
dir /b "C:\Program Files (x86)\Windows Kits\10\Lib\*\um\x64\msvcrt.lib" 2>nul
