# rtlgen

[English](README.md) | 中文

`rtlgen` 是一个基于 Python 的 RTL 设计、仿真、验证与 SystemVerilog 生成工具箱。
它是本仓库中 RTLCraft 的 clean-core 发布包。

本发布版使用 `rtlgen` 作为公开包名。此前的 `rtlgen_x` 名称不再出现在面向用户
的发布文档中。历史 `skills/`、`tools/`、远程登录式仿真辅助脚本、临时生成
probe，以及项目特定实验内容都不属于本发布面。

## 设计哲学

### 白盒 RTL，而不是黑盒 HLS

`rtlgen` 不是 C 到门级的编译器，也不是不透明的 HLS 系统。设计被写成显式的
Python 对象图：

1. 端口是显式的 `Input` 与 `Output`
2. 状态是显式的 `Reg`、`Array` 或 `Memory`
3. 控制流是显式的 `If`、`Else`、`Switch` 和时序块
4. 层次结构是显式的子模块实例化和端口映射
5. 生成 RTL、仿真、诊断、验证、PPA 分析都来自同一份结构

核心目标是让硬件尽早可执行，并且每一步都可检查。设计出问题时，用户应该能
看到原始 DSL、lowering 后的可执行模型、生成 RTL，以及带源位置的诊断，而不
需要猜隐藏编译器做了什么。

### 语义优先

推荐闭环如下：

```text
DSL module
  -> authoring-intent 检查
  -> lowering 与检查
  -> Python 仿真
  -> compiled C++ 仿真
  -> SystemVerilog 生成
  -> 本地 RTL simulator smoke
  -> 验证与 PPA 报告
  -> DSL 迭代
```

Python 仿真用于快速源级调试。compiled C++ backend 用于更高吞吐的 parity 与
regression。生成 RTL 后，再用本地 `iverilog`、`verilator` 或本地安装的
`vcs` 做 smoke / closure。

### Agent 友好，但工程师可控

`rtlgen` 适合与 coding agent 配合，但核心契约仍然是工程优先：

1. 设计可见对象需要挂在 module 上
2. signedness 重要时必须显式表达
3. 不支持的 storage/backend contract 会 fail fast
4. diagnostics 尽可能包含稳定规则名与源位置
5. 生成的 collateral 是可审阅文本

Agent 可以编写、检查和修改 DSL，但用户始终拿到 RTL 工程师熟悉的代码、测试、
生成 RTL、验证 collateral 和报告。

## 仓库布局

RTLCraft 发布目录被刻意保持很小：

```text
RTLCraft/
  README.md
  README_CN.md
  rtlgen/
    archsim/   早期架构模型、workload、sweep、瓶颈报告
    dsl/       硬件 DSL、lowering、Verilog emitter、lint/readability helper
    sim/       Python runtime、compiled C++ backend、trace、parity、cosim
    verify/    directed checks、streaming checks、Python-UVM、SV/UVM collateral
    ppa/       结构/运行时 PPA 分析、校准、优化建议
    tests/     clean-core 回归覆盖
```

`RTLCraft/rtlgen/README.md` 不再使用。GitHub 目录入口 README 放在
`RTLCraft/README.md`，代码包本体放在 `RTLCraft/rtlgen/`。

## 快速开始

从仓库根目录运行：

```bash
PYTHONPATH=RTLCraft python - <<'PY'
import rtlgen
print("rtlgen import ok")
PY
```

从 `RTLCraft/` 目录运行：

```bash
PYTHONPATH=. python - <<'PY'
import rtlgen
print("rtlgen import ok")
PY
```

发布版适合直接从源码 checkout 使用。很多流程不依赖外部 RTL simulator：
Python 仿真、compiled C++ 仿真、DSL lint、验证 helper、PPA 报告都可以先跑
起来，再进入外部 RTL 工具。

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

### 稳定 DSL 能力

当前 DSL 覆盖：

1. module、port、wire、reg、array、memory
2. 组合逻辑、时序逻辑、latch、初始化块
3. `If` / `Else` / `Elif`、`Switch`、`Mux`、拼接、slice、part-select
4. 通过 `.as_sint()` 和 `.as_uint()` 显式表达 signed / unsigned intent
5. `SRA(...)` 算术右移和 `RoundShiftRight(...)` 定点 round-then-shift
6. 通过 `init_data` 与 `init_file` 描述 ROM/LUT 初始化
7. 显式子模块实例化和 parent-owned stage handoff wire
8. clock/reset domain 声明和多时钟可执行 stepping
9. CDC primitive 与 report-oriented CDC 检查
10. 支持子集内的 SystemVerilog 生成

