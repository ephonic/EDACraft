# DSIMCraft

DSIMCraft 是编译式 Verilog / SystemVerilog 数字电路仿真器，将设计降为 IR，生成 C++17，再编译为本机仿真程序。本目录发布 **v0.13.0 纯源码工程版**；不包含平台可执行文件、商业 EDA 软件、UVM 库或第三方工具链。

源码来自 [ephonic/dsim](https://github.com/ephonic/dsim)，固定版本为 [`14f9e3de`](https://github.com/ephonic/dsim/commit/14f9e3dedbd716f7a748415866c00e47983133d1)。逐文件来源见 [SOURCE_ORIGIN.json](SOURCE_ORIGIN.json)，发布记录见 [CHANGELOG.md](CHANGELOG.md)，本源码快照的实际验收见 [VERIFICATION.md](VERIFICATION.md)。

获取源码后可用 `python3 DSIMCraft/release/verify_source.py` 检查 [SHA256SUMS](SHA256SUMS) 及固定上游文件的完整性。校验覆盖清单内的发布文件；用户新增的构建目录不参与校验。源码发布标签为 `dsimcraft-v0.13.0`。

## 适用范围

适合在已支持的语言和时序子集中开展 RTL 功能仿真、门级网表仿真及 UVM 验证流程实验。它是持续完善中的工程版本，**不是 VCS 的完整替代，也未证明覆盖“绝大多数工业数字电路”**。请先用自己的设计和测试平台做回归验证。

| 能力 | 当前范围 |
| --- | --- |
| RTL / SystemVerilog | 四态、宽位串、层次/generate、过程/事件与 NBA、数组/聚合/枚举、package、class、task/function/ref 等已实现的子集 |
| 门级与时序 | 独立门级 parser、库模型、延迟、SDF 解析/绑定/执行及部分时序检查；不是完整时序签核工具 |
| 文件与库 | filelist、Liberty、SPEF、原生 DB 对象读取等；各格式有明确边界 |
| 验证 | 部分约束随机、mailbox/semaphore、process/fork、有限并发断言及覆盖率 |
| interface / UVM | interface/modport、virtual interface、接口 task/function、可恢复任务与基础 UVM 验证通路 |
| 波形与执行 | 文本 VCD、压缩波形、可选分区执行和预测回滚；不承诺普遍性能领先 |

RTL parser 与大规模门级 parser **分别实现**，源码均已归入本目录；普通构建不需要仓库外的 parser 工程，也不需要重新生成 Flex/Bison 文件。

## 构建

需要 CMake 3.19+、C++17 编译器、Tcl 开发文件和 zlib。测试及辅助脚本需要 Python 3；Zstandard 用于波形功能，Z3 用于约束随机化。发布验证使用了 Z3 4.15.4。依赖路径可通过 `CMAKE_PREFIX_PATH`，或 `DSIM_Z3_INCLUDE/DSIM_Z3_LIBRARY`、`DSIM_ZSTD_INCLUDE/DSIM_ZSTD_LIBRARY` 指定。

从 EDACraft 根目录执行：

```sh
cmake -S DSIMCraft -B build/dsimcraft -DCMAKE_BUILD_TYPE=Release
cmake --build build/dsimcraft --target dsim -j 4
./build/dsimcraft/dsim --version
```

也可以进入 `DSIMCraft` 后使用 `cmake -S . -B build`。macOS 发布验证使用 Apple Clang；Linux 发布验证使用 Intel icpx。可通过 `-DCMAKE_CXX_COMPILER=... -DDSIM_MODEL_CXX=...` 指定编译器；当前版本不提供 Windows 构建验证。

只需要仿真器时可加 `-DBUILD_TESTING=OFF`。无需执行 `publish_stable.py`；该脚本用于维护上游开发环境的不可变稳定安装，而不是普通源码用户的必需安装步骤。编译器生成模型时会读取本源码树的 runtime 头文件，请保留源码目录；移动或删除目录后应重新配置、构建。

## 快速运行

```sh
./build/dsimcraft/dsim DSIMCraft/examples/counter.sv --top top -o /tmp/dsimcraft-counter
/tmp/dsimcraft-counter
```

预期输出：`DSIMCRAFT COUNTER PASS 4`。`-f filelist.f` 可读取源文件列表；更完整的入口见 `dsim --help` 和[前端说明](docs/frontend-compatibility.md)。

文本 VCD 示例：

```sh
./build/dsimcraft/dsim DSIMCraft/examples/counter.sv --wave-support -o /tmp/dsimcraft-wave
/tmp/dsimcraft-wave --waveform /tmp/dsimcraft-counter.vcd --wave-format vcd
```

需要配置时序、库模型或 SDF 的设计，请参阅[门级来源](docs/tool-flow.md)、[SDF](docs/sdf-binding.md)和[文档索引](docs/README.md)。

## UVM 验证范围

未修改的 Accellera UVM 2020.3.1 已通过以下代表性流程：

- 基本 `run_test`，factory override、config_db、sequencer/driver、analysis/scoreboard。
- field 自动化、clone/copy/compare、简单整数约束随机化及 uvm_event。
- driver 调用 `vif.drive()`、monitor 调用 `vif.active()/sample()`，真实 DUT 和 scoreboard 都观察到三笔 100/101/102，总和 303，与同源 VCS 一致。
- 8192 位字段 pack/unpack，全位比较通过，大小 8196/8196 与 VCS 一致。

这些属于 **`--shared-functions`、`UVM_NO_DPI` 和原生 `-O0` 条件下的功能验证**，不是完整 UVM/VIP/RAL 认证或性能测量。UVM 源码需自行提供：

```sh
python3 DSIMCraft/scripts/uvm_smoke.py \
  --compiler ./build/dsimcraft/dsim \
  --uvm-dir /path/to/accellera-uvm-2020.3.1 \
  --test DSIMCraft/tests/uvm_preprocess/interface_calls.sv \
  --out /tmp/dsimcraft-uvm \
  --model-optimization=-O0
```

## 测试与已知限制

本版本的上游稳定安装在 macOS ARM64、Linux x86_64 各通过选定的三组回归：98 次捕获、35 项编译边界检查、5 项运行期错误检查。普通接口组还验证了七次失败预测、七次提交、两次恢复及真实双分区。原版 UVM 接口方法流程通过前端/原生 ASan/UBSan。**这些数字不是完整语言覆盖率，也不是全套回归通过的声明。**

安装所需依赖后，可在本目录重跑相关回归：

```sh
ctest --test-dir build/dsimcraft --output-on-failure \
  -R '^(rtl_virtual_interface_calls|rtl_virtual_interfaces|rtl_interface_subroutines)$'
```

这里的 `build/dsimcraft` 指从 EDACraft 根目录配置的构建目录。完整测试说明见 [CONTRIBUTING.md](CONTRIBUTING.md)。

主要剩余缺口包括：联合对象图约束随机化、完整 DPI/VPI 与 HDL backdoor、带参数采样的复杂覆盖率/数据库、完整 SVA、virtual clocking、interface 实例数组等。接口调用的实参改绑绑定时机、副作用事件函数和空接口函数探针仍有 dsim/VCS 差异，均已单列，没有计为对齐成功。详见[接口调用范围](docs/virtual-interface-calls.md)、[功能状态](docs/vcs-feature-status.md)和[版本验收](validation/m236-interface-calls/README.md)。历史验收产物完整记录保留在上游仓库；本源码发行不携带历史可执行文件及编译缓存。

## 许可与来源

遵循本仓库现有的[许可证及非商业使用限制](LICENSE)。第三方代码保留原始版权和许可声明；来源见 [parser 说明](parsers/README.md)及 `docs/parser-origin/`。本发行未重新授权这些第三方组件，也不包含 VCS、Synopsys 库或其他商业软件。
