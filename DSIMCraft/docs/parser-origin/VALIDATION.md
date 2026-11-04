# 本次打包验证

日期：2026-10-17。平台：Windows MSYS2 MinGW-w64，GCC 15.2.0，Release，CMake/Ninja。
依赖：zlib 1.3.2、Tcl 8.6、pthread。验证只针对打包副本，没有修改原始 parser 或 fsyn 源码。

- 统一 CMake 配置成功；全部 39 个构建步骤成功（5 类 parser、2 个静态库、转换工具、示例和回归）。
- `parser_bundle_smoke` 通过：门级 top/网绑定、SPEF RC 节点/电阻/电容单位、两个小型 Liberty fixture、普通及 gzip FTLib 的保存与回读。
- `rtl_semantic_memory` 失败：输出 `reg_var_symbol redefine check: name=z` 后出现 `parse result 1`，随后 `semantic_memory.cpp:47` 的 `result==expected` 断言失败。尚未在本次打包任务中定位根因，也未执行本包的 Linux 验证。
- 最终完整 CTest：1/2 通过，返回码 8。保留失败测试，没有禁用测试或修改 parser 实现来绕过。
- 原始库二进制回归源码已收录；因其中另一个 fixture 是工艺库，本包默认不执行该原始测试。

复现：

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
ctest --test-dir build --output-on-failure
```

原始 CTest 输出见 `validation/ctest_results.txt`。随包的历史修复文档记录的是此前验证，不替代本次结果。
源码文件 SHA256 与原工作区快照逐个校验；压缩包文件也逐个核对 SHA256SUMS。
