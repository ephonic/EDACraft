# rfsim — 射频仿真器（Harmonic Balance + OpenVAF/OSDI）
# 详见 plan.md。本顶层 CMake 仅做项目级配置与子目录聚合。
cmake_minimum_required(VERSION 3.20)

project(rfsim
    VERSION 0.1.0
    DESCRIPTION "RF circuit simulator: Harmonic Balance + OpenVAF/OSDI"
    LANGUAGES CXX)

# ---- 全局编译选项 -----------------------------------------------------------
# plan.md §2.2: C++17 及以上，MSVC/GCC/Clang 三套均需通过。
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 构建类型默认 Release（数值仿真注重性能）
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

# 输出到统一目录便于运行
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# GCC/Clang 警告：严格但实用
add_compile_options(
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wall>
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wextra>
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wpedantic>
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wconversion>
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wshadow>
    $<$<CXX_COMPILER_ID:GNU,Clang,AppleClang>:-Wnon-virtual-dtor>)

# MSVC 用 UTF-8 源码 + C4267 等警告
if(MSVC)
    add_compile_options(/utf-8 /W4 /permissive-)
endif()

# 位置无关代码（便于后续构建共享库/插件）
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 测试使能（默认开）
option(RFSIM_BUILD_TESTS "Build unit tests with GoogleTest" ON)

# ---- 配置头 -----------------------------------------------------------------
configure_file(
    ${CMAKE_SOURCE_DIR}/cmake/rfsim_config.h.in
    ${CMAKE_BINARY_DIR}/generated/rfsim/rfsim_config.h
    @ONLY)

# ---- 子目录 -----------------------------------------------------------------
add_subdirectory(src)

if(RFSIM_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
