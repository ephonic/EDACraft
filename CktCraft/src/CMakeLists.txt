# rfsim 核心库：聚合各模块成一个静态库 rfsim_core
# 模块划分对应 plan.md §2.1 流水线各层。

# ---- 源文件按模块分组 -------------------------------------------------------
set(RFSIM_PARSER_SOURCES
    parser/token.cpp
    parser/ast.cpp
    parser/parser.cpp
    parser/expression.cpp
)

set(RFSIM_CIRCUIT_SOURCES
    circuit/node_table.cpp
    circuit/circuit.cpp
    circuit/flatten.cpp
)

# M2+ 模块占位（暂为空，避免空目录报错时再启用）
set(RFSIM_MODEL_SOURCES
    model/builtin_devices.cpp
    model/osdi_model.cpp
    model/sparam_device.cpp
    model/device_factory.cpp
    model/osdi/osdi_library.cpp
    model/osdi/osdi_client.cpp
)
set(RFSIM_ASSEMBLY_SOURCES
    assembly/matrix.cpp
    assembly/linear_solver_factory.cpp
    assembly/solver_benchmark.cpp
    assembly/iterative_solver.cpp
    assembly/lu_solver.cpp
    assembly/mna.cpp
    assembly/hb_jacobian.cpp
    assembly/gmres.cpp
    assembly/transient_assembly.cpp
)
# Phase A1-5：KLU 求解器源仅在 RFSIM_USE_KLU=ON 时编译。
# KluZSolver（AC 分析用）同样依赖 KLU，一并门控。
if(RFSIM_USE_KLU)
    list(APPEND RFSIM_ASSEMBLY_SOURCES
        assembly/klu_solver.cpp
        assembly/klu_z_solver.cpp)
endif()
# UMFPACK 求解器（经验性求解器选择候选）。需 BLAS（用户通过 RFSIM_BLAS_LIB 提供）。
if(RFSIM_USE_UMFPACK)
    list(APPEND RFSIM_ASSEMBLY_SOURCES assembly/umfpack_solver.cpp)
endif()
set(RFSIM_SOLVER_SOURCES
    solver/dc_op.cpp
    solver/dc_sweep.cpp
    solver/ac_analysis.cpp
    solver/hb_solver.cpp
    solver/hb_nonlinear.cpp
    solver/nonlinear_damping.cpp
    solver/time_stepper.cpp
    solver/shooting.cpp
    solver/noise_analysis.cpp
)

# MOR (Model Order Reduction) — amor RC 互连线降阶（可选，需 RFSIM_USE_MOR=ON + ARPACK）
set(RFSIM_MOR_SOURCES
    mor/amor_amor.cpp
    mor/amor_cap.cpp
    mor/amor_ckt.cpp
    mor/amor_eigs.cpp
    mor/amor_element.cpp
    mor/amor_linear_solver.cpp
    mor/amor_node_list.cpp
    mor/amor_res.cpp
    mor/amor_subckt.cpp
    mor/amor_timer.cpp
    mor/amor_unit.cpp
    mor/mor_wrapper.cpp
)
if(RFSIM_USE_MOR)
    list(APPEND RFSIM_SOLVER_SOURCES ${RFSIM_MOR_SOURCES})
else()
    # mor_wrapper.cpp 也在无 MOR 时编译（stub 返回 false）
    list(APPEND RFSIM_SOLVER_SOURCES mor/mor_wrapper.cpp)
endif()
set(RFSIM_OUTPUT_SOURCES
    output/hspice_out.cpp
    output/waveform_export.cpp
    output/measure.cpp
)

# S 参数工具
set(RFSIM_SPARAM_SOURCES
    sparam/touchstone.cpp
    sparam/vector_fit.cpp
    sparam/stability.cpp
)

# V2-γ C3: 性能计数器（RFSIM_BENCH_JSON=1 启用；Windows 用 Psapi 取 RSS）
set(RFSIM_UTIL_SOURCES
    util/bench.cpp
)

add_library(rfsim_core STATIC
    ${RFSIM_PARSER_SOURCES}
    ${RFSIM_CIRCUIT_SOURCES}
    ${RFSIM_MODEL_SOURCES}
    ${RFSIM_ASSEMBLY_SOURCES}
    ${RFSIM_SPARAM_SOURCES}
    ${RFSIM_SOLVER_SOURCES}
    ${RFSIM_OUTPUT_SOURCES}
    ${RFSIM_UTIL_SOURCES}
)

target_include_directories(rfsim_core
    PUBLIC
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_BINARY_DIR}/generated
)

