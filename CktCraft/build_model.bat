@echo off
REM Build OSDI model library with OpenVAF-Reloaded (OSDI v0.4 ABI)
REM
REM Switched from OpenVAF 23.5.0 (pascalkuthe, OSDI 0.3) to OpenVAF-Reloaded
REM osdi_0.4-153-g2e066436 (IHP, 2026-02-26) in Sprint S3 to pick up upstream
REM "critical bugs" fixes (MOS-AK 2024) and to align host with the actively
REM maintained fork. host src/model/osdi/osdi.h accepts both v0.3 (legacy
REM precompiled dlls: bsim4soi/bsimcmg/bsimsoi) and v0.4 (this compiler's
REM output). See docs/osdi_0_4_migration.md.
REM
REM Legacy OpenVAF 23.5.0 kept as tools/openvaf-legacy.exe for rollback.
REM
REM Usage: build_model.bat <input.va> <output.dll>
setlocal

set "SIM=G:\vibe-codeing\simulator"
set "TMP=%SIM%\build\tmp"
set "TEMP=%SIM%\build\tmp"
if not exist "%TMP%" mkdir "%TMP%"

REM Enter MSVC build environment (OpenVAF uses MSVC link.exe for codegen)
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

REM Keep mingw64 available too (for any aux tools), but MSVC link now precedes
set "PATH=%SIM%\tools;G:\msys64\mingw64\bin;%PATH%"

echo === Compiling %1 with OpenVAF-Reloaded (OSDI 0.4) ===
"%SIM%\tools\openvaf-reloaded.exe" %1 -o %2
if errorlevel 1 (echo FAILED & exit /b 1)
echo === OK: %2 ===
dir %2
endlocal
