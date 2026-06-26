# rtlgen

`rtlgen` 是一个基于 Python 的 RTL 设计、仿真、验证与 SystemVerilog 生成工具箱。

这个发布版本使用 `rtlgen` 作为包名。历史上的 `skills/` 与 `tools/` 目录
不进入发布包。发布版聚焦一个小而清晰、可检查、工程师可控的 RTL 设计闭环，
而不是大型 prompt/workflow 框架。

## 设计哲学

### 白盒 RTL，而不是黑盒 HLS

`rtlgen` 不是 C 到门级的编译器，也不是不透明的 HLS 引擎。设计被写成一个
Python 对象图：

1. 端口是显式的 `Input` / `Output`
2. 状态是显式的 `Reg`、`Array` 或 `Memory`
3. 控制流是显式的 `If`、`Else`、`Switch` 和时序块
4. 层次结构是显式的子模块实例化和端口映射
5. 生成 RTL、仿真、诊断、验证、PPA 分析都使用同一份结构

核心思想很简单：硬件应该尽早可执行，并且每一步都可检查。出问题时，用户
应该能看到原始 DSL、lowering 后的可执行模型、生成的 RTL，以及带源位置的
诊断，而不是猜一个隐藏编译器做了什么。

### 语义优先

推荐的工作流是语义优先：

```text
DSL Module
  -> authoring-intent 检查
  -> lowering / flattening
  -> Python simulator
  -> compiled C++ simulator
  -> emitted SystemVerilog
  -> 本地 RTL simulator smoke / closure
  -> PPA 与验证报告
```

这样可以在进入完整 RTL 工具链之前，用更低成本抓住设计错误。Python 仿真
用于快速 debug，compiled simulator 用于更快的 parity/regression，生成 RTL
再交给本地 `iverilog`、`verilator` 或本地安装的 `vcs` 做 smoke / closure。

### Agent 友好，但工程师可控

`rtlgen` 适合与 coding agent 配合使用，但核心契约仍然是工程优先：

1. 设计可见对象必须挂在 module 上
2. signedness 重要时必须显式表达
3. 不支持的 storage/backend contract 会 fail fast
4. diagnostics 尽可能包含稳定规则名与源位置
5. 生成的 collateral 是可审阅文本，而不是隐藏副作用

Agent 可以编写、检查、修改设计，但用户始终拿到的是 RTL 工程师熟悉的代码、
测试和报告。

## 本发布版包含什么

发布包以 `rtlgen` clean-core 工具箱为中心。

```text
rtlgen/
  archsim/   早期架构模型、workload、sweep、瓶颈报告
  dsl/       硬件 DSL、lowering、Verilog emitter、lint/readability helper
  sim/       Python runtime、compiled C++ backend、trace、parity、cosim
  verify/    directed tests、streaming checks、Python-UVM、SV/UVM collateral
  ppa/       结构/运行时 PPA 分析、校准、优化建议
  tests/     clean-core 回归测试

jpeg_decoder/
  dsl_modules.py
  README.md
  tests/
```

发布版刻意排除：

1. `skills/`
2. `tools/`
3. 旧的 prompt/workflow 实验
4. 临时生成的 probe 与 simulator build 目录
5. 网络登录式 simulator helper 和环境特定 farm 脚本

发布文档中的 VCS 使用默认指本地 VCS。没有 VCS 的用户仍然可以使用 Python
仿真、compiled C++ backend、`iverilog` compile smoke，以及可用时的
`verilator`。

## DSL 概览

### 最小模块

```python
from rtlgen.dsl import Else, If, Input, Module, Output, Reg


class Accumulator(Module):
    def __init__(self, width=16):
        super().__init__("Accumulator")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.x = Input(width, "x")
        self.y = Output(width, "y")

        self.acc = Reg(width, "acc")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                with If(self.en == 1):
                    self.acc <<= self.acc + self.x

        with self.comb:
            self.y <<= self.acc
```

### 核心 DSL 能力

`rtlgen.dsl` 当前稳定子集包括：

1. module、port、wire、reg、array、memory
2. 组合逻辑、时序逻辑、latch、初始化块
3. `If` / `Else` / `Elif`、`Switch`、`Mux`、拼接、slice、part-select
4. 通过 `.as_sint()` 和 `.as_uint()` 显式表达 signed / unsigned intent
5. `SRA(...)` 算术右移和 `RoundShiftRight(...)` 定点 round-then-shift
6. 通过 `init_data` 与 `init_file` 描述 module-owned ROM/LUT 初始化
7. 显式子模块实例化和 parent-owned stage handoff wire
8. clock/reset domain 声明和多时钟可执行 stepping
9. CDC primitive 与 report-oriented CDC 检查
10. 支持子集内的 SystemVerilog 生成

### 重要写法规则

这些规则是刻意强制的，用来避免 Python、C++、生成 RTL 和外部工具之间出现
静默不一致：

1. 不要写 Python `if signal:`，要用 `with If(signal):`
2. 不要对 DSL 值使用 Python `and` / `or` / `not`，要用 `&`、`|`、`~`
   或 `Mux`
3. 设计可见对象要挂在 `self` 上，例如 `self.tmp = Wire(...)`、
   `self.buf = Array(...)`、`self.mem = Memory(...)`
