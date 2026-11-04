# 开发与验证

## 构建

从仓库根目录运行。需要 CMake ≥ 3.19、C++17、Tcl 开发包、zlib 和 Python 3；安装 Zstandard 后可运行相应的压缩及回放回归。Linux 常见开发包名为 `tcl-dev`、`zlib1g-dev`、`libzstd-dev`。macOS 非默认库路径可通过 `-DCMAKE_PREFIX_PATH=...` 传给 CMake。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure \
  -R '^(rtl_semantic_memory|parser_bundle_smoke|runtime|gate_source|sdf_parser)$'
```

只构建工具可传 `-DBUILD_TESTING=OFF`；此配置不包含回归目标。格式 parser 可[单独构建](parsers/README.md)，RTL 与门级 parser 必须保持独立。

## 回归与 VCS 对齐

根 `CMakeLists.txt` 定义产品目标，`cmake/Tests.cmake` 注册仿真器回归，`parsers/CMakeLists.txt` 注册 parser 回归。新增测试输入与独立期望值放入 `tests/<feature>/`，避免依赖 `validation/` 中的历史产物。

```sh
ctest --test-dir build -N
ctest --test-dir build --output-on-failure
python3 scripts/run_flow.py tests/flow/manifest.json
```

完整回归耗时较长。M91 修复 `packed_aggregates` 中混合 packed struct/union 成员写入丢失 X/Z 的缺陷，原始断言保留，并新增组合场景回归，见[存储与视图说明](docs/packed-storage.md)。[M90 验收记录](validation/m90-ascending-packed/README.md)保留当时的失败和极端 64 位下标等边界差异。测试子集通过应明确写出子集，不能据此宣称全量通过；不要调整期望值以掩盖失败。

修改功能后运行相关测试；对照 VCS 时使用同一份源文件，分别记录工具版本、编译和运行时间、日志、stdout 与完整波形，说明未比较的范围。VCS 环境配置和差分入口见[统一流程](docs/tool-flow.md)，功能正确性用例不能作为性能领先的依据。

修改 RTL grammar 时才运行 `scripts/regenerate_parser.sh`，并提交生成后的 lexer/yacc；普通构建不需要生成工具。保留原版权和来源说明，不给来源代码追加未经授权的许可证。

## 目录与产物

构建输出放入 `build*/`。生成的 C++、可执行文件、波形、日志、缓存和源码包留在构建或发布目录。`validation/` 保存报告、结构化结果、复现工具和源输入；历史原始产物按[归档说明](validation/README.md)取回。提交前检查 `git status`，按路径添加文件，避免顺带提交个人实验目录。

生成可在另一台主机构建的源码包：

```sh
python3 scripts/package_source.py /tmp/dsim-source.tar.gz
```

包内包含 CMake 模块、parser、运行时、回归和来源说明，以及逐文件 SHA256 清单。发布稳定版需要运行[发布流程](docs/stable-release.md)，同时保存源码和二进制身份；普通文档整理不需要替换稳定二进制。
