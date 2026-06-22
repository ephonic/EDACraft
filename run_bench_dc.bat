@echo off
setlocal
set "RFSIM_BENCH_JSON=1"
set "RFSIM_BENCH_DIR=G:\vibe-codeing\simulator\build"
"G:\vibe-codeing\simulator\build\bin\rfsim_tests.exe" --gtest_filter=MultiDevice.EightFingerBalanced:LargeScaleBsim4.SelfBiasedCascodeStack5 2>&1
endlocal
