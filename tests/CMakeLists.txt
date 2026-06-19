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
)

add_executable(rfsim_tests ${RFSIM_TEST_SOURCES})
target_link_libraries(rfsim_tests PRIVATE rfsim_core gtest_main)
target_include_directories(rfsim_tests PRIVATE ${CMAKE_SOURCE_DIR}/src)

# 传递测试数据目录
target_compile_definitions(rfsim_tests PRIVATE
    RFSIM_TEST_DATA_DIR="${CMAKE_SOURCE_DIR}/tests/netlists")

gtest_discover_tests(rfsim_tests)
