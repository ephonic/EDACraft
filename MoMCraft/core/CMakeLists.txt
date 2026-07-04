# =====================================================================
# mom_core —— C++ 计算核心静态库
# =====================================================================

# ---------- 依赖：Eigen（头文件库，通过 FetchContent 拉取） ----------
if(MOM_USE_EIGEN)
    include(FetchContent)
    # 锁定版本，避免上游变动破坏数值行为
    set(EIGEN_BUILD_DOC OFF CACHE BOOL "" FORCE)
    set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
    # 关闭 Eigen 子项目的测试/示例，仅取头文件
    set(EIGEN_BUILD_TESTING OFF CACHE BOOL "" FORCE)
    FetchContent_Declare(
        eigen
        GIT_REPOSITORY https://gitlab.com/libeigen/eigen.git
        GIT_TAG        3.4.0
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(eigen)
    # Eigen 顶层 target 为 Eigen3::Eigen；include 目录可由其 INTERFACE 提供
    if(TARGET Eigen3::Eigen)
        set(MOM_EIGEN_INCLUDE_DIR "")
    else()
        set(MOM_EIGEN_INCLUDE_DIR ${eigen_SOURCE_DIR})
    endif()
    message(STATUS "Eigen include: ${eigen_SOURCE_DIR}")
endif()

# ---------- 源文件 ----------
set(MOM_CORE_SOURCES
    src/common/types.cpp
    src/common/quadrature.cpp
    src/common/analytic.cpp
    src/sweep/frequency_sweep.cpp
    src/mesh/mesh.cpp
    src/mesh/trimesh.cpp
    src/mom/efie.cpp
    src/mom/rwg_assembly.cpp
    src/solver/dense.cpp
    src/solver/pfft.cpp
    src/microstrip.cpp
    src/tl_extract.cpp
    src/green/spectral.cpp
    src/green/poles.cpp
    src/green/branch.cpp
    src/green/layered_spatial.cpp
    src/green/qwe.cpp
    src/green/lc_extract.cpp
    src/green/dyadic.cpp
)

# ---------- 静态库 ----------
add_library(mom_core STATIC ${MOM_CORE_SOURCES})
add_library(mom::core ALIAS mom_core)

target_include_directories(mom_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${MOM_EIGEN_INCLUDE_DIR}
)

# 若 FetchContent 成功建出 Eigen3::Eigen，走其 INTERFACE include
if(MOM_USE_EIGEN AND TARGET Eigen3::Eigen)
    target_link_libraries(mom_core PRIVATE Eigen3::Eigen)
endif()

target_compile_features(mom_core PUBLIC cxx_std_17)

target_compile_definitions(mom_core PUBLIC
    $<$<BOOL:${MOM_USE_EIGEN}>:MOM_USE_EIGEN>
)

# OpenMP（装配 / 扫频并行）
if(MOM_ENABLE_OPENMP)
    find_package(OpenMP QUIET)
    if(OpenMP_CXX_FOUND)
        target_link_libraries(mom_core PUBLIC OpenMP::OpenMP_CXX)
        target_compile_definitions(mom_core PUBLIC MOM_HAS_OPENMP=1)
        message(STATUS "OpenMP enabled")
    else()
        message(STATUS "OpenMP not found; building serial core")
    endif()
endif()
