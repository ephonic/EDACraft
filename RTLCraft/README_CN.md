# RTLCraft (rtlgen) — Python API for Verilog RTL 生成

> 一套面向对象、装饰器驱动的 Python API，用于描述可综合的 Verilog / SystemVerilog 数字逻辑。
> 这不是一个黑盒生成器，而是一个**白盒框架**——让代码（LLM / Agent）能够直接理解、操作和演化 RTL 的抽象语法树（AST）。

---

## 设计哲学

### 白盒工具：让 Code 做 Reasoning

传统 HLS（高层次综合）工具是**黑盒**：你写 C++/Python，它吐出 Verilog，中间发生了什么你一无所知。出了问题也无法调试。

RTLCraft 走完全相反的路——它是一个**白盒框架**：

- **AST 完全透明**：Python 层构建的每一个 `Signal`、`Module`、`Assign` 都是显式的 AST 节点，你可以随时遍历、修改、打印。
- **Code 可读可写**：LLM 或开发者不仅能生成代码，还能读取已有设计的结构，进行增量修改、重构、优化。
- **工具与设计协同演化**：仿真器、PPA 分析器、综合器全部基于同一套 AST，任何一端的改动都能即时反馈到其他端。

```python
# 白盒：你可以直接访问模块的 AST
dut._inputs       # 所有输入端口的字典
dut._comb_blocks  # 所有组合逻辑块的列表
dut._seq_blocks   # 所有时序逻辑块的列表
```

### 从 Verilog 到 Python DSL 的双向流动

RTLCraft 支持**双向工作流**：

- **正向**：Python DSL → AST → Verilog / SV / UVM / Testbench / 仿真
- **逆向**：Verilog Repo → Python DSL（通过 `VerilogImporter`，需安装 pyverilog），将遗留代码库转换为可维护的 Python 描述

这让 RTLCraft 成为一个**活的工具链**——既能从零开始设计，也能接管和重构已有项目。

---

## 功能全景

| 模块 | 能力 | 状态 |
|------|------|------|
| `core` + `logic` | Python DSL → AST（信号、模块、逻辑控制、状态机、有符号/无符号类型、位宽推断、意图约束、源码追踪） | ✅ 成熟 |
| `codegen` | AST → Verilog-2001 / SystemVerilog（含子模块去重、EmitProfile、源码映射） | ✅ 成熟 |
| `lint` | Verilog 生成后 lint + 自动修复（14 条 Verilog 级规则 + 8 条 AST 级规则，含 width_truncation、signed_mix） | ✅ 成熟 |
| `sim` | Python AST 解释器（4 态逻辑、多时钟、VCD 导出、断点调试） | ✅ 成熟 |
| `sim_jit` | 纯 Python JIT 加速（50–500×），透明回退到解释器 | ✅ 可用 |
| `ppa` | 基于 AST 的逻辑深度 / 门数 / 扇出 / 死信号分析，意图约束检查 | ✅ 可用 |
| `smt` | 基于 SMT 的组合等价性检查（z3） | ✅ 可用 |
| `verification` | 行为级模型生成器、设计规则检查器、协议描述符 | ✅ 可用 |
| `blifgen` + `synth` | ABC 逻辑综合集成（BLIF → 优化网表） | ✅ 可用 |
| `uvmgen` | SV UVM testbench 自动生成（interface / agent / env / test） | ✅ 可用 |
| `pyuvm` + `pyuvm_sim` | 原生 Python UVM 框架 + 仿真器驱动 | ✅ 可用 |
| `pyuvmgen` | Python UVM → SystemVerilog 转译器 | ✅ 可用 |
| `cocotbgen` | cocotb 测试框架自动生成 | ✅ 可用 |
| `uvmvip` | APB / AXI4-Lite / AXI4 VIP 生成 | ✅ 可用 |
| `regmodel` | UVM RAL 寄存器模型生成 | ✅ 可用 |
| `pipeline` | 流水线引擎（自动握手 + 反压） | ✅ 可用 |
| `lib` | FSM / 同步 FIFO / 异步 FIFO / 仲裁器（固定优先级 + 轮询）/ 解码器 / 优先编码器 / 桶形移位器 / LFSR / CRC / 除法器 / 计数器 / 边沿检测器 / StreamFIFO / FlatMemory / SpillRegister / RegSlice / CreditFlowControl / ClockGateCell / DataflowPipeline | ✅ 可用 |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB-Lite / Wishbone | ✅ 可用 |
| `ram` | 单口 / 简单双口 RAM 封装 | ✅ 可用 |
| `cosim` | Python ↔ iverilog 协同仿真 | ✅ 可用 |
| `verilog_import` | Verilog / SV → Python DSL（需 pyverilog） | ⚠️ 可选依赖 |
| `netlist` | 门级网表解析 | ✅ 可用 |
| `liberty` | Liberty 标准单元库解析与生成 | ✅ 可用 |
| `lef` | LEF 物理库解析与生成 | ✅ 可用 |
| `passes` | PassManager 编译管线（LintPass / ConstantFoldPass / DeadCodeElimPass） | ✅ 可用 |
| `registry` | 组件注册表（标签、面积、延迟、搜索） | ✅ 可用 |
| `behaviors` | TemplateRegistry 可复用行为模板 | ✅ 可用 |
| `params` | 香山风格参数预设，流式 PEParams 构建器 | ✅ 可用 |
| `arch_def` | 通用 PE 模型（FuConfig / ExuConfig / Param / PEParams / Array / RegPool / PortGroup），适用于 CPU、GPGPU、NPU、协议控制器 | ✅ 可用 |
| `arch_planner` | 架构规划器（SpecIR → ArchitectureIR，4 大类） | ✅ 可用 |
| `dsl_gen` | DSL 骨架生成器（ArchitectureIR → Module，4 大类） | ✅ 可用 |
| `arch_sim` | 架构级仿真器（含反压、IPC 追踪、冒险检测） | ✅ 可用 |
| `arch_skel` | PE 类型专属步骤向导，自动 Array / Reg 选择 | ✅ 可用 |
| `ppa_optimizer` | PPA 评分 + 6 种优化策略（流水化、资源共享、位宽缩减、算子选择、Mux 均衡、FSM 编码） | ✅ 可用 |
| `verif_gen` | 验证生成器（参考模型、定向/随机测试、覆盖率、协议检查） | ✅ 可用 |
| `decomposition` | 类 gem5 层次分解，PPA 违规预检测 | ✅ 可用 |
| `spec_ir` | Spec IR / Architecture IR / OptimizableOp 数据类 | ✅ 可用 |
| `spec_extractor` | Spec 补全器 + SpecExtractor（YAML、模板、自然语言） | ✅ 可用 |

