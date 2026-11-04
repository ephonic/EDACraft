# dsim

编译式 Verilog / SystemVerilog 仿真器：将设计降为 IR，生成 C++17 并编译为本机仿真程序。RTL 与大规模门级网表使用独立 parser，支持范围内的四态逻辑、事件调度、延迟、SDF、分区执行和预测回滚。

当前是持续开发中的工程版本，尚不能完整替代 VCS。class、约束随机、完整 UVM / SVA、covergroup、虚拟接口、完整 DPI/VPI 等仍有缺口；已有功能也有明确的支持边界，见[功能状态](docs/vcs-feature-status.md)。

M236 开发实现 [virtual interface task/function](docs/virtual-interface-calls.md)，原版 UVM driver 调用接口任务、monitor 调用接口函数的真实 DUT 流程与 VCS 一致（3笔/303）；覆盖延时重入、参数/ref、静态局部和纯automatic事件函数。剩余差异与发布进度见 [M236](validation/m236-interface-calls/README.md)。

M235 已推送并更新本地与 103 稳定入口，修复动态 stream cast 的枚举类型身份，原版 UVM 8192 位字段 pack/unpack 与 VCS 对齐，输出8196/8196；M234 的 virtual interface→DUT→monitor 集成通过完整 ASan/UBSan。[当前验证与发布进度](validation/m235-stream-enums/README.md)。

M233/M234 新增 [virtual interface](docs/virtual-interfaces.md) 和动态数组 stream 左值。原版 UVM 的 config_db→driver→真实 DUT→monitor→scoreboard 已运行通过，三笔 100/101/102、总和 303 与 VCS 一致；field 自动化、clone/copy/compare、简单约束和 uvm_event 工具用例也通过。条件仍为 UVM_NO_DPI、原生 -O0，完整 UVM 支持及发布状态见 [M234](validation/m234-virtual-interfaces/README.md)。以下里程碑为历史记录。

M232 双端稳定版接通 [类属性 ref 引用](docs/object-scalar-references.md)，原始完整 UVM 的基本 run_test 与 sequence/driver 集成均已通过（UVM_NO_DPI、原生 -O0），包含 factory override、config_db、analysis 与 scoreboard；完整集成也通过 ASan/UBSan。field 自动化仍卡左值流式赋值，尚非完整 UVM 支持，见 [M232](validation/m232-scalar-refs/README.md)。

M231 双端稳定版补齐 [关联数组 input/output/inout 值传递](docs/associative-values.md)及迟创建类特化的虚分派，十个同源 VCS 模型对齐。原始完整 UVM 已能生成并编译本机验证程序，运行推进至类标量成员 ref 引用错误，仍未跑通；稳定发布进展见 [M231](validation/m231-associative-values/README.md)。

M230 已更新本地与 103 稳定入口，补入 [动态数组流式转换、bit-stream cast 与固定字符串数组](docs/array-streams.md)，十四模型42捕获通过，十二同源 VCS 输出对齐、两项表达式差异保留。原始完整 UVM 已越过 stream/cast 和固定字符串数组，当前卡在 phase 的关联数组按值/output 实参，仍未跑通；见 [M230](validation/m230-array-streams/README.md)。

M229 已更新本地与 103 稳定入口，补入 [可恢复的共享自动任务](docs/shared-tasks.md)，支持递归/互递归、虚任务与 fork 重入、调用者身份、回写、取消和回滚。十二同源 VCS 模型通过；原始完整 UVM 越过 sequence.start，下一阻塞为动态队列流式转换，仍未跑通；见 [M229 验证](validation/m229-shared-tasks/README.md)。

M228 已发布到本地与 103，补入 [process 生命周期](docs/process-lifecycle.md)，支持 status/kill/await 及取消后的等待唤醒；完整 UVM 验证改为优先直跑原始库和 hello_test。同源 VCS 已运行通过，dsim 当前卡在 sequence 任务重入展开，仍未跑通；见 [M228 验证](validation/m228-process-lifetime/README.md)。

