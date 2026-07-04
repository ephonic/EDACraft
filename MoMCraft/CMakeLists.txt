# =====================================================================
# mom — 互连线 S 参数提取（MoM + 多层介质格林函数）
# 顶层 CMake 配置
# =====================================================================
cmake_minimum_required(VERSION 3.16)

# CMAKE_PROJECT_VERSION 由 scikit-build-core 通过 --project-version 注入；
# 独立配置（cmake -S . -B build）时给一个回退。
if(NOT DEFINED PROJECT_VERSION AND NOT DEFINED CMAKE_PROJECT_VERSION)
    set(_MOM_FALLBACK_VERSION "0.0.1")
else()
    set(_MOM_FALLBACK_VERSION "0.0.1")
endif()

project(mom
    VERSION ${_MOM_FALLBACK_VERSION}
    LANGUAGES CXX
    DESCRIPTION "互连线 S 参数提取（MoM + 多层介质格林函数）"
)

# ---------- 全局选项 ----------
option(MOM_BUILD_PYTHON "构建 pybind11 Python 绑定（_mom 扩展）" ON)
option(MOM_BUILD_TESTS  "构建 C++ 单元测试（GoogleTest）" OFF)
option(MOM_ENABLE_OPENMP "启用 OpenMP 并行（矩阵装配 / 扫频）" ON)
option(MOM_USE_EIGEN    "启用 Eigen 线性代数后端" ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# 输出统一到一处，便于打包与测试
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# MSVC：UTF-8 源码、稳定数值
if(MSVC)
    add_compile_options(/utf-8 /permissive- /W3 /EHsc /bigobj)
    # Release 默认已含 /O2；浮点严格化避免数值漂移
    add_compile_definitions(_USE_MATH_DEFINES NOMINMAX)
endif()

# MinGW-w64：较新 GCC 默认 Win32 线程模型
if(MINGW)
    add_compile_options(-Wall -Wextra -Wno-unused-parameter)
endif()

# ---------- 模块路径 ----------
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake)

message(STATUS "mom ${PROJECT_VERSION} | ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "  python ext: ${MOM_BUILD_PYTHON} | tests: ${MOM_BUILD_TESTS} | OpenMP: ${MOM_ENABLE_OPENMP}")

# ---------- 子目录 ----------
add_subdirectory(core)

if(MOM_BUILD_PYTHON)
    add_subdirectory(bindings)
endif()

if(MOM_BUILD_TESTS)
    enable_testing()
    add_subdirectory(core/tests)
endif()
