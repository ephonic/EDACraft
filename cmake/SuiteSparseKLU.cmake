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
# KLU 核心：suitesparse_config + amd + colamd + btf + klu
# UMFPACK（可选，RFSIM_USE_UMFPACK=ON）：额外需要 umfpack 子项目 + BLAS。
if(RFSIM_USE_UMFPACK)
    set(SUITESPARSE_ENABLE_PROJECTS "suitesparse_config;amd;colamd;btf;klu;umfpack"
        CACHE STRING "SuiteSparse subprojects to build" FORCE)
else()
    set(SUITESPARSE_ENABLE_PROJECTS "suitesparse_config;amd;colamd;btf;klu"
        CACHE STRING "SuiteSparse subprojects to build" FORCE)
endif()

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
#
# RFSIM_USE_UMFPACK=ON 时 UMFPACK 真实调用 BLAS-3（dgemm/dgemv/dtrsm），
# 此时 KLU-only 的空占位会导致链接失败（未解析 BLAS 符号）。用户需提供
# RFSIM_BLAS_LIB（MSVC 兼容的 BLAS 库路径，如 OpenBLAS/MKL）。
if(RFSIM_USE_UMFPACK AND RFSIM_BLAS_LIB)
    # 真实 BLAS：用用户提供的库
    set(BLAS_LIBRARIES "${RFSIM_BLAS_LIB}" CACHE STRING "BLAS library for UMFPACK" FORCE)
    set(BLA_VENDOR     "Generic" CACHE STRING "" FORCE)
else()
    # KLU-only：空占位跳过 BLAS 查找
    set(BLAS_LIBRARIES "" CACHE STRING "BLAS placeholder for KLU-only build" FORCE)
    set(BLA_VENDOR     "Generic" CACHE STRING "BLAS placeholder vendor" FORCE)
endif()

# ---- FetchContent 声明 ------------------------------------------------------
# 注：本地 zip 路径（用户手动下载，避免 GitHub 直连慢/卡）。
# CMake 的 FetchContent + URL 会自动解压；若顶层有单一目录（如 SuiteSparse-dev/），
# 它会被作为 SOURCE_DIR。
FetchContent_Declare(
    SuiteSparse
    URL        ${CMAKE_SOURCE_DIR}/../SuiteSparse.zip
    DOWNLOAD_EXTRACT_TIMESTAMP TRUE
)

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

# ---- UMFPACK 目标别名（RFSIM_USE_UMFPACK=ON 时）----------------------------
if(RFSIM_USE_UMFPACK)
    if(TARGET UMFPACK_static)
        if(NOT TARGET SuiteSparse::UMFPACK)
            add_library(SuiteSparse::UMFPACK INTERFACE IMPORTED)
            target_link_libraries(SuiteSparse::UMFPACK INTERFACE UMFPACK_static)
        endif()
    elseif(TARGET UMFPACK)
        if(NOT TARGET SuiteSparse::UMFPACK)
            add_library(SuiteSparse::UMFPACK INTERFACE IMPORTED)
            target_link_libraries(SuiteSparse::UMFPACK INTERFACE UMFPACK)
        endif()
    else()
        message(WARNING "RFSIM_USE_UMFPACK=ON but UMFPACK target not found; UMFPACK disabled")
        set(RFSIM_USE_UMFPACK OFF CACHE BOOL "" FORCE)
    endif()
endif()

# ---- MSVC 下降低 SuiteSparse 子项目警告噪声 --------------------------------
# SuiteSparse 上游已支持 MSVC CI (root-cmakelists-msvc.yaml)，但 /W4 在其 C 源
# (printf / sign-compare / unused-param) 上噪声大；KLU/AMD 等 C11 源本身已干净，
# 这里对 SuiteSparseConfig 做保险降噪，确保 MSVC /W4 顶层默认不被这些子项目污染。
if(MSVC)
    foreach(tgt
            KLU_static AMD_static BTF_static COLAMD_static
            KLU AMD BTF COLAMD
            UMFPACK_static UMFPACK
            SuiteSparseConfig_static SuiteSparseConfig)
        if(TARGET ${tgt})
            target_compile_options(${tgt} PRIVATE /W0)
        endif()
    endforeach()
endif()