---

## 核心 API 设计

### 1. Python DSL：装饰器 + 上下文管理器

RTLCraft 的设计目标是用**最 Pythonic 的方式**描述硬件，同时保持**完全可综合**的语义。

```python
from rtlgen import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, Switch, Mux, Cat, ForGen

class ALU(Module):
    def __init__(self, width=8):
        super().__init__("ALU")
        self.a = Input(width, "a")
        self.b = Input(width, "b")
        self.op = Input(3, "op")
        self.result = Output(width, "result")

        @self.comb
        def _logic():
            with Switch(self.op) as sw:
                with sw.case(0b000):
                    self.result <<= self.a + self.b
                with sw.case(0b001):
                    self.result <<= self.a - self.b
                with sw.case(0b010):
                    self.result <<= self.a & self.b
                with sw.default():
                    self.result <<= 0
```

**关键设计决策**：
- `<<=` 操作符：统一表示阻塞赋值（`=`）和非阻塞赋值（`<=`），根据目标信号类型（`Wire`/`Reg`）和上下文（`@comb`/`@seq`）自动推导
- `with If(...)` / `with Switch(...)`：上下文管理器让条件分支读起来像 Python，生成的是标准 Verilog `if/else` / `case`
- `ForGen`：在模块顶层生成 `generate for`，在 always 块内生成 `integer for`
- `StateTransition`：解决 FSM 中同一寄存器多分支赋值的覆盖问题，自动合并为优先级 Mux 链

### 2. 仿真引擎：AST 解释器

内置 Python AST 遍历解释器，支持完整的 RTL 语义：

```python
from rtlgen import Simulator

sim = Simulator(dut)
sim.reset()                   # 自动检测 rst/rst_n
sim.poke("a", 0x12)           # Verilator 风格 API
sim.poke("b", 0x34)
sim.step()                    # 推进一个时钟周期
assert sim.peek("result") == 0x46
```

**特性**：
- 层次化设计自动 flatten
- Memory 读写直接支持
- Trace 输出（table / VCD 格式）
- 多时钟域仿真
- X/Z 四态逻辑支持
- 断点调试（`add_breakpoint` / `run_until_break`）