4. 子模块 `port_map` 的 key 必须和 child module 声明的端口名一致
5. signed 乘法、比较、clip 前使用 `.as_sint()`
6. signed 定点 round-then-shift 使用 `RoundShiftRight(...)`
7. ROM 的 `init_data` / `init_file` 是设计语义的一部分

## 工具能力

### 仿真

`rtlgen` 提供两条主要可执行路径：

1. `PythonSimulator`：用于快速 debug 和源级可观察性
2. compiled C++ backend：用于更高吞吐的 parity 与 regression

常见写法：

```python
from rtlgen.dsl import lower_dsl_module_to_sim, build_compiled_simulator_from_dsl
from rtlgen.sim import PythonSimulator

module = Accumulator()
py_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
cpp_sim = build_compiled_simulator_from_dsl(module)
```

### Verilog / SystemVerilog 生成

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Accumulator())
```

Emitter 会在边界处做检查，不支持的 contract 会 fail fast。当前本地 backend
建议：

1. 先用 Python/C++ 仿真修 DSL 语义
2. 用 `iverilog -g2012` 做轻量 compile smoke
3. 用 `verilator` 做更强的本地 emitted-RTL closure
4. 如果环境提供本地 `vcs`，需要项目级 simulator 行为时可以使用

网络登录式 simulator flow 不属于发布版文档范围。

### 验证

验证包面向 DSL，而不是裸 simulator IR。它包括：

1. directed step-vector tests
2. streaming checks
3. Python-UVM 风格 sequence 执行
4. SV/UVM collateral 生成
5. 生成 reference model 的 smoke check
6. CDC 与 reset-release 报告

目标是让本地测试、生成 reference model、导出验证 collateral 都复用同一份
DSL 可执行语义。

### PPA 与架构探索

`rtlgen.archsim` 用于在详细 RTL 定稿前探索 bandwidth、latency、capacity、
queue-depth、workload bottleneck 等架构问题。

`rtlgen.ppa` 用于分析详细 module 的结构压力，例如寄存器位数、组合表达式
压力、storage 使用和可重写热点。它是早期工程辅助，不替代最终综合 signoff。

## 推荐 RTL 设计方法

把 `rtlgen` 当成一个可执行 RTL 设计闭环：

1. 先写小的行为/reference model，定义期望 transaction
2. 编写 DSL module，显式定义端口、状态、storage 和层次结构
3. 用 focused tests 跑 Python 仿真
4. 用 compiled simulation 做 parity 和速度提升
5. 生成 RTL 并跑本地 compile smoke
6. executable path 稳定后再生成更完整的 verification collateral
7. 跑 PPA 分析，定位结构热点
8. 修改 DSL，复用同一批测试，保持短闭环

JPEG 风格 datapath 示例见：

1. [jpeg_decoder/README.md](./jpeg_decoder/README.md)
2. [rtlgen/JPEG_DATAPATH_COOKBOOK.md](./rtlgen/JPEG_DATAPATH_COOKBOOK.md)

该例子覆盖 signed fixed-point IDCT、LUT-backed MAC、transpose/reorder
buffer、parent-owned stage handoff wire、Python/C++ 仿真 parity，以及生成
RTL 的 smoke check。

## 当前能力边界

当前稳定且推荐使用：

1. 单时钟同步控制和 datapath module
2. 显式声明 domain 的多时钟执行
3. 支持 storage 子集内的 module-owned array/memory
4. ROM/LUT `init_data` 与 `init_file` 语义
5. 显式 signed intent 的 signed fixed-point arithmetic
6. 通过 parent-owned interconnect 做层次化组合
7. 本地 Python/C++ 仿真和本地 RTL backend smoke/closure
8. report-oriented CDC、验证与 PPA flow

仍然属于 deliberate fail-fast 或有限支持：

1. 广义任意多端口 memory contract
2. emitted RTL 中任意非零 read latency storage
3. 不受约束的 macro mapping
4. 从普通逻辑中证明任意 CDC protocol
5. 把 `iverilog` 当成所有 SystemVerilog 的最终 correctness signoff

## 文档入口

发布版入口：

1. [README.md](./README.md) - 英文 README
2. [Tutorial.md](./Tutorial.md) - 英文最佳实践教程
3. [Tutorial_CN.md](./Tutorial_CN.md) - 中文最佳实践教程
4. [rtlgen/DSL_SEMANTICS.md](./rtlgen/DSL_SEMANTICS.md)
5. [rtlgen/DSL_SUPPORT_MATRIX.md](./rtlgen/DSL_SUPPORT_MATRIX.md)
6. [rtlgen/STDLIB_SUPPORT_MATRIX.md](./rtlgen/STDLIB_SUPPORT_MATRIX.md)
7. [rtlgen/JPEG_DATAPATH_COOKBOOK.md](./rtlgen/JPEG_DATAPATH_COOKBOOK.md)
8. [rtlgen/MIXED_DESIGN_COSIM_GUIDE.md](./rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

所有面向用户的示例都使用发布包名 `rtlgen`。

## License

框架代码遵循仓库 license。本发布包不包含历史 `skills/` 参考设计库。
