# rfsim — 射频仿真器（Harmonic Balance + OpenVAF/OSDI）
# 详见 plan.md。本顶层 CMake 仅做项目级配置与子目录聚合。
cmake_minimum_required(VERSION 3.22)  # SuiteSparse 7.x 要求 >=3.22

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

# MSVC 工具链：必须 /MD 与 OpenVAF 生成的 bsim4.dll (UCRT + VCRUNTIME140) 对齐，
# 否则 host (msvcrt 静态 / mingw msvcrt) 与 dll (ucrtbase 动态) 跨堆 → 触发 KI-2
# cross-CRT 堆腐败（osdi_log msg free 等场景）。详见 plan0621-v4.md §2 与
# docs/known_issues.md KI-2。/permissive- 与 /W4 仅作用 C++，避免下渗到 KLU/AMD
# 等纯 C 子项目（C 源走 /W1 降噪）。
if(MSVC)
    set(CMAKE_MSVC_RUNTIME_LIBRARY
        "MultiThreaded$<$<CONFIG:Debug>:Debug>DLL")

    add_compile_options(
        /utf-8                              # 源/执行字符集 UTF-8（无 BOM）
        /Zc:__cplusplus                     # __cplusplus 报真实 C++ 版本
        /Zc:preprocessor                    # 标准 conforming 预处理器
        $<$<COMPILE_LANGUAGE:CXX>:/permissive->
        $<$<COMPILE_LANGUAGE:CXX>:/W4>
        $<$<COMPILE_LANGUAGE:C>:/W1>        # KLU/AMD 等 C 源降噪
        /wd4244 /wd4267 /wd4305             # size_t↔int / double→float 隐式转换
        /wd4191                             # FARPROC → 函数指针 unsafe cast (GetProcAddress)
        /wd4127                             # gtest 宏中 (cond) 常量条件
        /wd4459)                            # 局部变量屏蔽上层声明

    add_compile_definitions(
        _CRT_SECURE_NO_WARNINGS             # getenv / fprintf 等不被 deprecate
        _WINSOCK_DEPRECATED_NO_WARNINGS)
endif()

# 位置无关代码（便于后续构建共享库/插件）
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 测试使能（默认开）
option(RFSIM_BUILD_TESTS "Build unit tests with GoogleTest" ON)

# Phase A1-5：KLU 稀疏直接求解器可选。默认 ON（保持现有构建行为）。
# OFF 时：cmake/SuiteSparseKLU.cmake 不 include，klu_solver.cpp/klu_z_solver.cpp
# 不编译，rfsim_core 不定义 RFSIM_USE_KLU；linear_solver_factory 的 Auto 策略
# 与显式 Klu 请求都回退到 DenseLu。AC 分析（KluZSolver）在 OFF 时不可用——
# 此时 AC 测试会跳过（依赖门控）。
option(RFSIM_USE_KLU "Use SuiteSparse KLU sparse direct solver" ON)

# 优化项3：器件 eval 并行化（OpenMP）。默认 OFF——MSVC mingw OpenMP 与 OSDI DLL
# 的线程安全需验证。ON 时在 assembleTransient 的器件循环加 #pragma omp parallel for。
# 并行收益主要在大电路（器件多）transient/HB。
option(RFSIM_USE_OPENMP "Enable OpenMP parallel device eval" OFF)

# UMFPACK 稀疏直接求解器（multifrontal + BLAS-3）。作为经验性求解器选择的候选。
# 默认 OFF（需用户提供 BLAS 库 RFSIM_BLAS_LIB）。ON 时需 -DRFSIM_BLAS_LIB=<path>。
option(RFSIM_USE_UMFPACK "Use SuiteSparse UMFPACK (requires BLAS via RFSIM_BLAS_LIB)" OFF)

# ---- 配置头 -----------------------------------------------------------------
configure_file(
    ${CMAKE_SOURCE_DIR}/cmake/rfsim_config.h.in
    ${CMAKE_BINARY_DIR}/generated/rfsim/rfsim_config.h
    @ONLY)

# ---- 第三方依赖：SuiteSparse KLU（Shooting 稀疏直接求解器）------------------
if(RFSIM_USE_KLU)
    include(${CMAKE_SOURCE_DIR}/cmake/SuiteSparseKLU.cmake)
endif()

# ---- 子目录 -----------------------------------------------------------------
add_subdirectory(src)

if(RFSIM_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()
