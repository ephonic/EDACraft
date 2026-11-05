cmake_minimum_required(VERSION 3.16)
project(tcad_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
option(TCAD_FORCE_LONG_DOUBLE "Use the platform long double scalar backend" OFF)
set(TCAD_CONSTANTS_PROFILE "si" CACHE STRING "Shared charge constant profile: si or legacy-charge")
set_property(CACHE TCAD_CONSTANTS_PROFILE PROPERTY STRINGS si legacy-charge)
if(NOT TCAD_CONSTANTS_PROFILE STREQUAL "si" AND
   NOT TCAD_CONSTANTS_PROFILE STREQUAL "legacy-charge")
    message(FATAL_ERROR "TCAD_CONSTANTS_PROFILE must be si or legacy-charge")
endif()

# Enable quad precision (GCC/Clang)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-O3 -march=native)
    if(NOT TCAD_FORCE_LONG_DOUBLE)
        link_libraries(quadmath)
    endif()
endif()

# Source files
set(TCAD_SRC
    src/math_types.cpp
    src/sparse_matrix.cpp
    src/linear_solver.cpp
    src/ilu_preconditioner.cpp
    src/ic_preconditioner.cpp
    src/poisson_solver.cpp
    src/density_gradient.cpp
    src/gummel_solver.cpp
    src/newton_solver.cpp
    src/mobility_model.cpp
    src/device_simulator.cpp
)

# Core static library
add_library(tcad_core STATIC ${TCAD_SRC})
target_include_directories(tcad_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
if(TCAD_CONSTANTS_PROFILE STREQUAL "legacy-charge")
    target_compile_definitions(tcad_core PUBLIC TCAD_CONSTANTS_LEGACY_CHARGE=1)
endif()
if(TCAD_FORCE_LONG_DOUBLE)
    # PUBLIC is required: every consumer of real_t must use the same ABI.
    target_compile_definitions(tcad_core PUBLIC TCAD_FORCE_LONG_DOUBLE)
endif()

# Tests
enable_testing()
if(EXISTS "${CMAKE_SOURCE_DIR}/tests/cpp")
    add_subdirectory(tests/cpp)
endif()
