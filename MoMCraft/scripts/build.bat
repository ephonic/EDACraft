@echo off
REM =====================================================================
REM MoMCraft Windows 构建：编译 _mom 扩展并就地安装（pip install -e .）。
REM
REM 本脚本不再硬编码任何机器路径，自动探测 Python / MSVC 环境。
REM
REM 环境要求：
REM   - Python 3.9+ （在 PATH 中，或用 py 启动器）
REM   - CMake 3.16+
REM   - C++17 编译器（MSVC 2019+/2022，或 MinGW-w64）
REM   - 首次构建需联网（CMake FetchContent 拉取 Eigen 3.4.0）
REM
REM 跨平台首选：直接  pip install -e .
REM （Windows 下本脚本等价于该命令的本地化封装）
REM =====================================================================
setlocal
cd /d "%~dp0\.."

REM --- 探测 Python ---
set "PYEXE="
where py >nul 2>&1 && set "PYEXE=py"
if not defined PYEXE ( where python >nul 2>&1 && set "PYEXE=python" )
if not defined PYEXE (
    echo [ERROR] 未找到 Python。请安装 Python 3.9+ 并加入 PATH，或使用 conda 环境。
    exit /b 1
)

echo === Build ^& install MoMCraft (editable) ===
%PYEXE% -m pip install -e .
if errorlevel 1 (
    echo [ERROR] 构建失败。请检查：CMake / Ninja / C++17 编译器是否已安装。
    exit /b 1
)

echo.
echo === Smoke test ===
%PYEXE% -c "import numpy as np; import mom; a=np.array([1.,2.,3.]); mom.square_inplace(a); print('ok', a, mom.__version__)"
if errorlevel 1 ( echo [ERROR] 冒烟测试失败 & exit /b 1 )

echo.
echo [OK] MoMCraft 构建成功。
endlocal
