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

add_library(rfsim_core STATIC
    ${RFSIM_PARSER_SOURCES}
    ${RFSIM_CIRCUIT_SOURCES}
    ${RFSIM_MODEL_SOURCES}
    ${RFSIM_ASSEMBLY_SOURCES}
    ${RFSIM_SOLVER_SOURCES}
    ${RFSIM_OUTPUT_SOURCES}
)

target_include_directories(rfsim_core
    PUBLIC
        ${CMAKE_SOURCE_DIR}/src
        ${CMAKE_BINARY_DIR}/generated
)

# C++17
target_compile_features(rfsim_core PUBLIC cxx_std_17)

# 命令行入口（M1: 解析网表并打印结构化电路描述，作为验证手段）
add_executable(rfsim_cli cli/main.cpp)
target_link_libraries(rfsim_cli PRIVATE rfsim_core)
set_target_properties(rfsim_cli PROPERTIES OUTPUT_NAME rfsim)
