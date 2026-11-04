# v0.13.0 源码发布验收

日期：2026-11-04。发布标签：`dsimcraft-v0.13.0`。

本发行的引擎、parser、runtime、测试及辅助脚本固定来自上游
[`14f9e3dedbd716f7a748415866c00e47983133d1`](https://github.com/ephonic/dsim/commit/14f9e3dedbd716f7a748415866c00e47983133d1)。
`SOURCE_ORIGIN.json` 中的 3254 个文件逐项 SHA256 与该提交一致。
本发行另加 README、许可证副本、版本文件、示例和验收/完整性文件；引擎源码未作发行专用修改。

## 独立源码构建

构建使用导出后的 `DSIMCraft/`，未借用上游构建目录、parser 工程或已编译仿真模型。两台主机均从源码生成 `dsim`，再重新生成、编译和运行对应回归模型。

| 项目 | macOS ARM64 | Linux x86_64 |
| --- | --- | --- |
| 环境 | macOS 27.0.1 / Apple Clang 21.0.0 | CentOS Stream 9 / Intel icpx 2026.1.1 |
| Release 构建 `dsim` | PASS，版本 0.13.0 | PASS，版本 0.13.0 |
| `examples/counter.sv` | PASS，计数 4 | PASS，计数 4 |
| `rtl_virtual_interface_calls` | PASS，30 次捕获 / 6 项编译边界 / 2 项运行错误 | PASS，30 / 6 / 2 |
| `rtl_virtual_interfaces` | PASS，33 / 8 / 3 | PASS，33 / 8 / 3 |
| `rtl_interface_subroutines` | PASS，35 / 21 / 0 | PASS，35 / 21 / 0 |

每台主机合计 98 次捕获、35 项预期编译拒绝、5 项预期运行错误。
普通接口子程序组还包含七次失败预测、七次提交、两次 checkpoint 恢复及实际双分区用例。
捕获是在多个执行模式下重复运行设计，不是 98 个独立设计或语言覆盖率。

macOS 额外构建并通过 `parser_bundle_smoke`、`sdf_parser`、`gate_source`、`runtime` 四项测试。
计数器输出的波形通过文本 VCD 头部检查。
这里只报告本次实际执行的子集，没有执行全套 CTest。

复现三组回归（从 EDACraft 根目录配置后）：

```sh
ctest --test-dir build/dsimcraft --output-on-failure \
  -R '^(rtl_virtual_interface_calls|rtl_virtual_interfaces|rtl_interface_subroutines)$'
```

复现四项基础测试前，需先构建相应测试目标：

```sh
cmake --build build/dsimcraft --target \
  parser_bundle_smoke sdf_parser_test gate_source_test runtime_test -j 4
ctest --test-dir build/dsimcraft --output-on-failure \
  -R '^(parser_bundle_smoke|sdf_parser|gate_source|runtime)$'
```

Linux 本次指定 `CMAKE_CXX_COMPILER` 和 `DSIM_MODEL_CXX` 为 icpx，设置 Tcl 开发路径及 Z3 4.15.4 路径。
macOS 使用 Xcode SDK 和本机开发依赖。用户应按本机依赖位置配置；本发行不携带这些编译器和依赖的二进制文件。

## 原版 UVM

macOS 用本次导出源码新构建的编译器、未修改的完整 Accellera UVM 2020.3.1 库，重新生成并编译原生模型，执行 `tests/uvm_preprocess/interface_calls.sv`：

```text
TRACE UVM_PIN 100
TRACE UVM_PIN 101
TRACE UVM_PIN 102
TRACE UVM_DUT 3 303
TRACE REAL_UVM_SMOKE VIRTUAL_INTERFACE_CALLS 3 303
UVM_ERROR : 0
UVM_FATAL : 0
```

使用 `--shared-functions`、`UVM_NO_DPI`、原生编译 `-O0`。
原版库有两条与 No-DPI 功能相关的 warning，未将其当作错误隐藏。
库共 181 个文件，树 SHA256 为
`65296510b8010f96fccb3cd294936a68ec1fc7f71c9fe540af181bfddf45fe6f`；
测试文件 SHA256 为
`cebcfc4562d2608bee7dae5b3e56501820d612b20923427e5cb14a8e92bac2bb`。

本次源码发行的结构化结果在 [release/validation.json](release/validation.json)。
上游已完成的同源 VCS 比较和 sanitizer 检查属于上游验收；本次没有对导出目录重新执行 VCS 或 sanitizer，也没有做性能基准测试。

## 保留的 VCS 差异

接口调用组十个正向用例中，上游九个同源 VCS 比较通过，一个接收者/实参副作用探针有明确差异：

```text
dsim: TRACE vif capture 1 6 16 16 10
VCS:  TRACE vif capture 1 6 16 10 16
```

两者基础接收者均只求值一次；dsim 保留实参求值前的虚接口，VCS 使用实参改绑后的接口。
另外，副作用事件函数在 VCS 中可接受、dsim 拒绝；空接口函数在 VCS 探针中可执行、dsim 报错。
这些差异没有计为兼容通过。边界检查的 PASS 表示符合当前声明的接受/拒绝行为，不等于 VCS 对齐。

完整 UVM/VIP/RAL、复杂对象图随机化、完整 DPI/VPI/覆盖率/SVA、virtual clocking 和 interface 实例数组仍有缺口。
本版本是可构建、可回归的源码工程版本，不能由这些子集测试推导出支持绝大多数工业数字电路。

## 来源与完整性

```sh
python3 DSIMCraft/release/verify_source.py
```

此命令检查发布校验和及固定上游文件身份。`SHA256SUMS` 不包含其自身；校验只覆盖列出的文件，允许用户添加构建输出。
平台可执行文件、编译缓存、工具链、商业 EDA 库和完整 UVM 库不在发布目录中。