### 重要写法规则

这些规则用来避免 Python、C++、生成 RTL 和外部工具之间出现静默不一致：

1. 不要对 DSL 值写 Python `if signal:`，要用 `with If(signal):`
2. 不要对 DSL 值使用 Python `and`、`or`、`not`，要用 `&`、`|`、`~` 或
   `Mux`
3. 设计可见对象要挂在 `self` 上，例如 `self.tmp = Wire(...)`、
   `self.buf = Array(...)`、`self.mem = Memory(...)`
4. 子模块 `port_map` 的 key 必须和 child module 的端口名一致
5. signed 乘法、比较、clip 或定点运算前使用 `.as_sint()`
6. ROM 的 `init_data` / `init_file` 是设计语义的一部分

## 工具能力

### 仿真

`rtlgen` 提供两条可执行路径：

1. `PythonSimulator`：用于快速 debug 和源级可观察性
2. compiled C++ simulation：用于更高吞吐的 parity 与 regression

常见写法：

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl, lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

module = Accumulator()
py_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
cpp_sim = build_compiled_simulator_from_dsl(module)
```

### SystemVerilog 生成

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Accumulator())
```

生成 RTL 后建议使用本地工具：

1. `iverilog -g2012` 做轻量 compile smoke
2. `verilator` 做更强的本地 RTL closure
3. 环境提供本地 `vcs` 时，可用于项目级仿真

远程登录式 VCS flow 被刻意排除在本发布文档之外。

### 验证

验证包面向 DSL，包含：

1. directed step-vector tests
2. streaming checks
3. Python-UVM 风格 sequence 执行
4. SV/UVM collateral 生成
5. 生成 reference model 的 smoke check
6. CDC 与 reset-release 报告

目标是让本地测试、reference model、导出验证 collateral 都复用同一份 DSL 可
执行语义。

### PPA 与架构探索

`rtlgen.archsim` 用于在详细 RTL 定稿前探索 bandwidth、latency、capacity、
queue depth 和 workload bottleneck。

`rtlgen.ppa` 分析详细 module 的结构压力，例如寄存器位数、组合表达式压力、
storage 使用和可重写热点。它是早期工程辅助，不替代最终综合 signoff。

## 推荐 RTL 设计方法

建议把 `rtlgen` 当成短闭环、可执行的 RTL 设计方法：

1. 先写小的 behavior/reference model，定义期望 transaction
2. 编写 DSL module，显式定义端口、状态、storage 和层次结构
3. 用 focused tests 跑 Python 仿真
4. 用 compiled simulation 做 parity 和速度提升
5. 生成 SystemVerilog 并跑本地 compile smoke
6. executable path 稳定后再生成验证 collateral
7. 跑 PPA 分析，定位结构热点
8. 修改 DSL，复用同一批测试

更完整的流程可从这些文档开始：

1. [Architecture exploration to PPA tutorial](rtlgen/TUTORIAL_ARCH_PPA.md)
2. [DSL to local UVM tutorial](rtlgen/TUTORIAL_UVM.md)
3. [JPEG datapath cookbook](rtlgen/JPEG_DATAPATH_COOKBOOK.md)
4. [Mixed design cosimulation guide](rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

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

仍然属于有限支持或 deliberate fail-fast：

1. 广义任意多端口 memory contract
2. emitted RTL 中任意非零 read-latency storage
3. 不受约束的 macro mapping
4. 从普通逻辑中证明任意 CDC protocol
5. 把 `iverilog` 当成所有 SystemVerilog 的最终 correctness signoff

## 文档

核心文档：

1. [English README](README.md)
2. [DSL semantic contract](rtlgen/DSL_SEMANTICS.md)
3. [DSL support matrix](rtlgen/DSL_SUPPORT_MATRIX.md)
4. [Standard-library support matrix](rtlgen/STDLIB_SUPPORT_MATRIX.md)
5. [Architecture exploration to PPA tutorial](rtlgen/TUTORIAL_ARCH_PPA.md)
6. [DSL to local UVM tutorial](rtlgen/TUTORIAL_UVM.md)
7. [JPEG datapath cookbook](rtlgen/JPEG_DATAPATH_COOKBOOK.md)
8. [Mixed design cosimulation guide](rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

## License

框架代码遵循仓库 license。本发布包不包含历史 `skills/` 参考设计库。
