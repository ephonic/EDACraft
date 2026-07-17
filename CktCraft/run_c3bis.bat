@echo off
REM C3-bis diagnostic runner (post-restructure)
REM Sets RFSIM_FORCE_C3BIS=1 then runs gtest filter on rfsim_tests
setlocal
set "RFSIM_FORCE_C3BIS=1"
set "SRC=G:\vibe-codeing\simulator"
set "BUILD=%SRC%\build"
if not exist "%BUILD%\tmp" mkdir "%BUILD%\tmp"
set "TMP=%BUILD%\tmp"
set "TEMP=%BUILD%\tmp"
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
set "VSROOT=G:\Program Files\Microsoft Visual Studio\2022\Enterprise"
set "PATH=%VSROOT%\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;%PATH%"
"%BUILD%\bin\rfsim_tests.exe" --gtest_filter=MultiDevice.C3bis_* 2>&1
endlocal
