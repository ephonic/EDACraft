# SuiteSparseKLU.cmake — 通过 FetchContent 集成 SuiteSparse 的 KLU 稀疏直接求解器
#
# 用途：
#   - Shooting/Transient 内层 Newton 与外层 monodromy 雅可比都是稀疏不对称矩阵，
#     用稠密 LU(O(n^3)) 不可扩展。改用 KLU(分块三角化 + 部分选主元 + AMD 排序)
#     能在大型电路上拿到接近最优的稀疏直接因子化复杂度。
#   - HB 仍走 GMRES + 预条件子 + Krylov 子空间复用（HB 雅可比块结构非 KLU 友好）。
#
# 集成策略：
#   仅启用 KLU 必需的 SuiteSparse 子项目: suitesparse_config + amd + colamd + btf + klu
#   - 关闭 Fortran/OpenMP/CUDA 依赖（保持纯 C，免装外部 BLAS/LAPACK）
#   - 静态库（避免 .dll 分发问题）
#   - 关闭 demo / test，缩短首次构建时间
#
# 暴露目标: SuiteSparse::KLU （包含 KLU 头与所有必需的依赖链接）
#
# 详见 plan.md §4.x（Shooting 求解器替换计划）。

include_guard(GLOBAL)
include(FetchContent)

# ---- SuiteSparse 子项目过滤 -------------------------------------------------
# 必须在 FetchContent_MakeAvailable 之前设为 CACHE，才会被子目录识别。
set(SUITESPARSE_ENABLE_PROJECTS "suitesparse_config;amd;colamd;btf;klu"
    CACHE STRING "SuiteSparse subprojects to build" FORCE)

# 关闭 Fortran/OpenMP/CUDA：保证纯 C 构建路径在 MinGW-w64 上无外部依赖
set(SUITESPARSE_USE_FORTRAN OFF CACHE BOOL "" FORCE)
set(SUITESPARSE_USE_OPENMP  OFF CACHE BOOL "" FORCE)
set(SUITESPARSE_USE_CUDA    OFF CACHE BOOL "" FORCE)
set(SUITESPARSE_USE_64BIT_BLAS OFF CACHE BOOL "" FORCE)

# 不构建 SuiteSparse 自带的 demo / test
set(SUITESPARSE_DEMOS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING     OFF CACHE BOOL "" FORCE)

# KLU 默认会拉 CHOLMOD（用于额外的 ordering），CHOLMOD 又依赖 BLAS/LAPACK。
# 我们只用 KLU 的 BTF+AMD+部分选主元路径，关掉 CHOLMOD 依赖能彻底摆脱 BLAS。
set(KLU_USE_CHOLMOD     OFF CACHE BOOL "" FORCE)
set(UMFPACK_USE_CHOLMOD OFF CACHE BOOL "" FORCE)

# 静态库为主（避免 dll 分发；调试时可改为 ON+ON）
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_STATIC_LIBS ON  CACHE BOOL "" FORCE)

# SuiteSparseConfig 可能尝试找 BLAS；强制关闭其对外部 BLAS 的依赖
set(NSTATIC OFF CACHE BOOL "" FORCE)

# KLU 本身不调用 BLAS，但 SuiteSparse_config 的 SuiteSparseBLAS.cmake
# 默认会 find_package(BLAS REQUIRED) 失败而中断 configure。
# 走它的"用户已提供 BLAS 变量"分支（line 65 的 DEFINED 早返回）以跳过查找。
# BLA_VENDOR 必须设非空字符串（避免 SuiteSparse__blas_threading 里
# string(REGEX MATCH ...) 因空入参而失败）；"Generic" 是安全占位。
set(BLAS_LIBRARIES "" CACHE STRING "BLAS placeholder for KLU-only build" FORCE)
set(BLA_VENDOR     "Generic" CACHE STRING "BLAS placeholder vendor" FORCE)

