# Project-owned data model and SDC implementation, fully vendored here.
add_library(edacraft_core STATIC
    src/core/design_db.cpp src/core/constraint_db.cpp
    src/core/gate_netlist_view.cpp src/core/logic_view.cpp
    src/core/timing_db.cpp src/core/sdc/sdc_parser.cpp src/core/sdc_writer.cpp)
add_library(TimeEngine::edacraft_core ALIAS edacraft_core)
target_compile_features(edacraft_core PUBLIC cxx_std_17)
target_include_directories(edacraft_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src/core)