M227 已更新本地与 103 稳定入口，新增[整张关联数组 ref/const ref](docs/associative-references.md)，支持模块/自动局部/类成员存储、嵌套转发与延时引用。未修改完整 UVM 推进至 `process::kill()`，仍未跑通；见 [M227 验收](validation/m227-associative-refs/README.md)。

M226 已更新本地与 103 稳定入口，新增[函数终止与暂停控制](docs/function-termination.md)，支持函数/虚方法/构造器中的 `$finish`、`$stop` 及初始化/final 边界。未修改完整 UVM 推进至关联数组函数实参，仍未跑通；见 [M226 验收](validation/m226-function-termination/README.md)。

M225 已更新本地与 103 稳定入口，新增[运行期字符串重复](docs/string-replication.md)，支持嵌套、字符串到 packed 转换及等待唤醒。未修改完整 UVM 已越过 printer，下一阻塞为函数内 `$finish`，仍未跑通；见 [M225 验收](validation/m225-string-replication/README.md)。

M224 已更新本地与 103 稳定入口，新增[事件复制与自动局部事件](docs/event-aliases.md)，保留等待对象身份、支持 UVM reset 和空事件规则。未修改完整 UVM 已推进到 printer 的运行期字符串重复表达式，仍未跑通；见 [M224 验收](validation/m224-event-aliases/README.md)。

M223 已更新本地与 103 稳定入口，新增[函数内后台 fork](docs/function-background-forks.md)，支持延时子进程、自动变量捕获、父进程等待/取消及初始化调用。报告打桩 UVM 已推进至 `process::await`，完整 UVM 仍未通过；详见 [M223](validation/m223-function-forks/README.md)。

M222 新增[类成员动态数组/队列 ref 引用](docs/object-array-references.md)，接通 UVM 数组复制的真实别名、延时引用和等待唤醒；有界队列传给无界引用仍保持实际容量。完整 UVM 的下一阻塞为事件句柄赋值，验收见 [M222](validation/m222-object-array-refs/README.md)。

新增[功能覆盖率](docs/functional-coverage.md)：真实 covergroup/bins/cross 采样、实例查询和回滚；带参数采样、复杂 bins 与覆盖数据库仍缺。

最新类型能力见[前置 class 别名与 process 索引](docs/forward-class-aliases.md)。最新容器能力见[多维关联数组](docs/multidimensional-associative-arrays.md)，覆盖逐维类型、子数组、遍历及复制/回滚；完整 UVM 仍未通过。

M210 补齐[函数互递归与类方法递归](docs/recursive-functions.md)，并修复自动函数缓存跨任务共享临时变量导致的分区退化。Mac 与 103 Intel 稳定入口均已更新，选定四组回归及实际入口通过；完整 UVM 仍未通过，范围与验收见 [M210 记录](validation/m210-recursive-functions/README.md)。

M211 对照 103 的 modmult 流程，修复 SDF 初始路径事件和 filelist 入口。固定输入 RTL 的 128 笔对照通过，独立副本也修正了 GOLDMODE 的刺激差异；完整门级/SDF 对照尚缺原网表及系统任务接入，见 [测试记录](validation/m211-modmult/README.md)。

M212 接入[静态 `$sdf_annotate`](docs/sdf-task.md)：源代码实例参数、空位选项、min/typ/max 和运行时日志进入实际定时后端，受支持模型的完整输入/输出时间线与 VCS 对照通过。动态重注解和多实例独立定时表仍未支持。

## 快速开始

