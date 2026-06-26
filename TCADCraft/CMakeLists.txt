cmake_minimum_required(VERSION 3.16)
project(tcad_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Enable quad precision (GCC/Clang)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(-O3 -march=native)
    link_libraries(quadmath)
endif()

# Source files
set(TCAD_SRC
    src/math_types.cpp
    src/sparse_matrix.cpp
    src/linear_solver.cpp
    src/poisson_solver.cpp
    src/density_gradient.cpp
    src/gummel_solver.cpp
    src/device_simulator.cpp
)

# Core static library
add_library(tcad_core STATIC ${TCAD_SRC})
target_include_directories(tcad_core PUBLIC ${CMAKE_SOURCE_DIR}/src)

# Tests
enable_testing()
if(EXISTS "${CMAKE_SOURCE_DIR}/tests/cpp")
    add_subdirectory(tests/cpp)
endif()
