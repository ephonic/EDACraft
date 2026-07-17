@echo off
REM rfsim build helper - MSVC toolchain (UCRT-aligned /MD for OpenVAF bsim4.dll)
REM
REM Background: bsim4.dll links UCRT (ucrtbase + VCRUNTIME140, i.e. MSVC /MD).
REM   Host must also use MSVC /MD so host and dll share the same ucrtbase heap.
REM   MinGW's msvcrt.dll is a legacy NT4-era CRT, incompatible with UCRT,
REM   triggering KI-2 cross-CRT heap corruption.
REM   See docs/known_issues.md KI-2 and plan0621-v4.md section 2.
REM
REM Workaround: user TEMP dir contains non-ASCII chars (Chinese), which breaks
REM   cl.exe (D8037 / "cannot open compiler intermediate file"). Redirect
REM   TMP/TEMP to an ASCII path under the project.
REM
REM Usage:
REM   build.bat configure   - first-time configure (Ninja + MSVC)
REM   build.bat build       - compile
REM   build.bat test        - build and run rfsim_tests
REM   build.bat clean       - clean

setlocal

set "SRC=G:\vibe-codeing\simulator"
set "BUILD=%SRC%\build"

REM ASCII temp dir to avoid non-ASCII username path issues (cl.exe D8037)
if not exist "%BUILD%\tmp" mkdir "%BUILD%\tmp"
set "TMP=%BUILD%\tmp"
set "TEMP=%BUILD%\tmp"

REM Enter MSVC build environment (cl/link/lib + Windows SDK prepended to PATH)
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

REM Use VS2022-bundled cmake/ninja (same toolchain, isolated from mingw)
set "VSROOT=G:\Program Files\Microsoft Visual Studio\2022\Enterprise"
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