#### 2.1 JIT 仿真加速（`sim_jit`）

```python
from rtlgen.sim_jit import JITSimulator

# 比 AST 解释器快 50–500 倍，透明回退
sim = JITSimulator(dut)
sim.reset()
sim.poke("a", 0x12)
sim.step(1000)  # 批量推进时钟周期
```

### 3. UVM / Testbench 生成

#### 3.1 SystemVerilog UVM（`uvmgen`）

```python
from rtlgen import UVMEmitter

files = UVMEmitter().emit_full_testbench(dut)
# 生成：*_if.sv, *_pkg.sv, *_transaction.sv, *_driver.sv,
#       *_monitor.sv, *_agent.sv, *_scoreboard.sv, *_env.sv,
#       *_test.sv, tb_top.sv
```

#### 3.2 原生 Python UVM（`pyuvm` + `pyuvm_sim`）

在 Python 中运行完整的 UVM 测试平台（component tree、sequence、TLM、phase、objection），底层驱动 `Simulator`：

```python
from rtlgen.pyuvm import UVMTest, UVMSequence, uvm_do, delay

class MyTest(UVMTest):
    async def run_phase(self, phase):
        seq = MySequence("seq")
        await seq.start(self.env.agent.sequencer)
```

这意味着你可以在 Python 中**快速调试 UVM 平台逻辑**，确认无误后导出 SV 交付给 VCS/Questa/Xcelium。

#### 3.3 Python UVM → SV 转译（`pyuvmgen`）

将 Python UVM 测试代码转译为标准 SystemVerilog，包含 `uvm_component_utils`、`uvm_object_utils` 宏、clocking block 等。

### 4. 基于 AST 的 PPA 性能评估

不需要等待综合完成，在 Python 层就能基于 AST 进行快速 PPA 分析：

```python
from rtlgen import PPAAnalyzer

ppa = PPAAnalyzer(dut)
print(ppa.logic_depth("result"))    # 关键路径逻辑深度
print(ppa.gate_count())             # 估算门数
print(ppa.fanout_analysis())        # 高扇出信号
print(ppa.dead_signals())           # 死信号检测
print(ppa.toggle_rates())           # 翻转率估算
```

所有分析基于 AST 结构，**秒级完成**，适合在设计早期快速迭代架构决策。

PPA-aware 组件支持自动优化建议：
```python
from rtlgen.ppa import PPAAwareComponent, OptimizationAdvisor

class MyAccelerator(PPAAwareComponent):
    def __init__(self):
        super().__init__("MyAccelerator")
        self.advisor = OptimizationAdvisor(self)
        # Advisor 根据 PPA 目标推荐实现策略
        strategy = self.advisor.recommend("fifo", target="area")
```

### 5. 逻辑综合

集成 **ABC**（Berkeley Logic Synthesis）逻辑综合工具：

```python
from rtlgen import BLIFEmitter, ABCSynthesizer

blif = BLIFEmitter().emit(dut)
synth = ABCSynthesizer()
result = synth.synthesize(blif, script="resyn2")
print(result.netlist)
```

支持 BLIF 网表生成、ABC 脚本自定义、门级网表解析、Liberty 标准单元库解析、静态时序分析。

### 6. 总线协议与标准组件

#### 6.1 总线协议

```python
from rtlgen import AXI4, AXI4Lite, APB, AHBLite, AXI4Stream, Wishbone, Bundle

# 所有协议均可参数化地址/数据宽度
axi = AXI4(id_width=4, addr_width=32, data_width=32, user_width=0)
apb = APB(addr_width=32, data_width=32)
```

支持 `Bundle.flip()` 方向反转和 `Bundle.connect()` 自动连线映射。

#### 6.2 标准组件库

```python
from rtlgen import FSM, SyncFIFO, AsyncFIFO, RoundRobinArbiter
from rtlgen import Decoder, PriorityEncoder, BarrelShifter, LFSR, CRC, Divider
from rtlgen import Counter, EdgeDetector, FixedPriorityArbiter, StreamFIFO
from rtlgen import FlatMemory, SpillRegister, RegSlice
from rtlgen import CreditFlowControl, ClockGateCell, DataflowPipeline
from rtlgen import SinglePortRAM, SimpleDualPortRAM
```

### 7. 流水线引擎

