@echo off
setlocal
set "MINGW=G:\msys64\mingw64\bin"
set "PATH=%MINGW%;%PATH%"
set "RFSIM_TEST_HEAVY=1"
set "RFSIM_FORCE_HEAVY=1"
"%~dp0build\bin\rfsim_tests.exe" --gtest_filter=%1
endlocal
