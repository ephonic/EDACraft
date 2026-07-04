# =====================================================================
# bindings/ —— pybind11 扩展 _mom（阶段 0：FreqSweep + NumPy 零拷贝通路）
# =====================================================================

# 优先用已提供的 pybind11_DIR；否则通过 Python 解释器定位其 CMake 目录，
# 避免 cmd 控制台代码页（中文用户名）导致的路径乱码。
if(NOT DEFINED pybind11_DIR AND NOT DEFINED pybind11_ROOT)
    if(DEFINED Python_EXECUTABLE)
        set(_MOM_PY "${Python_EXECUTABLE}")
    elseif(DEFINED PYTHON_EXECUTABLE)
        set(_MOM_PY "${PYTHON_EXECUTABLE}")
    else()
        set(_MOM_PY "python")
    endif()
    execute_process(
        COMMAND "${_MOM_PY}" -c "import pybind11;print(pybind11.get_cmake_dir())"
        OUTPUT_VARIABLE _PYBIND_CMAKE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
        RESULT_VARIABLE _PYBIND_RC
    )
    if(_PYBIND_RC EQUAL 0 AND EXISTS "${_PYBIND_CMAKE_DIR}/pybind11Config.cmake")
        set(pybind11_DIR "${_PYBIND_CMAKE_DIR}")
        message(STATUS "pybind11 CMake dir (via Python): ${pybind11_DIR}")
    endif()
endif()

if(NOT TARGET pybind11::module)
    find_package(pybind11 CONFIG REQUIRED)
endif()

pybind11_add_module(_mom mom_bindings.cpp)

target_link_libraries(_mom PRIVATE mom::core)

# 扩展符号可见性（pybind11_add_module 已处理，这里显式保险）
set_target_properties(_mom PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

# 让生成的 _mom.<abi>.pyd/.so 落到 Python 包目录 py/mom 下，
# 这样 scikit-build-core 打包时能正确归入 mom 包。
set_target_properties(_mom PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/py/mom"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_SOURCE_DIR}/py/mom"
)