```python
from rtlgen import Pipeline

pipe = Pipeline("AdderPipe", data_width=32)
pipe.clk = Input(1, "clk")
pipe.rst = Input(1, "rst")

@pipe.stage(0)
def fetch(ctx):
    tmp = ctx.local("tmp", 32)
    tmp <<= ctx.in_hs.data + 1
    ctx.out_hs.data <<= tmp
    ctx.out_hs.valid <<= ctx.in_hs.valid

@pipe.stage(1)
def exec_(ctx):
    ctx.out_hs.data <<= ctx.in_hs.data + 2
    ctx.out_hs.valid <<= ctx.in_hs.valid

pipe.build()
```

自动生成级间寄存器、`ready` 反压信号、顶层握手端口。

### 8. Verilog 导入

将已有 Verilog / SystemVerilog 代码库转换为 RTLCraft Python DSL：

```python
from rtlgen import VerilogImporter  # 需 pip install pyverilog

importer = VerilogImporter("/path/to/verilog/repo")
importer.scan_repo()
importer.emit_repo("/output", package_name="imported")
```

内置 iverilog 宏展开 + SV 语法修复（`for (integer ...)`, `i++`, `'0` 等）。

### 9. SMT 等价性检查

使用 z3 验证两个模块实现的组合等价性：

```python
from rtlgen.smt import check_combinational_equivalence
from rtlgen.lib import FixedPriorityArbiter

opt = FixedPriorityArbiter(4)
naive = NaiveArbiter(4)

result = check_combinational_equivalence(opt, naive, outputs={"grant"})
print(result)  # {'equivalent': True} 或反例
```

从 `@comb` 和 `@seq` 块中提取每个输出的组合驱动，转换为 z3 位向量，并检查 `ForAll(inputs, outputs_a == outputs_b)`。支持 `Mux`、`Concat`、`Switch` 和自动位宽对齐。

---

## 架构框架

RTLCraft 包含一套完整的架构建模与规划框架，用于构建复杂的类处理器系统（CPU、GPGPU、NPU、协议控制器）。

### 10. 通用 PE 模型（`arch_def`）

受香山和 gem5 启发的领域无关 PE（Processing Element）模型：

```python
from rtlgen.arch_def import PEParams, FuConfig, ExuConfig, Array, RegPool, PortGroup

params = PEParams()
params.add_fu(FuConfig("alu", ops=["add", "sub", "and", "or"], latency=1))
params.add_fu(FuConfig("mul", ops=["mul"], latency=3))
params.add_exu(ExuConfig("exu0", fus=["alu", "mul"], issue_width=2))

# 自动 Array（组合）与 Reg（时序）选择
pool = RegPool("regfile", entries=32, width=64)
array = Array("sram", entries=1024, width=128)
```

### 11. 架构规划与骨架生成（`arch_planner` + `dsl_gen` + `arch_skel`）

```python
from rtlgen import SpecIR, ArchitecturePlanner, DSLGenerator

spec = SpecIR.from_yaml("...")
planner = ArchitecturePlanner(spec)
arch = planner.plan()
# → 基于 PPA 目标自动选择加法器/乘法器/FSM 的 ArchitectureIR

# 从 ArchitectureIR 生成 DSL 骨架
dut = DSLGenerator(spec, arch).generate()
```

`arch_skel` 提供中文的 CPU、GPGPU、NPU、协议控制器 PE 类型专属实现步骤向导。

### 12. 架构级仿真（`arch_sim`）

带反压建模和 IPC 追踪的架构级仿真器：

```python
from rtlgen.arch_sim import ArchSimulator

sim = ArchSimulator(dut)
sim.run(cycles=1000)
print(f"IPC: {sim.ipc}")
print(f"Stall cycles: {sim.stall_cycles}")
```

### 13. PPA 优化闭环（`ppa_optimizer` + `decomposition`）

```python
from rtlgen import PPAOptimizer, PPAScore, PPAGoal
from rtlgen.decomposition import DecompositionAnalyzer

# 类 gem5 层次分解，PPA 违规预检测
analyzer = DecompositionAnalyzer(dut)
violations = analyzer.check_ppa_constraints()

# 6 级优化策略
optimizer = PPAOptimizer(dut, spec)
result = optimizer.optimize(max_iterations=10)
```

**7 级 PPA 优化策略：**