需要 CMake ≥ 3.19、C++17 编译器、Tcl 开发头文件与库、zlib 和线程库；测试需要 Python 3。Zstandard 用于相关压缩与回放功能，建议安装。常规构建使用已提交的 lexer/parser，无需 Flex/Bison。

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 4
./build/dsim --top top tests/cases/counter.v -o build/counter_simv
./build/counter_simv
```

`dsim` 默认同时保留生成的 `.dsim.cpp`。生成的仿真程序可以独立运行；开发版编译器使用构建时指定的运行时头文件路径，移动或发布编译器请遵循[稳定版发布流程](docs/stable-release.md)。

大型验证调用图可以使用 `--shared-functions` 共享生成函数体，保留自动帧与引用语义；目前限串行 RTL，详见[共享函数模式](docs/shared-functions.md)。完整公开 UVM 尚未跑通。

支持 `dsim -f files.f --top tb -o simv` 和 `dsim -F files.f --top tb -o simv`。`-f` 中的相对路径以运行目录为基准，`-F` 中的相对路径以该列表所在目录为基准。列表可包含源文件、嵌套 `-f`/`-F`、`+incdir+`、`+define+`、注释及带引号的含空格路径；源文件按列表顺序处理，包文件应先于引用它的文件。

显式列出全部源文件时也接受 `+libext+.v+.sv` 后缀声明；`-y` 按需库搜索尚未实现，仍明确报错。`-F` 中的 `--sdf-annotate`、`--sdf-check` 路径同样相对于列表目录解析。

门级仿真通过独立入口读取结构网表，并以 Liberty 提供单元功能：

```sh
./build/dsim --gate-netlist tests/gate/four_state.net.v --gate-top dut \
  --liberty tests/gate/cells.lib tests/gate/four_state.tb.v -o build/gate_simv
./build/gate_simv
```

可通过 `--cxx` 和重复的 `--cxx-flag` 选择 Intel/GCC 及优化参数，见[C++ 编译器选项](docs/compiler-options.md)。更多编译参数见 `./build/dsim --help`；文件列表、波形、SDF 和 VCS 差分流程见[文档导航](docs/README.md)。

压缩波形使用自有 DWF 格式，支持四态差分编码、Zstd 分块压缩、时间索引和范围选择。加上 `--wave-async` 后，由一个独立接收线程完成编码、压缩及写盘，有界队列满时背压等待，退出时排空并写完索引：

```sh
./build/dsim tests/cases/counter.v --wave-support -o build/counter_wave
./build/counter_wave --waveform build/counter.dwf --wave-async \
  --wave-buffer-bytes 8388608 --wave-stats
python3 experiments/waveform/dwf.py unpack build/counter.dwf build/counter.vcd
```

输出文件须为新文件；可用 `--wave-scope`、`--wave-include`、`--wave-exclude` 和 `--wave-start/--wave-end` 限定范围，详见[压缩波形接口](docs/waveform-format.md#独立接收线程编码压缩与写盘m148)。DWF 不与 FSDB 文件格式兼容。

## 功能与验证

M193 扩展[整数与枚举关联索引](docs/integral-associative-keys.md)，保留任意位宽、符号及枚举身份，接通遍历、索引队列、约束 foreach 与恢复；完整公开 UVM 仍受多维运行期容器阻塞，验收状态见 [M193 记录](validation/m193-integral-keys/README.md)。

M192 修复[运行期初始化与默认实参的前向类调用](docs/runtime-initializer-binding.md)，当时公开 UVM 首错推进到关联数组索引类型检查，完整库仍未编译运行；验收状态见 [M192 记录](validation/m192-init-binding/README.md)。

M191 接入 [clocking 采样与驱动](docs/clocking.md)：input #1step/#0、常量输出 skew、默认时钟、@(cb) 与 ##N，并支持取消等待及预测恢复；支持边界和双端验收见 [M191 记录](validation/m191-clocking/README.md)。

M170/M171 新增[数组定位、去重及 with 迭代器](docs/array-locators.md)与[无括号函数体](docs/nonansi-bodies.md)。本地稳定 M171 九组1,064次捕获及实际入口复核通过；完整公开 UVM 仍有阻塞。

M103 新增[通用文本文件 I/O](docs/file-io.md)：FD/MCD、读行/字符、定位、格式化写入及预测期间文件副作用隔离。

M102 新增[运行参数与动态格式化](docs/testbench-io.md)：plusargs、sformatf/sformat 接入实际运行入口，七个同源模型的完整输出与1553个数值波形位通过VCS对照。

M95 新增[字符串子程序签名和返回值](docs/strings.md)，覆盖参数方向、自动激活、递归、事件触发及预测回滚；同源 VCS 对照见 [M95 验收](validation/m95-string-subroutines/README.md)。

| 范围 | 入口 |
| --- | --- |
| RTL / SystemVerilog | [前端架构](docs/frontend-design.md)、[接口与 modport](docs/interfaces.md)、[数组与类型](docs/README.md#rtl-与-systemverilog) |
| 并发过程与调度 | [编译式进程](docs/compiled-processes.md)、[fork 控制](docs/fork-control.md)、[时间语义](docs/time-semantics.md) |
| 断言与验证语法 | [单时钟 property](docs/concurrent-assertions.md)、[固定周期序列](docs/sequence-delays.md) |
| 门级与时序 | [独立 parser](parsers/README.md)、[SDF 运行时](docs/sdf-runtime.md)、[时序检查](docs/timing-checks.md) |
| 分区、回滚与性能 | [并行和回滚](docs/parallel-and-rollback.md)、[性能差距与测量](docs/performance-gap.md) |
| 已知差异与验收 | [功能状态](docs/vcs-feature-status.md)、[M90 验收](validation/m90-ascending-packed/README.md)、[历史验证归档](validation/README.md) |

小型功能用例通过不代表总体兼容或性能领先。M92 补齐未打包 struct 的成员状态转换与默认值，见[支持范围](docs/unpacked-state.md)。M91 修复了混合 packed struct/union 的成员写入 X/Z 丢失，见[存储与视图说明](docs/packed-storage.md)；极端 64 位下标等已知差异仍保留在 M90 验收记录中。

运行测试前先完成构建：

```sh
ctest --test-dir build --output-on-failure \
  -R '^(rtl_semantic_memory|parser_bundle_smoke|runtime|gate_source|sdf_parser)$'
