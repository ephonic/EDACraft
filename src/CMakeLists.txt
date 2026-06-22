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
    model/device_factory.cpp
    model/osdi/osdi_library.cpp
    model/osdi/osdi_client.cpp
)
set(RFSIM_ASSEMBLY_SOURCES
    assembly/matrix.cpp
    assembly/lu_solver.cpp
    assembly/klu_solver.cpp
    assembly/mna.cpp
    assembly/hb_jacobian.cpp
    assembly/gmres.cpp
    assembly/transient_assembly.cpp
)
set(RFSIM_SOLVER_SOURCES
    solver/dc_op.cpp
    solver/dc_sweep.cpp
    solver/ac_analysis.cpp
    solver/hb_solver.cpp
    solver/hb_nonlinear.cpp
    solver/time_stepper.cpp
    solver/shooting.cpp
)
set(RFSIM_OUTPUT_SOURCES
    output/hspice_out.cpp
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
target_link_libraries(rfsim_core PUBLIC SuiteSparse::KLU)

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
