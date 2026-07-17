@echo off
REM Run rfsim_tests with optional gtest filter; ensures mingw64 DLLs are on PATH.
setlocal
set "MINGW=G:\msys64\mingw64\bin"
set "PATH=%MINGW%;%PATH%"
set "FILTER=%~1"
if "%FILTER%"=="" (
    "%~dp0build\bin\rfsim_tests.exe"
) else (
    "%~dp0build\bin\rfsim_tests.exe" --gtest_filter=%FILTER%
)
endlocal
