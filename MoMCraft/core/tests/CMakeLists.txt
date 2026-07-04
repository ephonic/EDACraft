# =====================================================================
# core/tests/ —— C++ 单元测试（GoogleTest）
#
# GoogleTest 通过 FetchContent 拉取。沙箱中 github.com 可能不可达，
# 优先用 gitlab 镜像；也允许通过 -DMOM_GTEST_SOURCE=<local path> 指定
# 已存在的 GoogleTest 源码目录（离线/内网构建）。
# =====================================================================
include(FetchContent)

if(NOT DEFINED MOM_GTEST_SOURCE)
    # 优先 gitlab（与 Eigen 同源，规避 github 不可达环境）
    set(MOM_GTEST_REPO "https://gitlab.com/yaoyuanyue/gtest-git-mirror.git" CACHE STRING "")
    set(MOM_GTEST_TAG  "v1.14.0" CACHE STRING "")
endif()

if(MOM_GTEST_SOURCE)
    FetchContent_Declare(googletest SOURCE_DIR ${MOM_GTEST_SOURCE})
else()
    FetchContent_Declare(
        googletest
        GIT_REPOSITORY ${MOM_GTEST_REPO}
        GIT_TAG        ${MOM_GTEST_TAG}
        GIT_SHALLOW    TRUE
    )
endif()

# Windows + MSVC：禁用 gtest 强制使用的 /W4（避免与上层 warning 级别冲突）
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_executable(mom_core_tests
    test_frequency_sweep.cpp
)
target_link_libraries(mom_core_tests
    PRIVATE mom::core GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(mom_core_tests)
