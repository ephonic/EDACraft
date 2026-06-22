@echo off
call "G:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
cl /nologo /EHsc /utf-8 /I src\model\osdi /Fe:tools\read_desc.exe tools\offsetof_probe.cpp 2>nul
