# Python extension bindings for mom.

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

set_target_properties(_mom PROPERTIES
    CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN ON
)

set(MOM_PY_OUTPUT_DIR "${CMAKE_SOURCE_DIR}/py/mom" CACHE PATH
    "Output directory for the Python extension module")

set_target_properties(_mom PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY "${MOM_PY_OUTPUT_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${MOM_PY_OUTPUT_DIR}"
)
