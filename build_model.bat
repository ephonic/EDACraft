@echo off
REM Build OSDI model library: run OpenVAF inside MSVC env so MSVC link.exe wins
setlocal

set "SIM=G:\vibe-codeing\simulator"
set "TMP=%SIM%\build\tmp"
set "TEMP=%SIM%\build\tmp"
if not exist "%TMP%" mkdir "%TMP%"

REM Enter MSVC build environment (puts cl/link/lib + Windows SDK on PATH first)
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

REM Keep mingw64 available too (for any aux tools), but MSVC link now precedes
set "PATH=%SIM%\tools;G:\msys64\mingw64\bin;%PATH%"

echo === Compiling %1 with OpenVAF ===
"%SIM%\tools\openvaf.exe" %1 -o %2
if errorlevel 1 (echo FAILED & exit /b 1)
echo === OK: %2 ===
dir %2
endlocal