# Shooting 内层 Newton + 外层 monodromy 用 KLU 稀疏直接求解器（详见
# cmake/SuiteSparseKLU.cmake）。HB 走 GMRES + 预条件子，不依赖 KLU。
# Phase A1-5：RFSIM_USE_KLU=ON 时链接 KLU 并定义宏；OFF 时整库退化为稠密 LU。
if(RFSIM_USE_KLU)
    target_link_libraries(rfsim_core PUBLIC SuiteSparse::KLU)
    target_compile_definitions(rfsim_core PUBLIC RFSIM_USE_KLU)
endif()
# UMFPACK 链接 + 宏。UMFPACK 需要 BLAS（用户提供的 RFSIM_BLAS_LIB 已在
# cmake/SuiteSparseKLU.cmake 内设为 BLAS_LIBRARIES）。
# BLAS 作为 PUBLIC 链接：UMFPACK_static 引用 BLAS 符号，rfsim_tests/rfsim_cli
# 链接 rfsim_core 时需传递 BLAS（SuiteSparse::UMFPACK 的 BLAS 依赖不自动透传）。
if(RFSIM_USE_UMFPACK)
    target_link_libraries(rfsim_core PUBLIC SuiteSparse::UMFPACK)
    target_compile_definitions(rfsim_core PUBLIC RFSIM_USE_UMFPACK)
    if(DEFINED BLAS_LIBRARIES AND NOT "${BLAS_LIBRARIES}" STREQUAL "")
        target_link_libraries(rfsim_core PUBLIC ${BLAS_LIBRARIES})
    endif()
endif()

# 优化项3：OpenMP 并行器件 eval。RFSIM_USE_OPENMP=ON 时启用。
if(RFSIM_USE_OPENMP)
    find_package(OpenMP REQUIRED)
    target_link_libraries(rfsim_core PUBLIC OpenMP::OpenMP_CXX)
    target_compile_definitions(rfsim_core PUBLIC RFSIM_USE_OPENMP)
endif()

# MOR (amor RC 降阶)：需 ARPACK + UMFPACK。
# ARPACK-ng 提供 arpack-ng::arpack 目标（Fortran 库）；UMFPACK 复用仓库的。
if(RFSIM_USE_MOR)
    target_compile_definitions(rfsim_core PUBLIC RFSIM_USE_MOR)
    target_link_libraries(rfsim_core PUBLIC arpack-ng::arpack)
    # MOR 的 amor_linear_solver 用 UMFPACK（直接 include <umfpack.h>）
    if(RFSIM_USE_UMFPACK)
        target_compile_definitions(rfsim_core PUBLIC RFSIM_USE_MOR_UMFPACK)
    endif()
endif()

# V2-γ C3: bench.cpp 在 Windows 用 Psapi 取 RSS
if(MSVC)
    target_link_libraries(rfsim_core PUBLIC Psapi)
endif()

# C++17
target_compile_features(rfsim_core PUBLIC cxx_std_17)

# 命令行入口（M1: 解析网表并打印结构化电路描述，作为验证手段）
add_executable(rfsim_cli cli/main.cpp)
target_link_libraries(rfsim_cli PRIVATE rfsim_core)
set_target_properties(rfsim_cli PROPERTIES OUTPUT_NAME rfsim)

# 诊断探针：探测 BSIM4 非线性 HB 收敛行为（非正式测试，仅手动运行）
# 默认 OFF；用 cmake -DRFSIM_BUILD_PROBES=ON 或环境变量打开。
if(RFSIM_BUILD_PROBES OR DEFINED ENV{RFSIM_BUILD_PROBES})
    if(EXISTS ${CMAKE_SOURCE_DIR}/probe_hb.cpp)
        add_executable(probe_hb ${CMAKE_SOURCE_DIR}/probe_hb.cpp)
        target_link_libraries(probe_hb PRIVATE rfsim_core)
    endif()
    if(EXISTS ${CMAKE_SOURCE_DIR}/probe_react.cpp)
        add_executable(probe_react ${CMAKE_SOURCE_DIR}/probe_react.cpp)
        target_link_libraries(probe_react PRIVATE rfsim_core)
    endif()
    if(EXISTS ${CMAKE_SOURCE_DIR}/probe_react2.cpp)
        add_executable(probe_react2 ${CMAKE_SOURCE_DIR}/probe_react2.cpp)
        target_link_libraries(probe_react2 PRIVATE rfsim_core)
    endif()
    add_executable(probe_flake ${CMAKE_SOURCE_DIR}/probe_flake.cpp)
    target_link_libraries(probe_flake PRIVATE rfsim_core)
    if(MSVC)
        # 生成 map file 与 PDB，用于把 VEH 抓到的 RVA 映射到函数名
        target_link_options(probe_flake PRIVATE /MAP /MAPFILE:probe_flake.map /DEBUG:FULL)
        target_compile_options(probe_flake PRIVATE /Zi /Od)
    endif()
endif()
