@echo off
REM Build OSDI model library with OpenVAF-Reloaded (OSDI v0.4 ABI)
REM
REM OpenVAF-Reloaded (IHP maintained fork) replaces OpenVAF 23.5.0.
REM host src/model/osdi/osdi.h accepts both v0.3 (legacy precompiled
REM dlls: bsim4soi/bsimcmg/bsimsoi) and v0.4 (this compiler output).
REM See Development_guide.md "OSDI Integration".
REM
REM Legacy OpenVAF 23.5.0 kept as tools/openvaf.exe for rollback.
REM
REM Usage: build_model.bat ^<input.va^> ^<output.dll^>
setlocal

set "SIM=%~dp0"
if "%SIM:~-1%"=="\" set "SIM=%SIM:~0,-1%"
set "TMP=%SIM%\build\tmp"
set "TEMP=%SIM%\build\tmp"
if not exist "%TMP%" mkdir "%TMP%"

REM Find MSVC vcvars64.bat (OpenVAF uses MSVC link.exe for codegen)
set "VCVARS="
for %%E in (Enterprise Professional Community) do (
  for %%D in (C G) do (
    if exist "%%D:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=%%D:\Program Files\Microsoft Visual Studio\2022\%%E\VC\Auxiliary\Build\vcvars64.bat"
  )
)
if "%VCVARS%"=="" (
    echo error: cannot find Visual Studio 2022 vcvars64.bat
    exit /b 1
)
call "%VCVARS%" >nul 2>&1

REM tools dir first so openvaf-reloaded takes priority
set "PATH=%SIM%\tools;%PATH%"

echo === Compiling %1 with OpenVAF-Reloaded (OSDI 0.4) ===
"%SIM%\tools\openvaf-reloaded.exe" %1 -o %2
if errorlevel 1 (echo FAILED & exit /b 1)
echo === OK: %2 ===
dir %2
endlocal
