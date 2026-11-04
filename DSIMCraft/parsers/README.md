# dsim parsers

Parser 源码直接在 dsim 仓库维护，正常构建、发布和源码打包均使用本目录，不依赖仓库外的 EDACraft / ftimer 工程，也无需运行补丁重放。

| 目录 | 构建目标 | 用途 |
| --- | --- | --- |
| `rtl/` | `dsim_rtl_parser` | RTL/SystemVerilog 语法、AST、符号和类型语义 |
| `gate/` | `dsim_gate_parser` | 独立门级网表 parser 和 Network 适配 |
| `liberty/` | `dsim_liberty_parser` | Liberty、FTLib、gzip FTLib、原生 DB 对象读取（完整模型装配待补） |
| `spef/` | `dsim_spef_parser` | SPEF 寄生参数 |
| `common/` | 头文件 | ID、字符串池、网络、Liberty 和寄生数据库 |
| `tools/`、`test/` | `lib2ftlib`、测试 | 库转换、小型 fixture 和格式往返测试 |

RTL 与门级 parser 保持独立实现。`dsim_format_parsers` 是汇总三个格式库的 INTERFACE 目标，不包含 RTL。SDF 是 dsim 自身实现，继续在 `src/sdf.cpp/.hpp`。

根工程正常构建自动包含 parser。单独验证格式 parser（不需要 Tcl）：

```sh
cmake -S parsers -B build-parsers -DDSIM_PARSERS_BUILD_RTL=OFF
cmake --build build-parsers --parallel 4
ctest --test-dir build-parsers --output-on-failure
```

默认也构建 RTL，需要 Tcl 开发包。保留生成后的 lexer/yacc，正常构建不需要 Flex/Bison。修改语法后，从仓库根运行：

```sh
BISON=/opt/homebrew/opt/bison/bin/bison sh scripts/regenerate_parser.sh
```

`rtl/CMakeLists.txt` 的历史独立构建入口已移到来源归档，统一使用本目录或根工程的 CMake；不再沿用旧文件中固定的 macOS SDK 路径。

来源为最初导入的 `edacraft_parsers_20261017` 源码快照，之后的功能修正在 dsim Git 历史中。原版权、注释、命名空间和生成器声明均保留，没有新增许可证授权。原始清单和历史构建文件见 `docs/parser-origin/`；`REORGANIZATION.json` 逐文件记录整理前路径、当时 SHA256 和当前路径。其中原包 SHA256SUMS/SOURCE_MANIFEST 描述的是历史导入快照，不是当前源码校验清单。[原始压缩包和早期补丁](../docs/parser-origin/README.md)仅供来源追溯，不参与当前构建。

用户提供的原生 Synopsys DB API 已直接归入 `liberty/db_api.h/cc`，不含 lc_shell 路径。范围与诊断见 [原生 DB 读取](../docs/liberty-db.md)，来源见 [导入记录](../docs/parser-origin/db-api/README.md)。
