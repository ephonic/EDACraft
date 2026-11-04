cmake_minimum_required(VERSION 3.19)
project(edacraft_parsers LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(ZLIB REQUIRED)
find_package(Threads REQUIRED)
include(CTest)
option(PARSERS_BUILD_RTL "Build RTL parser and its existing semantic regression" ON)

add_library(edacraft_format_parsers STATIC
    ftimer_craft/src/parser/gate_netlist_parser.cc
    ftimer_craft/src/parser/verilog_parser_adapter.cc
    ftimer_craft/src/parser/spef_parser.cc
    ftimer_craft/src/parser/liberty_parser.cc
    ftimer_craft/src/liberty/liberty_binary.cc
    ftimer_craft/src/liberty/liberty_compress.cc)
target_include_directories(edacraft_format_parsers PUBLIC
    ftimer_craft/include ftimer_craft/src edacraft_core/include)
target_link_libraries(edacraft_format_parsers PUBLIC ZLIB::ZLIB Threads::Threads)
add_executable(lib2ftlib ftimer_craft/src/tools/lib2ftlib.cc)
target_link_libraries(lib2ftlib PRIVATE edacraft_format_parsers)

if(PARSERS_BUILD_RTL)
    # Use the shipped generated scanner/parser; Flex/Bison are optional.
    # Original grammar and component CMakeLists.txt remain in verilog_parser/.
    find_package(TCL REQUIRED)
    file(GLOB_RECURSE rtl_sources CONFIGURE_DEPENDS verilog_parser/src/*.cpp)
    add_library(edacraft_rtl_parser STATIC ${rtl_sources})
    set_target_properties(edacraft_rtl_parser PROPERTIES CXX_STANDARD 11)
    target_include_directories(edacraft_rtl_parser PUBLIC
        verilog_parser/src/err verilog_parser/src/err/parser_err
        verilog_parser/src/err/util_err verilog_parser/src/mgr
        verilog_parser/src/parser/verilog verilog_parser/src/preproc/verilog
        verilog_parser/src/tcl_engine verilog_parser/src/token
        verilog_parser/src/util/singleton ${TCL_INCLUDE_PATH})
    target_link_libraries(edacraft_rtl_parser PUBLIC ${TCL_LIBRARY} Threads::Threads)
    add_executable(rtl_parser_demo verilog_parser/vsyn.cpp)
    target_link_libraries(rtl_parser_demo PRIVATE edacraft_rtl_parser)
    if(BUILD_TESTING)
        add_executable(test_verilog_semantic_memory verilog_parser/test/semantic_memory.cpp)
        target_link_libraries(test_verilog_semantic_memory PRIVATE edacraft_rtl_parser)
        if(MSVC)
            target_compile_options(test_verilog_semantic_memory PRIVATE /UNDEBUG)
        else()
            target_compile_options(test_verilog_semantic_memory PRIVATE -UNDEBUG)
        endif()
        add_test(NAME rtl_semantic_memory COMMAND test_verilog_semantic_memory)
    endif()
endif()

if(BUILD_TESTING)
    add_executable(parser_bundle_smoke examples/parser_bundle_smoke.cc)
    target_link_libraries(parser_bundle_smoke PRIVATE edacraft_format_parsers)
    add_test(NAME parser_bundle_smoke COMMAND parser_bundle_smoke
        "${CMAKE_CURRENT_SOURCE_DIR}" "${CMAKE_CURRENT_BINARY_DIR}")
endif()