# 完整回归（耗时较长，已知失败及对照边界见 CONTRIBUTING.md）
ctest --test-dir build --output-on-failure
```

## 仓库布局

| 目录 | 内容 |
| --- | --- |
| `src/` | 编译驱动、RTL/门级编译器、预处理与 SDF |
| `include/dsim/` | 生成程序使用的运行时、调度器、波形和并行基础 |
| `parsers/` | 独立 RTL、门级 Verilog、Liberty、SPEF 组件及公共数据库 |
| `tests/` | 回归输入、独立期望值和检查脚本 |
| `cmake/` | CTest 目标注册，根 CMake 保留构建入口 |
| `scripts/` | 构建发布、源码打包、VCS 差分及测量工具 |
| `docs/` | 按主题组织的功能说明、支持边界和来源记录 |
| `validation/` | 历史报告、结构化结果和复现输入；生成产物按归档说明取回 |
| `experiments/` | 实验性工具与基准 |

开发与验证方法见 [CONTRIBUTING.md](CONTRIBUTING.md)。原始 parser 压缩包、版权说明和早期补丁集中在[来源归档](docs/parser-origin/README.md)，当前 parser 直接在 `parsers/` 维护。

原始开发计划保留在 [plan1017.md](plan1017.md)，整理前的长篇首页保留为[截至 M90 的历史记录](docs/history/README-m90.md)。

原生 Synopsys DB 对象读取：`dsim --liberty-db-info cells.db` 输出恢复对象与覆盖 JSON，不调用 lc_shell。完整 DB 仿真模型装配尚未实现，详见 [范围与接口](docs/liberty-db.md)。

M198 补齐 string 队列的普通/类属性存储、函数与任务传参、复制和预测恢复，并接通字符串 locator/映射 reduction。七模型与 VCS 同源执行一致，Mac 与 103 Intel 稳定入口均已更新，跨端 123 CPP/461 捕获及编码相同；冻结四组 37 模型/461 捕获/71 拒绝及生成代码 ASan/UBSan 通过。原版公开 UVM 尚有静态单例句柄比较的常量求值阻塞，完整 UVM 未通过。双端发布状态与收据见 [M198](validation/m198-string-queues/README.md)。
