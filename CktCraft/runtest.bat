@echo off
REM Run rfsim_tests with optional gtest filter.
REM MSVC build produces self-contained exe (UCRT runtime), no extra DLL path needed.
setlocal
set "FILTER=%~1"
if "%FILTER%"=="" (
    "%~dp0build\bin\rfsim_tests.exe"
) else (
    "%~dp0build\bin\rfsim_tests.exe" --gtest_filter=%FILTER%
)
endlocal
