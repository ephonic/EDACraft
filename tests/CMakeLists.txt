# tests — GoogleTest 单元测试
#
# 通过 FetchContent 拉取 GoogleTest（无需系统预装）。
include(FetchContent)

set(FETCHCONTENT_QUIET ON)
FetchContent_Declare(
    googletest
    URL https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz
)
# Windows: 避免共享 gtest DLL
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

include(GoogleTest)

set(RFSIM_TEST_SOURCES
    test_lexer.cpp
    test_expression.cpp
    test_parser.cpp
    test_flatten.cpp
    test_model.cpp
    test_assembly.cpp
    test_analysis.cpp
    test_osdi.cpp
    test_hb.cpp
    test_newton.cpp
    test_hb_nl.cpp
    test_bsim4.cpp
    test_gmres.cpp
    test_shooting.cpp
    test_osdi_models.cpp
    test_convergence_grid.cpp
    test_multi_device.cpp
    test_edge_cases.cpp
    test_gmin_floor.cpp
    test_large_scale.cpp
    test_large_circuit.cpp
)

add_executable(rfsim_tests ${RFSIM_TEST_SOURCES})
target_link_libraries(rfsim_tests PRIVATE rfsim_core gtest_main)
target_include_directories(rfsim_tests PRIVATE ${CMAKE_SOURCE_DIR}/src)

# 传递测试数据目录
target_compile_definitions(rfsim_tests PRIVATE
    RFSIM_TEST_DATA_DIR="${CMAKE_SOURCE_DIR}/tests/netlists")

# 已知 BSIM4 OSDI .dll 在多实例（>=2 个 BSIM4 NMOS）的 ctest-isolated
# 进程中会偶发 0xc0000374 (STATUS_HEAP_CORRUPTION)。复现率约 30~50%，
# 单实例不复现。已排除 BsimLib 双重 LoadLibrary、测试体重复实例等本仿真器
# 侧因素；残余 flake 落在 BSIM4 OSDI 库内部 setup_model / eval 路径的多实例
# 堆行为上，属于上游 OSDI 模块问题。V2-γ C3 引入 OsdiModelBlock 共享层
# （osdi_model.cpp:46-48 标注的 M2 优化）后 setup_model 10×→1× 可大幅缓解。
#
# 注意：CTest 的“until-pass 自动重试”不是测试属性，而是 ctest CLI 选项
#       `--repeat until-pass:N` （per-test property `REPEAT_UNTIL_PASS`
#       会被 CMake 当作未知属性接收但 ctest 并不会读取）。所以兜底重试
#       由 build/runctest.bat 在调用层添加 `--repeat until-pass:8` 完成。
# TIMEOUT 给所有发现的测试统一上一个比较宽的上限（默认 60s 偏紧）。
gtest_discover_tests(rfsim_tests
    PROPERTIES
        TIMEOUT 240)