| 策略 | 层级 | 作用 |
|------|------|------|
| PipelineInsertion | AST | 插入寄存器打断长路径 |
| ResourceSharing | AST | 互斥路径间共享算子 |
| BitwidthReduction | RTL | 去除冗余位宽扩展 |
| OperatorSelection | AST | 切换加法器/乘法器实现 |
| MuxBalancing | RTL | 重新平衡大 Mux 树 |
| FSMEncodingSelect | Arch | 选择二进制/独热/格雷编码 |
| SynthesisFeedback | Tech | ABC 网表面积/延迟反馈 |

完整的教程请见 [Tutorial_CN.md](Tutorial_CN.md)。

---

## 框架增强

### 14. 类型系统：位宽推断与有符号类型

**位宽推断**：二元运算自动推导结果位宽，与 Verilog 语义一致：

```python
a = Input(8, "a")
b = Input(8, "b")
result = a + b   # 自动 9-bit（进位）
product = a * b  # 自动 16-bit
eq = a == b      # 自动 1-bit
```

**有符号/无符号转换**：`signal.as_sint()` / `signal.as_uint()` 显式指定符号性。

**Lint 规则**：`width_truncation` 警告隐式截断；`signed_mix` 检测无符号/有符号混用。

### 15. 源码映射（Python → Verilog 可追溯性）

每条 `Assign` 记录 Python 源码位置：

```python
emitter = VerilogEmitter(emit_source_map=True)
verilog_text, source_map = emitter.emit_design_with_source_map(dut)
# 生成：// rtlcraft: source=my_design.py:42
```

### 16. EmitProfile（Verilog 风格配置）

```python
from rtlgen import EmitProfile, VerilogEmitter

profile = EmitProfile(
    style="sv", always_comb=True, always_ff=True,
    explicit_nettype=True, reset_style="async_low",
)
sv = VerilogEmitter(profile=profile).emit(dut)
```

### 17. 意图约束（PPA-Aware 设计）

```python
class MyDesign(Module):
    def __init__(self):
        super().__init__("MyDesign")
        self.clk = Input(1, "clk")
        @self.intent
        def c(x):
            x.latency_cycles = 3
            x.clock_freq = 500e6

from rtlgen.ppa import PPAAnalyzer
results = PPAAnalyzer(dut).check_intent()
```

### 18. PassManager（编译管线）

```python
from rtlgen import PassManager, LintPass, ConstantFoldPass, DeadCodeElimPass

pm = PassManager()
pm.add(LintPass())
pm.add(ConstantFoldPass())
pm.add(DeadCodeElimPass())
results = pm.run(dut)
```

### 19. 组件注册表

```python
from rtlgen import ComponentRegistry
arbiters = ComponentRegistry.search(tags=["arbitration"])
small = ComponentRegistry.search(max_area=100)
```

### 20. 规格驱动 RTL 生成（Spec2RTL）

闭环 Spec → RTL 流程：**YAML/自然语言 Spec → Spec IR → Architecture IR → DSL → RTL AST → 验证 → PPA 优化 → Verilog**。

```python
from rtlgen import (
    SpecIR, SpecCompleter, SpecExtractor,
    ArchitecturePlanner, DSLGenerator,
    PPAOptimizer, PPAScore, PPAGoal,
    ReferenceModel, TestGenerator, VerificationRunner, CoverageTracker,
)
from rtlgen.synth import ABCSynthesizer

# 第 1 步：解析规格（YAML、模板或自然语言）
spec = SpecIR.from_yaml("""
module:
  name: MAC16
  category: stream_pipeline
function:
  expr: y = a * b + c
timing:
  latency_max: 3
  throughput: 1
ppa:
  priority: timing_first
  max_logic_depth: 6
  allow_pipeline: true
""")

# 第 2 步：补全规格（自动推断端口、填充默认值）
completed = SpecCompleter.complete(spec)

# 第 3 步：规划架构（基于规则、PPA 感知）
planner = ArchitecturePlanner(completed)
arch = planner.plan()
# → pipelined_datapath, 3 stages, wallace mul + carry_lookahead adder

# 第 4 步：生成 RTL 骨架
# dut = DSLGenerator(completed, arch).generate()

# 第 5 步：验证功能正确性
ref = ReferenceModel(completed)
assert ref.evaluate(a=10, b=20, c=5) == 205

tg = TestGenerator(completed)
tests = tg.generate_directed()  # 零、最大值、边界、2 的幂
random_tests = tg.generate_random(count=100, seed=42)

ct = CoverageTracker(completed)
for t in random_tests[:20]:
    ct.sample(t.inputs)

# 第 6 步：PPA 评分 + 优化闭环
goal = PPAGoal(max_logic_depth=completed.timing.latency_max)
score = PPAScore.compute(ppa_report, goal)

optimizer = PPAOptimizer(module, spec)
result = optimizer.optimize(max_iterations=10)

# 第 7 步：综合反馈（ABC → 结构化 JSON）
synth = ABCSynthesizer()
feedback = synth.parse_feedback(synth_result)
# → {"area": N, "depth": D, "suggestion": "..."}
```

