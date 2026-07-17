@echo off
REM rfsim build helper - MSVC toolchain (UCRT-aligned /MD for OpenVAF bsim4.dll)
REM
REM bsim4.dll links UCRT (ucrtbase + VCRUNTIME140, i.e. MSVC /MD).
REM Host must also use MSVC /MD so host and dll share the same ucrtbase heap.
REM MinGW msvcrt.dll is legacy NT4-era CRT, incompatible with UCRT,
REM triggering cross-CRT heap corruption. See Development_guide.md.
REM
REM Workaround: non-ASCII TEMP breaks cl.exe (D8037). Redirect TMP/TEMP.
REM
REM Usage:
REM   build.bat configure   - first-time configure (Ninja + MSVC)
REM   build.bat build       - compile
REM   build.bat test        - build and run rfsim_tests
REM   build.bat clean       - clean

setlocal

REM SRC = script directory (portable, no absolute path dependency)
set "SRC=%~dp0"
if "%SRC:~-1%"=="\" set "SRC=%SRC:~0,-1%"
set "BUILD=%SRC%\build"

REM ASCII temp dir to avoid non-ASCII username path issues (cl.exe D8037)
if not exist "%BUILD%\tmp" mkdir "%BUILD%\tmp"
set "TMP=%BUILD%\tmp"
set "TEMP=%BUILD%\tmp"

REM Find MSVC vcvars64.bat (VS2022 Community/Professional/Enterprise)
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

REM Use VS2022-bundled cmake/ninja (same toolchain, isolated from mingw)
set "VSROOT=%VCVARS:\VC\Auxiliary\Build\vcvars64.bat=%"
set "PATH=%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"

if /i "%1"=="configure" goto configure
if /i "%1"=="build" goto build
if /i "%1"=="test" goto test
if /i "%1"=="clean" goto clean
goto usage

:configure
cmake -S "%SRC%" -B "%BUILD%" -G Ninja ^
    -DCMAKE_C_COMPILER=cl ^
    -DCMAKE_CXX_COMPILER=cl ^
    -DCMAKE_BUILD_TYPE=Release ^
    -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL ^
    -DFETCHCONTENT_QUIET=OFF
goto end

:build
cmake --build "%BUILD%" %2 %3 %4
goto end

:test
cmake --build "%BUILD%" --target rfsim_tests
if errorlevel 1 goto end
"%BUILD%\bin\rfsim_tests.exe"
goto end

:clean
cmake --build "%BUILD%" --target clean
goto end

:usage
echo Usage: build.bat [configure^|build^|test^|clean]

:end
endlocal
