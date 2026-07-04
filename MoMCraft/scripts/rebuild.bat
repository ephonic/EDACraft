@echo off
REM =====================================================================
REM MoMCraft Windows 干净重建：清空 build/ + 旧 .pyd，重新编译并跑 pytest。
REM 探测 Python / MSVC，不硬编码机器路径。
REM =====================================================================
setlocal
cd /d "%~dp0\.."

set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
    echo [ERROR] 未找到 Python。
    exit /b 1
)

echo === Remove stale build + old _mom extension ===
if exist build rmdir /S /Q build
if exist py\mom\_mom*.pyd del /Q "py\mom\_mom*.pyd" 2>nul
if exist py\mom\*.so del /Q "py\mom\*.so" 2>nul

echo === Rebuild (editable) ===
%PYEXE% -m pip install -e . --no-build-isolation
if errorlevel 1 ( echo [ERROR] 构建失败 & exit /b 1 )

echo.
echo === Smoke ===
%PYEXE% -X faulthandler -c "import numpy as np; import mom; print('version', mom.__version__)"
echo SMOKE_EXIT=%errorlevel%

echo.
echo === pytest ===
%PYEXE% -m pytest tests/test_smoke.py -q
echo PYTEST_EXIT=%errorlevel%

endlocal