完整的教程请见 [Tutorial_CN.md](Tutorial_CN.md)。

---

## Skills 目录

`skills/` 是 RTLCraft 的**硬件设计参考库**，收集可复用的领域特定模块和教程，灵感来源于第三方开源 RTL：

| 目录 | 内容 | 状态 |
|------|------|------|
| `codec/ldpc/` | WiMax 802.16e LDPC 解码器 | ✅ 可用 |
| `codec/video/` | xk265 HEVC 解码器（复旦 VIPcore） | ✅ 可用 |
| `cpu/` | 玄铁 C910 RISC-V 核心 | ✅ 可用 |
| `dsp/` | DSP 库（FIR、IIR、CIC、FFT 蝶形运算） | ✅ 可用 |
| `fft/` | R2²SDF FFT 处理器 | ✅ 可用 |
| `gpgpu/` | 乘影 Ventus GPGPU — ALU 阵列、Warp 调度器、Tensor Core | ✅ 可用 |
| `image/isp/` | Infinite-ISP v1.1 图像信号处理器 | ✅ 可用 |
| `interfaces/axi/` | AXI4 全功能主/从 | ✅ 可用 |
| `interfaces/axi_lite/` | AXI4-Lite 从机 RAM | ✅ 可用 |
| `interfaces/axis/` | AXI-Stream | ✅ 可用 |
| `interfaces/btle/` | 蓝牙低功耗基带 | ✅ 可用 |
| `interfaces/ethernet/` | 以太网 MAC + PCS/PMA | ✅ 可用 |
| `interfaces/i2c/` | I2C 主/从 | ✅ 可用 |
| `interfaces/pcie/` | PCIe DMA + AXI 桥 | ✅ 可用 |
| `interfaces/spi/` | SPI 主/从 | ✅ 可用 |
| `interfaces/uart/` | AXI-Stream UART | ✅ 可用 |
| `interfaces/wishbone/` | Wishbone 总线 | ✅ 可用 |
| `mem/cam/` | 内容寻址存储器 | ✅ 可用 |
| `mem/ddr3/` | DDR3 SDRAM 控制器 | ✅ 可用 |
| `noc/` | 2D 网格片上网络 | ✅ 可用 |
| `npu/` | Intel FPGA-NPU | ✅ 可用 |

每个 Skill 目录包含 `SKILL.md`、`README.md`、Python 源文件和设计文档。完整的来源归属与许可证信息请见 [skills/README.md](skills/README.md)。

---

## 项目结构

