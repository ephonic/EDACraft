# vaParser — Verilog-A → C++ 器件模型代码生成器（rfsim 工具链）
#
# 用法:
#   vaParser <model>.va src/model/generated/<name> --format=rfsim
# 产出 <name>_gen.cpp/.h 与 <name>_reg.inc，再由 tools/regen_registry.sh
# 汇总进 src/model/generated/generated_registry.cpp。
#
# lex/yacc 产出物（vaLex.cpp/vaYacc.cpp/derLex.cpp/derYacc.cpp）已入库，
# 构建不依赖 flex/bison；如需重新生成可用本目录 Makefile（MSYS 环境）。

set(VAPARSER_SOURCES
    vaLex.cpp
    vaYacc.cpp
    vaParser.cpp
    derYacc.cpp
    derLex.cpp
    derivation.cpp
    xyce_vcomp.cpp
    rfsim_codegen.cpp
    preparser.cpp
    preprocessorLex.c
    preprocessorYacc.c
    preprocessorMain.c
    adms.c
    switchVariableBlock.cpp
)

# 原 Makefile 用 g++ 编译全部源（.c 也按 C++ 处理），preparser.cpp 引用
# adms.c 符号时依赖 C++ 链接名；保持一致：.c 文件按 C++ 编译。
set_source_files_properties(adms.c preprocessorLex.c preprocessorYacc.c preprocessorMain.c
                            PROPERTIES LANGUAGE CXX)

add_executable(vaParser ${VAPARSER_SOURCES})
target_include_directories(vaParser PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
if(MSVC)
    # unistd.h shim（见 msvc_compat/）
    target_include_directories(vaParser PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/msvc_compat)
endif()

# 继承自 ADMS 的旧式 C/C++ 代码：MSVC 下压低告警、允许旧式字符串字面量转换
if(MSVC)
    target_compile_options(vaParser PRIVATE /W1 /wd4018 /wd4244 /wd4267 /wd4996
        /Zc:strictStrings- /FIgnu_compat.h)
    target_compile_definitions(vaParser PRIVATE _CRT_SECURE_NO_WARNINGS _GNU_SOURCE)
else()
    target_compile_options(vaParser PRIVATE -w -Wno-write-strings)
    target_compile_definitions(vaParser PRIVATE _GNU_SOURCE)
endif()

# Deriv — 独立的导数推导工具（开发辅助）
add_executable(vaDeriv
    main.cpp
    derivation.cpp
    derYacc.cpp
    derLex.cpp
)
target_include_directories(vaDeriv PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
if(MSVC)
    target_include_directories(vaDeriv PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/msvc_compat)
endif()
if(MSVC)
    target_compile_options(vaDeriv PRIVATE /W1 /wd4018 /wd4244 /wd4267 /wd4996
        /Zc:strictStrings- /FIgnu_compat.h)
    target_compile_definitions(vaDeriv PRIVATE _CRT_SECURE_NO_WARNINGS _GNU_SOURCE)
else()
    target_compile_options(vaDeriv PRIVATE -w -Wno-write-strings)
    target_compile_definitions(vaDeriv PRIVATE _GNU_SOURCE)
endif()
