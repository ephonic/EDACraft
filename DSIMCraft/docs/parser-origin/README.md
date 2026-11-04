> dsim 来源归档：本目录保存原始快照说明、清单和历史构建文件。
> 原始包为 [edacraft_parsers_20261017.zip](edacraft_parsers_20261017.zip)，早期补丁见 [legacy-patches](legacy-patches/README.md)。
> 当前构建使用 [parsers/](../../parsers/README.md)，不解压旧包或重放补丁。以下为原始说明，路径和测试结果描述历史快照。

# EDACraft parser 源码包（2026-10-17）

来自打包时本机工作区的当前源码快照，包含未提交的现有修复。
原始源码保持原路径与字节内容；包根目录的 CMake、examples 和校验文件是打包辅助文件。

| 组件 | 入口与主要实现 | 输出 |
| --- | --- | --- |
| Verilog RTL | `verilog_parser/src/parser/verilog/veri_parser.hpp`，`veri_parser.cpp`，`verilog.l`，`verilog.y` | AST、符号表、参数/端口语义分析 |
| Verilog 门级 | `ftimer_craft/src/parser/gate_netlist_parser.hh/.cc`；`verilog_parser_adapter.hh/.cc` | `te::Network` |
| SPEF | `ftimer_craft/src/parser/spef_parser.hh/.cc` | `te::TimingParasiticDB`，通过 `SpefNameResolver` 绑定网/端口 |
| Liberty `.lib` | `ftimer_craft/src/parser/liberty_parser.hh/.cc` | `edacraft::core::LibertyDB` + `StringPool` |
| 二进制 `.ftlib` / `.ftlib.gz` | `ftimer_craft/src/liberty/liberty_binary.hh/.cc`，`liberty_compress.hh/.cc` | Liberty 数据库序列化/反序列化，gzip 压缩 |

已包含 RTL 预处理器、节点池/语义处理、生成的 lexer/yacc、Tcl 接口、示例与现有语义回归；
其余四类 parser 所需的 Network、寄生数据库、ID、StringPool、ObjectTable 与 LibertyDB 头文件也已包含。
其中 RTL 的第二轮遍历内存、参数/端口及 SV sized cast（例如 `32'(a)`）修复来自当前工作区。
历史修复说明见 `verilog_parser/SEMANTIC_MEMORY_FIX_20261016.md`；其中引用的大型远端证据不在本包内。
本包不代表完整 SystemVerilog 或 PrimeTime 功能支持，具体以源码与测试覆盖为准。

## 构建

建议 Linux GCC/Clang，或 Windows MSYS2 MinGW-w64（RTL 使用 POSIX 头文件，不保证 MSVC）。
需要 CMake >= 3.19、C++17 编译器、zlib 开发包、线程库，以及 Tcl 开发包（RTL）。
Linux Debian/Ubuntu 依赖示例：`build-essential cmake zlib1g-dev tcl-dev`。
默认直接编译随包生成的 lexer/yacc，因此统一入口不要求安装 Flex/Bison。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure
```

只构建门级、SPEF、Liberty、FTLib（无需 Tcl）：

```sh
cmake -S . -B build-formats -DPARSERS_BUILD_RTL=OFF
cmake --build build-formats --parallel 4
```

生成静态库目标 `edacraft_format_parsers`、`edacraft_rtl_parser`，以及 `lib2ftlib` 工具。
上层 CMake 可 `add_subdirectory(...)` 并链接这些目标，include/link 依赖会传递。
RTL 保留 C++11 编译设置；格式 parser 为 C++17。
如需修改语法后重新生成，组件原始入口 `cmake -S verilog_parser -B build-rtl-original -DVERILOG_BUILD_TESTS=ON`
会调用 Flex/Bison，需要额外安装 `flex bison`；该入口生成文件写回组件源码目录。

## 使用

```sh
./build/lib2ftlib ftimer_craft/test/compare/seq_cell.lib -o build/seq.ftlib
./build/lib2ftlib ftimer_craft/test/compare/seq_cell.lib -o build/seq.ftlib.gz --gzip
./build/parser_bundle_smoke . build
```

Windows 可执行文件后缀为 `.exe`，多配置生成器还可能位于 `Release/` 下。
`examples/parser_bundle_smoke.cc` 展示门级读取、SPEF 名称绑定、Liberty 读取和两种 FTLib 回读。
RTL API 和第二轮遍历用法见 `verilog_parser/test/semantic_memory.cpp`；
历史演示 `rtl_parser_demo` 的输入路径相对于 `verilog_parser/` 目录的 `testcases/first_100/`。
`read_core_liberty_file` 可统一读取 `.lib`、`.ftlib`、`.ftlib.gz`；纯文本 `.lib.gz` 不由该函数解压。
FTLib 按头部版本检查兼容性，旧格式不兼容时应由对应 `.lib` 重新转换。

## 测试与校验

默认 CTest 包含：现有 RTL 语义/内存及 sized cast 回归；打包依赖与接口 smoke，
检查门级/SPEF 网络、合成 Liberty fixture 和未压缩/gzip FTLib 回读。
本次 Windows MinGW Release 实测：全部目标编译成功，格式 parser smoke 通过；
现有 `rtl_semantic_memory` 回归失败（`parse result 1`，断言位于 `semantic_memory.cpp:47`）。
因此不能把本包视作全部回归通过的发行版本；详细原始结果见 `VALIDATION.md` 和 `validation/ctest_results.txt`。
`ftimer_craft/tests/test_liberty_binary.cc` 作为原始回归源码收录，但不注册到本包默认 CTest：
它还引用未收录的工艺库 `industrial_ccs.lib`。本包只带 `seq_cell.lib`、`csm_cell.lib` 两个小型测试 fixture。
不包含 fsyn 代码、完整 timing engine 或工艺库全集。
保留原代码版权标头与生成器声明；本包没有额外授予许可证。

`SOURCE_MANIFEST.json` 记录原始文件的相对路径、长度与 SHA256，`SHA256SUMS` 覆盖除自身外的包内文件。
打包实测结果见 `VALIDATION.md`。