```
RTLCraft/
├── rtlgen/                   # 核心框架（~33K 行）
│   ├── core.py               # Signal / Module / Parameter / AST / Intent / SourceLoc
│   ├── logic.py              # If / Else / Switch / ForGen / StateTransition
│   ├── codegen.py            # VerilogEmitter / EmitProfile / Source Map
│   ├── lint.py               # VerilogLinter（14 条 Verilog + 8 条 AST 规则 + 自动修复）
│   ├── sim.py                # Simulator（AST 解释器，4 态逻辑）
│   ├── sim_jit.py            # JIT 加速（50–500×）
│   ├── cosim.py              # Python ↔ iverilog 协同仿真
│   ├── verilog_import.py     # Verilog → Python 导入（可选）
│   ├── ppa.py                # PPAAnalyzer + 意图约束检查
│   ├── verification.py       # BehavioralModelGenerator + DesignRuleChecker + ProtocolDescriptor
│   ├── smt.py                # SMT 组合等价性检查器（z3）
│   ├── blifgen.py            # BLIF 网表生成（位级展开）
│   ├── synth.py              # ABC 综合集成
│   ├── passes.py             # PassManager / LintPass / ConstantFoldPass / DeadCodeElimPass
│   ├── registry.py           # ComponentRegistry / ComponentMeta（21 个组件）
│   ├── behaviors.py          # TemplateRegistry 可复用行为模板
│   ├── params.py             # 香山风格参数预设
│   ├── spec_ir.py            # SpecIR / ArchitectureIR / OptimizableOp 数据类
│   ├── spec_extractor.py     # SpecCompleter + SpecExtractor（YAML、模板、自然语言）
│   ├── arch_def.py           # 通用 PE 模型（FuConfig / ExuConfig / PEParams）
│   ├── arch_planner.py       # 架构规划器（4 大类）
│   ├── dsl_gen.py            # DSL 骨架生成器（4 大类）
│   ├── arch_sim.py           # 架构级仿真器（IPC、反压）
│   ├── arch_skel.py          # PE 类型专属步骤向导
│   ├── ppa_optimizer.py      # PPA 评分 + 6 种优化策略
│   ├── verif_gen.py          # 验证生成器（参考模型、测试、覆盖率）
│   ├── decomposition.py      # 类 gem5 层次分解
│   ├── netlist.py            # 门级网表
│   ├── liberty.py            # Liberty 标准单元库
│   ├── lef.py                # LEF 物理库
│   ├── uvmgen.py             # SV UVM testbench 生成
│   ├── pyuvm.py              # 原生 Python UVM 框架
│   ├── pyuvmgen.py           # Python UVM → SV 转译器
│   ├── pyuvm_sim.py          # Python UVM 仿真驱动
│   ├── cocotbgen.py          # cocotb 测试生成
│   ├── uvmvip.py             # APB/AXI VIP 生成
│   ├── protocols.py          # AXI4 / APB / AHB / Wishbone Bundle
│   ├── pipeline.py           # 流水线引擎
│   ├── lib.py                # FSM / FIFO / Arbiter / etc.
│   ├── ram.py                # RAM 封装
│   ├── regmodel.py           # UVM RAL 寄存器模型
│   ├── debug.py              # 调试探针工具
│   └── dpi_runtime.py        # DPI-C 运行时
├── skills/                   # 硬件设计参考库（21 个 skills）
├── README.md                 # English version
├── README_CN.md              # 本文档（中文）
├── Tutorial.md               # Spec-to-RTL Tutorial (English)
├── Tutorial_CN.md            # 中文版 Spec2RTL 教程
└── LICENSE                   # 许可证
```

---

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd RTLCraft

# 2. 安装核心依赖
pip install pyverilog numpy

# 3. 运行教程示例
cd skills/fundamentals/tutorials
python counter.py
python pipeline_adder.py
python api_demo.py
python lib_demo.py
python sim_counter_demo.py

