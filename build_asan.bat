@echo off
REM build_asan.bat — build rfsim with MSVC AddressSanitizer for KI-3 debugging
REM ASAN catches host-side heap-buffer-overflow/use-after-free/stack-overflow
REM at the first offending instruction with full stack trace.
REM Note: ASAN cannot instrument dynamically-loaded dlls (bsim4.dll etc.) built
REM by OpenVAF — but the host crash we're hunting happens in host code
REM (solveDcOp/assemble/OsdiClient::evalDC), so ASAN on host is sufficient.
setlocal

set "SRC=G:\vibe-codeing\simulator"
set "BUILD=%SRC%\build_asan"

if not exist "%BUILD%\tmp" mkdir "%BUILD%\tmp"
set "TMP=%BUILD%\tmp"
set "TEMP=%BUILD%\tmp"

call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1

set "VSROOT=G:\Program Files\Microsoft Visual Studio\2022\Enterprise"
set "PATH=%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"

if /i "%1"=="configure" goto configure
if /i "%1"=="build" goto build
if /i "%1"=="test" goto test
goto usage

:configure
cmake -S "%SRC%" -B "%BUILD%" -G Ninja ^
    -DCMAKE_C_COMPILER=cl ^
    -DCMAKE_CXX_COMPILER=cl ^
    -DCMAKE_BUILD_TYPE=Debug ^
    -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL ^
    -DCMAKE_CXX_FLAGS="/fsanitize=address /Zi /Od /MDd" ^
    -DCMAKE_C_FLAGS="/fsanitize=address /Zi /Od /MDd" ^
    -DCMAKE_EXE_LINKER_FLAGS="/INCREMENTAL:NO" ^
    -DFETCHCONTENT_QUIET=OFF
goto end

:build
cmake --build "%BUILD%" --target rfsim_tests %2 %3
goto end

:test
cmake --build "%BUILD%" --target rfsim_tests
if errorlevel 1 goto end
set "RFSIM_FORCE_HEAVY=1"
set "RFSIM_FORCE_C3BIS=1"
"%BUILD%\bin\rfsim_tests.exe" %2 %3 %4 %5
goto end

:usage
echo Usage: build_asan.bat [configure^|build^|test] [gtest args...]

:end
endlocal
