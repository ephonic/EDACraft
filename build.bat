@echo off
REM rfsim build helper
REM Workaround: user TEMP dir contains non-ASCII chars (Chinese), which breaks
REM   the mingw assembler when creating intermediate object files.
REM   Redirect TMP/TEMP to an ASCII path under the project to bypass.
REM Usage:
REM   build.bat configure   - first-time configure (Ninja)
REM   build.bat build       - compile
REM   build.bat test        - build and run tests
REM   build.bat clean       - clean

setlocal

set "MINGW=G:\msys64\mingw64\bin"
set "PATH=%MINGW%;%PATH%"

REM ASCII temp dir to avoid non-ASCII username path issues
if not exist "G:\vibe-codeing\simulator\build\tmp" mkdir "G:\vibe-codeing\simulator\build\tmp"
set "TMP=G:\vibe-codeing\simulator\build\tmp"
set "TEMP=G:\vibe-codeing\simulator\build\tmp"

set "SRC=G:\vibe-codeing\simulator"
set "BUILD=%SRC%\build"

if /i "%1"=="configure" goto configure
if /i "%1"=="build" goto build
if /i "%1"=="test" goto test
if /i "%1"=="clean" goto clean
goto usage

:configure
"%MINGW%\cmake.exe" -S "%SRC%" -B "%BUILD%" -G Ninja -DCMAKE_C_COMPILER="%MINGW%\gcc.exe" -DCMAKE_CXX_COMPILER="%MINGW%\g++.exe" -DCMAKE_MAKE_PROGRAM="%MINGW%\ninja.exe" -DCMAKE_BUILD_TYPE=Release
goto end

:build
"%MINGW%\cmake.exe" --build "%BUILD%" %2 %3 %4
goto end

:test
"%MINGW%\cmake.exe" --build "%BUILD%" --target rfsim_tests
if errorlevel 1 goto end
"%BUILD%\bin\rfsim_tests.exe"
goto end

:clean
"%MINGW%\cmake.exe" --build "%BUILD%" --target clean
goto end

:usage
echo Usage: build.bat [configure^|build^|test^|clean]

:end
endlocal