# ---- FetchContent 声明 ------------------------------------------------------
# 优先用本地源码目录 / zip（避免 GitHub 直连慢/卡）；若均不存在则从 GitHub Release 下载。
# 查找顺序：
#   1. 环境变量 RFSIM_SUITESPARSE_DIR 指向已解压的源码目录（开发推荐，最快）
#   2. 环境变量 RFSIM_SUITESPARSE_ZIP 指向 zip 绝对路径
#   3. <release_root>/SuiteSparse.zip（release 目录内）
#   4. <release_root>/../SuiteSparse.zip（仓库根或同级目录）
#   5. 从 GitHub Release 下载 SuiteSparse v7.7.0 源码包
#
# Linux 离线构建：提前放置 zip 并设 RFSIM_SUITESPARSE_ZIP，
# 或设 RFSIM_SUITESPARSE_URL 指向内网镜像。
set(_ss_dir "")
set(_ss_zip "")
if(DEFINED ENV{RFSIM_SUITESPARSE_DIR} AND EXISTS "$ENV{RFSIM_SUITESPARSE_DIR}/CMakeLists.txt")
    set(_ss_dir "$ENV{RFSIM_SUITESPARSE_DIR}")
elseif(DEFINED ENV{RFSIM_SUITESPARSE_ZIP} AND EXISTS "$ENV{RFSIM_SUITESPARSE_ZIP}")
    set(_ss_zip "$ENV{RFSIM_SUITESPARSE_ZIP}")
elseif(EXISTS "${CMAKE_SOURCE_DIR}/SuiteSparse.zip")
    set(_ss_zip "${CMAKE_SOURCE_DIR}/SuiteSparse.zip")
elseif(EXISTS "${CMAKE_SOURCE_DIR}/../SuiteSparse.zip")
    set(_ss_zip "${CMAKE_SOURCE_DIR}/../SuiteSparse.zip")
endif()

if(_ss_dir)
    FetchContent_Declare(
        SuiteSparse
        SOURCE_DIR "${_ss_dir}"
    )
elseif(_ss_zip)
    FetchContent_Declare(
        SuiteSparse
        URL        "${_ss_zip}"
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
else()
    set(_ss_url "https://github.com/DrTimothyAldenDavis/SuiteSparse/archive/refs/tags/v7.7.0.tar.gz")
    if(DEFINED ENV{RFSIM_SUITESPARSE_URL})
        set(_ss_url "$ENV{RFSIM_SUITESPARSE_URL}")
    endif()
    FetchContent_Declare(
        SuiteSparse
        URL        "${_ss_url}"
        DOWNLOAD_EXTRACT_TIMESTAMP TRUE
    )
endif()

FetchContent_MakeAvailable(SuiteSparse)

# ---- 暴露统一目标 SuiteSparse::KLU ------------------------------------------
# 注：SuiteSparse v7.x dev 分支用直接的目标名 KLU/KLU_static（非 namespaced）。
# 我们 BUILD_SHARED_LIBS=OFF + BUILD_STATIC_LIBS=ON，所以 KLU_static 是实际目标。
# 它的 PUBLIC link 已经包含 BTF_static / AMD_static / COLAMD_static / SuiteSparseConfig_static
# 与 PUBLIC include directories；这里只做项目内别名以保持调用方代码可读。
if(TARGET KLU_static)
    if(NOT TARGET SuiteSparse::KLU)
        add_library(SuiteSparse::KLU INTERFACE IMPORTED)
        target_link_libraries(SuiteSparse::KLU INTERFACE KLU_static)
    endif()
elseif(TARGET KLU)
    # 回退：动态库构建路径
    if(NOT TARGET SuiteSparse::KLU)
        add_library(SuiteSparse::KLU INTERFACE IMPORTED)
        target_link_libraries(SuiteSparse::KLU INTERFACE KLU)
    endif()
else()
    message(FATAL_ERROR "SuiteSparse KLU target not found after FetchContent_MakeAvailable")
endif()

# ---- MSVC 下降低 SuiteSparse 子项目警告噪声 --------------------------------
# SuiteSparse 上游已支持 MSVC CI (root-cmakelists-msvc.yaml)，但 /W4 在其 C 源
# (printf / sign-compare / unused-param) 上噪声大；KLU/AMD 等 C11 源本身已干净，
# 这里对 SuiteSparseConfig 做保险降噪，确保 MSVC /W4 顶层默认不被这些子项目污染。
if(MSVC)
    foreach(tgt
            KLU_static AMD_static BTF_static COLAMD_static
            KLU AMD BTF COLAMD
            SuiteSparseConfig_static SuiteSparseConfig)
        if(TARGET ${tgt})
            target_compile_options(${tgt} PRIVATE /W0)
        endif()
    endforeach()
endif()