# 4. 运行技能示例
cd skills/arithmetic/multipliers
python -c "
from rtlgen import VerilogEmitter
from skills.arithmetic.multipliers.montgomery_mult_384 import MontgomeryMult384
top = MontgomeryMult384()
print(VerilogEmitter().emit_design(top))
"
```

---

## 安装依赖

| 依赖 | 用途 | 必须 |
|------|------|------|
| `pyverilog` | Verilog 解析（verilog_import） | ⚠️ 可选 |
| `numpy` | 仿真加速 | ⚠️ 可选 |
| `iverilog` | 协同仿真 | ⚠️ 可选 |
| `abc` | 逻辑综合 | ⚠️ 可选 |
| `z3-solver` | SMT 等价性检查 | ⚠️ 可选 |

---

## 扩展方向

- **C++ 仿真引擎**：通过 pybind11 提升仿真速度 50–500×
- **CDC 模块**：格雷码计数器、异步 FIFO 完整实现
- **TrueDualPortRAM**：两口均可读写
- **CHISEL 导出**：AST → FIRRTL 后端
- **形式验证集成**：SVA + yosys-smtbmc
- **后端完善**：门尺寸优化（sizing）、全局/详细布线（routing）、RC 提取（rc/rcextract）

---

## AI 驱动的自动 RTL 生成

RTLCraft 最重要的用法是支持 Claude Code / Kimi Code 等 AI 代码助手完成从 Spec 到 RTL 的全流程自动化：

1. **Spec → Python RTL**：AI 根据自然语言描述生成 Python DSL 代码
2. **仿真验证**：内置 AST 解释器 + pyUVM 框架，覆盖报告直接反馈给 AI
3. **PPA 优化**：基于 AST 的静态分析 + ABC 综合，面积/时序报告反馈给 AI
4. **代码生成**：自动输出 Verilog / SV UVM Testbench / cocotb 测试

详细教程请查看 [Tutorial_CN.md](Tutorial_CN.md)。

---

## 第三方来源归属

`skills/` 目录中的 Python DSL 模块是基于第三方开源 Verilog 参考设计重新实现的。**原始参考 RTL 设计的版权归各自原作者所有。** 使用任何 Skill 时，你必须遵守原始项目的许可证条款。

> **说明**：原始 Verilog 参考设计**不**包含在本仓库中。下表提供来源归属和链接，以便你独立查阅原始许可证。

### 已验证来源

| Skill 领域 | 原作者 / 组织 | 来源链接 | 许可证 |
|-----------|-------------|---------|--------|
| `codec/ldpc` | crboth | <https://github.com/crboth/LDPC_Decoder> | 未指定 |
| `codec/video` | 复旦大学 VIPcore 团队 | <https://github.com/openasic-org/xk265> | 开源（见仓库） |
| `cpu` (C910) | 平头半导体（阿里集团） | <https://github.com/T-head-Semi/openc910> | Apache-2.0 |
| `cpu` (香山) | 开源香山团队 | <https://github.com/OpenXiangShan/XiangShan> | Mulan PSL v2 |
| `dsp` | Alex Forencich | <https://github.com/alexforencich/verilog-dsp> | MIT |
| `fft` | Nanamaru Namake | <https://github.com/nanamake/r22sdf> | MIT |
| `gpgpu` | 清华 DSP 实验室 / 国芯科技（乘影） | <https://github.com/THU-DSP-LAB/ventus-gpgpu-verilog> | Mulan PSL v2 |
| `image/isp` | 10xEngineers（Infinite-ISP） | <https://github.com/10x-Engineers/Infinite-ISP> | Apache-2.0 |
| `mem/cam` | Alex Forencich | <https://github.com/alexforencich/verilog-cam> | MIT |
| `mem/ddr3` | ultraembedded | <https://github.com/ultraembedded/core_ddr3_controller> | Apache-2.0 |
| `noc` | bakhshalipour | <https://github.com/bakhshalipour/NoC-Verilog> | 未指定 |
| `npu` | Intel Corporation | <https://github.com/intel/fpga-npu> | BSD-3-Clause |
| `interfaces/axi` | Alex Forencich | <https://github.com/alexforencich/verilog-axi> | MIT |
| `interfaces/axis` | Alex Forencich | <https://github.com/alexforencich/verilog-axis> | MIT |
| `interfaces/btle` | Xianjun Jiao | <https://github.com/JiaoXianjun/BTLE> | Apache-2.0 |
| `interfaces/ethernet` | Alex Forencich | <https://github.com/alexforencich/verilog-ethernet> | MIT |
| `interfaces/i2c` | Alex Forencich | <https://github.com/alexforencich/verilog-i2c> | MIT |
| `interfaces/pcie` | Alex Forencich | <https://github.com/alexforencich/verilog-pcie> | MIT |
| `interfaces/spi` | Dr. med. Jan Schiefer | <https://github.com/janschiefer/verilog_spi> | LGPL-2.1 |
| `interfaces/uart` | Alex Forencich | <https://github.com/alexforencich/verilog-uart> | MIT |
| `interfaces/wishbone` | Alex Forencich | <https://github.com/alexforencich/verilog-wishbone> | MIT |

---

## 许可协议

本项目采用自定义 MIT 许可证。允许个人学习和研究使用，但**禁止未经授权的商业用途**。
如需商用，请联系作者与复旦大学（集成芯片与系统全国重点实验室）：efouth@gmail.com

**第三方 IP 声明**：上述许可证仅适用于 RTLCraft 框架代码本身（Python DSL、AST、仿真器、生成器），**不**涵盖 `skills/` 中受第三方参考设计启发的 Python DSL 模块，亦不涵盖原始 Verilog 参考设计本身。在使用、修改或再分发这些设计前，用户须独立查阅并遵守各原始项目的许可证条款。详见上表及 [skills/README.md](skills/README.md)。

详见 [LICENSE](LICENSE) 文件。

---

## 相关文档

- [skills/README.md](skills/README.md) — Skills 目录总览与完整来源归属
- [README.md](README.md) — 英文版文档
- [Tutorial_CN.md](Tutorial_CN.md) — Spec2RTL 教程（含 Skills 详情）
- [Tutorial.md](Tutorial.md) — Spec-to-RTL Tutorial (English)
