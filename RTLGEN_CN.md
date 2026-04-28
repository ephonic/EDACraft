# RTLGEN — 基于 AI 代码助手的自动 RTL 生成

> 使用 Claude Code / Kimi Code 等 AI 编程助手，配合 RTLCraft 白盒框架，
> 完成从 Spec → RTL 设计 → 仿真验证 → 优化 → UVM 覆盖 → 代码生成的全流程自动化。
> 框架与它产生的设计**协同演化**——每个解决的问题都成为下一次设计的可复用组件。

---

## 1. 核心理念

### 1.1 白盒框架的六大能力

RTLCraft 不仅是一个 Verilog 生成器。它提供六大能力，与 AI 代码助手（Claude Code / Kimi Code）结合后，可以实现端到端的自动 RTL 设计：

| # | 能力 | 工具 | 作用 |
|---|------|------|------|
| 1 | **描述** | Python DSL | 面向对象的 RTL 描述——每个信号、模块、逻辑块都是 AST 节点 |
| 2 | **仿真和调试** | AST 解释器 | 四态逻辑周期精确仿真器，支持 VCD 波形导出 |
| 3 | **优化** | PPAAnalyzer + ABC | 毫秒级静态 PPA 分析 + Berkeley ABC 综合，评估面积/时序 |
| 4 | **UVM覆盖率** | pyUVM | 原生 Python UVM 框架——记分板、覆盖率、定向+随机测试 |
| 5 | **工具自演化** | 协议Bundle、Pipeline、lib | 框架随设计增长——已验证组件成为可复用库 |
| 6 | **编译器和仿真模型生成** | VerilogEmitter、UVMEmitter等 | 自动输出 Verilog / SV UVM 测试平台 / cocotb 测试脚手架 |

```
┌──────────────────────────────────────────────────────────┐
│  AI 代码助手 (Claude Code / Kimi Code)                     │
│                                                           │
│  1. 描述  ── Python DSL ──▶ AST (信号、模块、逻辑)         │
│       │                                                     │
│       ▼                                                     │
│  2. 仿真  ── AST 仿真器 ──▶ 通过 / 失败 + 波形              │
│       │         │                                           │
│       │         ▼                                           │
│       │    3. 优化  ── PPA + ABC ──▶ 面积 / 延迟 / 门数     │
│       │                                                     │
│       ▼                                                     │
│  4. UVM   ── pyUVM ──▶ 覆盖报告 + 记分板                    │
│       │                                                     │
│       ▼                                                     │
│  5. 自演化 ── 可复用库增长 (APB, AXI, FIFO, FSM...)         │
│       │                                                     │
│       ▼                                                     │
│  6. 生成  ── Verilog / SV UVM / cocotb / 编译器 IR          │
│                                                           │
│  结构化反馈（覆盖率 / PPA / lint）回流给 AI                  │
│  → 诊断 → 修补 → 重新验证 → 收敛                             │
└──────────────────────────────────────────────────────────┘
```

### 1.2 AI 代码助手如何驱动全流程

AI 代码助手（Claude Code / Kimi Code）作为编排者：

1. **接收自然语言 spec**
2. **用 RTLCraft DSL 写 Python RTL 代码**
3. **运行测试**——执行代码并读取结构化输出
4. **读取失败诊断**——哪个 cycle、哪个信号、哪个值不对
5. **修补代码**——精准编辑，不是整段重新生成
6. **重新运行测试**——直到覆盖率和 PPA 预算都满足
7. **输出最终 Verilog**，附带 UVM 测试平台和 cocotb 脚手架

因为 RTLCraft 的反馈是结构化的（Python 异常、PPA 报告、覆盖率百分比），AI 可以精确推理失败原因——与黑盒 Verilog 生成器只有"跑不通"一种反馈截然不同。

---

## 2. 环境准备

### 2.1 安装

```bash
# 克隆仓库
git clone <repo-url>
cd RTLCraft

# 安装核心依赖
pip install pyverilog numpy

# 安装可选依赖（逻辑综合）
brew install abc    # macOS
apt-get install abc # Ubuntu
```

### 2.2 确认环境

```bash
cd RTLCraft
python3 -c "
from rtlgen import Module, Input, Output, Reg, VerilogEmitter, Simulator
print('RTLCraft 已就绪')
"
```

---

## 3. 第一步：描述 — Python DSL

RTLCraft 使用 Python DSL 描述硬件——硬件是对象，不是文本。每个信号是带宽度的类型节点，每个模块是 Python 类，逻辑块是装饰器函数。

### 3.1 示例：8 位计数器

```python
from rtlgen import Module, Input, Output, Reg, VerilogEmitter
from rtlgen.logic import If, Else


class Counter(Module):
    def __init__(self, width=8):
        super().__init__("Counter")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.count = Output(width, "count")
        self._cnt = Reg(width, "cnt")

        @self.comb
        def _out():
            self.count <<= self._cnt

        @self.seq(self.clk, self.rst)
        def _logic():
            with If(self.rst == 1):
                self._cnt <<= 0
            with Else():
                with If(self.en == 1):
                    self._cnt <<= self._cnt + 1


if __name__ == "__main__":
    dut = Counter(width=8)
    sv = VerilogEmitter().emit(dut)
    print(sv)
```

关键设计决策：
- `<<=` 操作符：统一赋值——根据上下文自动选择阻塞赋值（`=`）或非阻塞赋值（`<=`）
- `@self.comb` / `@self.seq`：装饰器在构建时捕获控制流为 AST
- `with If(...)`：上下文管理器让条件分支读起来像 Python，生成标准 Verilog

### 3.2 更复杂：4 运算 ALU

```python
from rtlgen import Module, Input, Output, Wire
from rtlgen.logic import Switch

class SimpleALU(Module):
    def __init__(self, width=16):
        super().__init__("SimpleALU")
        self.a = Input(width, "a")
        self.b = Input(width, "b")
        self.op = Input(2, "op")       # 00=ADD, 01=SUB, 10=AND, 11=OR
        self.result = Output(width, "result")
        self.zero = Output(1, "zero")

        self._res = Wire(width, "res")

        @self.comb
        def _logic():
            with Switch(self.op) as sw:
                with sw.case(0b00):
                    self._res <<= self.a + self.b
                with sw.case(0b01):
                    self._res <<= self.a - self.b
                with sw.case(0b10):
                    self._res <<= self.a & self.b
                with sw.case(0b11):
                    self._res <<= self.a | self.b
            self.result <<= self._res
            self.zero <<= (self._res == 0)
```

### 3.3 标准组件库

RTLCraft 自带已验证组件库，AI 可以直接复用而不是从零生成：

```python
from rtlgen import SyncFIFO, BarrelShifter, LFSR, CRC, Divider

fifo = SyncFIFO(width=32, depth=16)
shifter = BarrelShifter(width=8, direction="left_rotate")
lfsr = LFSR(width=16, taps=[16, 14, 13, 11], seed=0xACE1)
crc = CRC(data_width=8, poly_width=8, polynomial=0x07)
div = Divider(dividend_width=8, divisor_width=8)
```

---

## 4. 第二步：仿真和调试 — AST 解释器

### 4.1 基本仿真

RTLCraft 的仿真器直接解释 AST——无需 Verilog 编译，无需 VPI 开销：

```python
from rtlgen import Simulator

dut = Counter(width=8)
sim = Simulator(dut)

sim.reset()             # 自动检测 rst/rst_n
sim.poke("en", 1)       # 驱动输入

for i in range(10):
    sim.step()          # 推进一个时钟周期
    print(f"  cycle {i}: count = {sim.peek('count')}")

# 预期: count = 1, 2, 3, ..., 10
```

### 4.2 AI 驱动调试：发现并修复 Bug

假设 AI 生成的计数器漏了 `en` 门控：

```python
@self.seq(self.clk, self.rst)
def _logic():
    with If(self.rst == 1):
        self._cnt <<= 0
    with Else():
        # BUG: 漏了 en 判断
        self._cnt <<= self._cnt + 1
```

AI 写一个两阶段测试，立即发现问题：

```python
sim = Simulator(dut)
sim.reset()

# 阶段 1: en=0, count 应该保持 0
sim.poke("en", 0)
for _ in range(3):
    sim.step()
assert sim.peek("count") == 0, f"en=0 but count={sim.peek('count')}"

# 阶段 2: en=1, count 应该递增
sim.poke("en", 1)
for _ in range(3):
    sim.step()
assert sim.peek("count") == 3, f"en=1 but count={sim.peek('count')}"
```

结构化的断言错误告诉 AI 出了什么问题：
```
AssertionError: en=0 but count=3
```

AI 诊断问题（缺少 `en` 门控）并修补代码——一行修改，不是整段重新生成。

### 4.3 仿真速度对比

| 设计 | 周期数 | RTLCraft | cocotb + Icarus |
|------|--------|----------|-----------------|
| Counter | 100 | ~0.8 ms | ~3,500 ms |
| Pipeline Adder | 100 | ~1.2 ms | ~5,000 ms |

原生解释器比外部 Verilog 流程快 **~70 倍**，因为省去了 Verilog 编译（~2-3s）和 VPI 通信开销。

---

## 5. 第三步：优化 — PPA 分析

### 5.1 静态 PPA（毫秒级）

```python
from rtlgen import PPAAnalyzer

dut = Counter(width=8)
ppa = PPAAnalyzer(dut)
report = ppa.analyze_static()

print(f"门数: {report['gate_count']}")
print(f"逻辑深度: {report['logic_depth']}")
# Counter: gates=38, depth={'count': 7, 'cnt': 7}
```

### 5.2 AI 驱动的优化循环

AI 使用 PPA 作为廉价的替代目标：

```python
# AI 读取 PPA 报告，识别关键路径
# 如果深度 > 预算: 插入流水线级
# 如果门数 > 预算: 简化逻辑或交换算术风格

from rtlgen.blifgen import AdderStyle, MultiplierStyle, SynthConfig

# 示例：不重写 RTL，一行切换乘法器风格
config = design.get_config()
config.multiplier = MultiplierStyle.WALLACE  # 之前是 ARRAY
```

静态分析在 **<1 ms** 内完成，适合快速迭代。AI 可以在调用较慢的 ABC 综合后端之前评估数百个候选设计。

---

## 6. 第四步：UVM覆盖率 — pyUVM 框架

### 6.1 原生 Python UVM

RTLCraft 在 Python 中实现了完整的 UVM 框架：

```python
from rtlgen.pyuvm import UVMTest, delay
from rtlgen.pyuvm_sim import run_test


class CounterTest(UVMTest):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.vif = None  # 虚拟接口（由框架自动绑定）

    async def run_phase(self, phase):
        phase.raise_objection(self)

        # 复位
        self.vif.cb.rst <= 1
        self.vif.cb.en <= 0
        await delay(2)
        self.vif.cb.rst <= 0
        await delay(1)

        # 测试 1: en=0, count 应该保持 0
        for _ in range(5):
            self.vif.cb.en <= 0
            await delay(1)
            assert self.vif._read("count") == 0

        # 测试 2: en=1, count 应该递增
        expected = 0
        for _ in range(20):
            self.vif.cb.en <= 1
            await delay(1)
            expected = (expected + 1) & 0xFF
            assert self.vif._read("count") == expected

        # 测试 3: en=0 再次测试, count 应该保持
        for _ in range(5):
            self.vif.cb.en <= 0
            await delay(1)
            assert self.vif._read("count") == expected

        phase.drop_objection(self)


# 运行测试
dut = Counter(width=8)
sim = Simulator(dut)
test = CounterTest("counter_test")
run_test(test, sim, max_cycles=200)
# [CHECKER] total=0 passed=0 failed=0
# UVM 测试完成，耗时 ~1.2ms
```

### 6.2 覆盖率驱动的 Bug 发现

对于 ALU 示例，AI 创建一个记分板，将 DUT 输出与 Python 参考模型对比：

```python
def ref_model(a, b, op):
    if op == 0: return (a + b) & 0xFFFF
    elif op == 1: return (a - b) & 0xFFFF
    elif op == 2: return a & b
    else: return a | b

# 56 个测试: 6 个定向 + 50 个随机
for i in range(50):
    a, b, op = random.randint(0, 0xFFFF), random.randint(0, 0xFFFF), random.randint(0, 3)
    # ... 驱动 DUT 并与 ref_model 比较 ...
```

56 个测试全部通过——AI 实现了功能正确性。

### 6.3 双模式执行

同一个 pyUVM 测试平台可以：
- **在 Python 中运行**用于快速迭代（每个测试 ~1-20ms）
- **导出为 SystemVerilog**用于商业仿真器签核（VCS、Xcelium）

---

## 7. 第五步：工具自演化 — 框架随设计增长

### 7.1 协议 Bundle

RTLCraft 内置预构建的协议 Bundle，AI 可以直接复用：

```python
from rtlgen import APB, AXI4Lite, AXI4, AXI4Stream, Wishbone

apb = APB(addr_width=32, data_width=32)    # 12 个信号
axi = AXI4Lite(addr_width=32, data_width=32)  # 19 个信号
```

AI 不需要从头写 APB/AXI 胶水逻辑——它将现有 Bundle 组合到新设计中。

### 7.2 流水线引擎

```python
from rtlgen import Pipeline

pipe = Pipeline("AdderPipe", data_width=32)
pipe.clk = Input(1, "clk")
pipe.rst = Input(1, "rst")

@pipe.stage(0)
def stage0(ctx):
    tmp = ctx.local("tmp", 32)
    tmp <<= ctx.in_hs.data + 1
    ctx.out_hs.data <<= tmp
    ctx.out_hs.valid <<= ctx.in_hs.valid

@pipe.stage(1)
def stage1(ctx):
    ctx.out_hs.data <<= ctx.in_hs.data + 2
    ctx.out_hs.valid <<= ctx.in_hs.valid

pipe.build()  # 自动生成级间寄存器、ready 反压信号、握手端口
# 生成: 58 行 Verilog, 0.13ms
```

### 7.3 UVM 测试平台自动生成

对任何 DUT，AI 可以生成完整的 UVM 测试平台：

```python
from rtlgen import UVMEmitter

uvm = UVMEmitter()
files = uvm.emit_full_testbench(dut)
# 生成 12 个文件:
#   SimpleDUT_if.sv, SimpleDUT_pkg.sv, SimpleDUT_transaction.sv,
#   SimpleDUT_driver.sv, SimpleDUT_monitor.sv, SimpleDUT_agent.sv,
#   SimpleDUT_scoreboard.sv, SimpleDUT_env.sv, SimpleDUT_sequence.sv,
#   SimpleDUT_sequencer.sv, SimpleDUT_test.sv, tb_top.sv
```

### 7.4 协同演化：设计驱动的库增长

随着 AI 解决更多问题，框架也在增长：

```
新设计 → 验证通过 → 加入 skills/ → 成为可复用参考
                                    ↓
                      AI 复用已验证模块，而不是从零生成
```

这就是**协同演化**：框架和它产生的设计一起进化。每个解决的问题都成为下一个问题的构建块，AI 的生产力随时间不断提升。

---

## 8. 第六步：代码生成 — Verilog / UVM / cocotb

### 8.1 Verilog-2001 / SystemVerilog

```python
from rtlgen import VerilogEmitter
from rtlgen.lint import VerilogLinter

dut = Counter(width=8)
sv = VerilogEmitter().emit(dut)

# 自动 lint
lint = VerilogLinter()
result = lint.lint(sv)
if result.fixed_text:
    sv = result.fixed_text
```

### 8.2 cocotb 测试脚手架

```python
from rtlgen import CocotbEmitter

cocotb = CocotbEmitter()
test_code = cocotb.emit_test(dut)
# 生成带随机激励的 cocotb 测试，含时钟驱动和复位序列
```

### 8.3 协议 VIP 生成

```python
from rtlgen import UVMEmitter

# 生成 APB UVM VIP
apb_dut = ...  # 任何 APB 从设备
files = UVMEmitter().emit_full_testbench(apb_dut)
# 生成完整的 APB agent、driver、monitor、scoreboard
```

---

## 9. 进阶：处理器/NPU 编译器自动生成

### 9.1 NPU 编译器

RTLCraft 的 NPU（`skills/cpu/npu/`）包含脉动阵列、向量 ALU、SFU、池化单元和 Scratchpad 内存。AI 可以自动生成编译器：

```python
from skills.cpu.npu.compiler.ir import NPUIR
from skills.cpu.npu.compiler.lowering import NPULowering
from skills.cpu.npu.compiler.codegen import NPUCodegen

ir = NPUIR()
ir.conv2d(input_shape=(1, 3, 224, 224), kernel_shape=(64, 3, 7, 7), stride=2, padding=3)
ir.relu()
ir.maxpool(kernel=3, stride=2)

lowering = NPULowering(ir)
instructions = lowering.lower()

codegen = NPUCodegen(instructions)
config = codegen.generate()
```

### 9.2 BOOM 风格乱序核心

```python
from skills.cpu.boom.core import BOOMCore

core = BOOMCore()
core.branch_predictor.bht_entries = 128  # AI 修改参数
core.rob_size = 64
```

---

## 10. 使用 Claude Code 实现 RTL 自动化设计

本节详细展示如何借助 Claude Code（或 Kimi Code）自动化完整的 RTL 设计流程——从初始生成、调试、PPA 优化、UVM 覆盖率提升到最终代码生成。

### 10.1 多轮自动化闭环

核心模式是用户与 AI 助手之间的**闭环对话**：

```
第1轮: 规格 → 生成 RTL → 基础仿真测试
第2轮: 仿真失败 → 诊断 → 修复 → 重测
第3轮: PPA 报告 → 优化 → 重新综合
第4轮: 覆盖率不足 → 补充测试 → 重验证
第5轮: 收敛 → 生成 Verilog + UVM + cocotb
```

每一轮都将**结构化反馈**（断言错误、PPA 指标、覆盖率报告）反馈给 AI，AI 诊断问题并进行精准修复。

### 10.2 第1轮：初始生成

**用户 Prompt：**

```
使用 RTLCraft 框架实现一个 8 位加减计数器，规格如下：

模块名称：UpDownCounter
端口：
  - clk (input, 1-bit): 时钟
  - rst (input, 1-bit): 同步复位，高有效
  - load (input, 1-bit): 加载使能
  - up_down (input, 1-bit): 1=加法, 0=减法
  - load_val (input, 8-bit): 加载值
  - count (output, 8-bit): 当前计数

行为：
  - 复位时 count = 0
  - load=1 时，count = load_val
  - load=0 且 up_down=1 时，count 每周期 +1
  - load=0 且 up_down=0 时，count 每周期 -1
  - 溢出/下溢时环绕

要求：
1. 将模块写入 counter.py
2. 运行基础仿真测试：复位、加载值5、加法计数3周期、减法计数2周期、验证结果
3. 报告任何错误
```

**AI 执行步骤：**
1. 使用 RTLCraft DSL 编写包含 `UpDownCounter` 类的 `counter.py`
2. 追加 `__main__` 块：创建模块、运行 `Simulator`、检查结果
3. 执行代码并读取输出

**预期输出（正确时）：**
```
[RESET] counter = 0
[LOAD 5] counter = 5
[UP 1] counter = 6
[UP 2] counter = 7
[UP 3] counter = 8
[DOWN 1] counter = 7
[DOWN 2] counter = 6
All tests passed!
```

**AI 第一轮常见错误：**
- 遗漏使能信号判断（如忘记检查 `load`）
- 条件逻辑中运算符优先级错误
- 信号宽度不匹配

当给出结构化错误输出时，AI 通常能在 1-2 轮内自我修复。

### 10.3 第2轮：自动调试闭环

当仿真失败时，AI 会看到结构化的错误信息：

```
AssertionError at cycle 3: expected count=6, got count=5
  Signal trace: cycle 0: count=0, cycle 1: count=5, cycle 2: count=5, cycle 3: count=5
```

**后续 Prompt（可由 AI 自动生成或用户输入）：**

```
仿真在第3周期失败：期望 count=6，实际 count=5。
计数器加载了值 5，然后 up_down=1 运行了 3 个周期。
期望序列：5→6→7→8，实际：5→5→5→5。

计数值没有递增。请检查 @self.seq 逻辑块中加法计数路径的代码。
修复 bug 并重新运行测试。
```

**AI 执行步骤：**
1. 读取错误——识别计数值没有变化
2. 读取源代码——定位 bug（如 `self._cnt <<= self._cnt` 而非 `self._cnt <<= self._cnt + 1`）
3. 精准修改——只改一行
4. 重新仿真——验证通过

**关键思路：** AI 不会重新生成整个文件。它读取错误、在 AST 源码中诊断根因、进行最小化修复——这与人类工程师调试的方式完全一致。

### 10.4 第3轮：自动 PPA 优化

功能正确后，用户要求 AI 优化面积/时序：

**用户 Prompt：**

```
UpDownCounter 功能已验证。现在运行 PPA 分析并优化面积。
如果门数超过 100，尝试简化逻辑。报告优化前后的指标对比。
```

**AI 执行步骤：**

```python
from rtlgen.ppa import PPAAnalyzer
from rtlgen.synth import ABCSynthesizer

# 第1步：静态 PPA 分析
dut = UpDownCounter()
ppa = PPAAnalyzer(dut)
report = ppa.analyze_static()
print(f"门数: {report['gate_count']}")
print(f"逻辑深度: {report['logic_depth']}")

# 第2步：如果面积过大，进行优化
# 例如，如果 AI 使用了复杂的 MUX 链，
# 可以简化为单个加减法器：
#
# 优化前（冗长）：
#   with If(self.up_down == 1):
#       self._cnt <<= self._cnt + 1
#   with Else():
#       self._cnt <<= self._cnt - 1
#
# 优化后（紧凑——单个 +/- 操作）：
#   direction = Wire(9, "dir")
#   direction <<= Concat(self.up_down, 0)  # 0b01 或 0b00
#   self._cnt <<= self._cnt + direction - 1

# 第3步：重新分析
report2 = ppa.analyze_static()
print(f"优化后门数: {report2['gate_count']}")
```

**预期输出：**
```
[优化前] 门数: 52, 逻辑深度: {'count': 5}
[优化后] 门数: 44, 逻辑深度: {'count': 4}
面积减少 15%
```

**AI 可应用的 PPA 优化模式：**

| 模式 | 优化前 | 优化后 | 节省 |
|------|--------|--------|------|
| 冗余 MUX | 两层嵌套 If → 两个 MUX 级联 | 单个 If 组合条件 | 10-20% |
| 加法器风格 | 行波进位（默认） | Kogge-Stone（通过 config） | 延迟 30-50% |
| 乘法器风格 | 阵列 | Wallace 树 | 面积 20-40% |
| 死代码 | 未使用的信号赋值 | Linter 自动移除 | 5-10% |

### 10.5 第4轮：自动 UVM 覆盖率提升

**用户 Prompt：**

```
为 UpDownCounter 创建 pyUVM 测试平台。目标 100% 功能覆盖率，
覆盖以下 bin：
- 复位行为（在不同计数值下复位）
- 加载行为（加载不同值，包括 0 和 255）
- 加法计数（从 0 开始、从中间值开始、从 254 开始环绕）
- 减法计数（从 255 开始、从中间值开始、从 0 开始环绕）
- load+up/down 组合
- 保持（load=0，up_down 多周期不变）

先用定向测试，再对未覆盖的 bin 添加随机测试。
运行测试并报告覆盖率。如果有 bin 未覆盖，添加定向测试并重新运行。
```

**AI 执行代码：**

```python
from rtlgen import Simulator
from rtlgen.pyuvm import UVMTest, Coverage, delay
from rtlgen.pyuvm_sim import run_test


class CounterTest(UVMTest):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.vif = None
        self.cov = Coverage("counter")
        self.cov.define_bins([
            "reset_from_zero", "reset_from_mid",
            "load_zero", "load_max", "load_mid",
            "up_from_zero", "up_from_mid", "up_wrap",
            "down_from_max", "down_from_mid", "down_wrap",
            "hold_multiple",
        ])

    def _record(self, bin_name):
        self.cov.sample(bin_name)

    async def run_phase(self, phase):
        phase.raise_objection(self)

        # 复位测试
        self.vif.cb.rst <= 1; self.vif.cb.load <= 0; await delay(2)
        self.vif.cb.rst <= 0; await delay(1)
        assert self.vif._read("count") == 0
        self._record("reset_from_zero")

        # 加载测试
        self.vif.cb.load <= 1; self.vif.cb.load_val <= 255; await delay(1)
        self.vif.cb.load <= 0; await delay(1)
        assert self.vif._read("count") == 255
        self._record("load_max")

        # ... 更多定向测试 ...

        # 随机测试：覆盖边界情况
        import random
        for _ in range(20):
            val = random.choice([0, 1, 127, 128, 254, 255])
            self.vif.cb.load <= 1; self.vif.cb.load_val <= val; await delay(1)
            self.vif.cb.load <= 0
            for _ in range(5):
                self.vif.cb.up_down <= random.choice([0, 1])
                await delay(1)

        print(f"覆盖率: {self.cov.report()}")
        phase.drop_objection(self)


dut = UpDownCounter()
sim = Simulator(dut)
test = CounterTest("counter_test")
run_test(test, sim, max_cycles=500)
```

**覆盖率提升闭环：**

如果覆盖率报告显示有未覆盖的 bin：

```
覆盖率报告：
  reset_from_zero: HIT (1 samples)
  reset_from_mid:  MISS
  load_zero:       HIT (1 samples)
  load_max:        HIT (1 samples)
  load_mid:        MISS
  ...
```

**用户 Prompt（或 AI 自动生成）：**

```
覆盖率报告显示 2 个未覆盖的 bin：reset_from_mid 和 load_mid。
为这两个 bin 添加定向测试并重新运行。
```

AI 添加两个特定测试用例并重新运行，直到所有 bin 都被覆盖。

### 10.6 第5轮：最终代码生成

**用户 Prompt：**

```
所有测试通过，覆盖率 100%。生成：
1. 干净的 Verilog 输出
2. 完整的 SystemVerilog UVM 测试平台
3. cocotb 测试脚手架
4. 所有文件保存到 output/counter/
```

**AI 执行代码：**

```python
import os
from rtlgen import VerilogEmitter, UVMEmitter, CocotbEmitter
from rtlgen.lint import VerilogLinter
from rtlgen.synth import ABCSynthesizer

os.makedirs("output/counter", exist_ok=True)

# 1. Verilog + Lint
dut = UpDownCounter()
sv = VerilogEmitter().emit(dut)
lint = VerilogLinter()
result = lint.lint(sv)
if result.fixed_text:
    sv = result.fixed_text
with open("output/counter/counter.v", "w") as f:
    f.write(sv)

# 2. 综合检查
synth = ABCSynthesizer()
synth.run(input_blif="/tmp/counter.blif", output_verilog="output/counter/counter_syn.v")

# 3. UVM 测试平台
uvm = UVMEmitter()
files = uvm.emit_full_testbench(dut, output_dir="output/counter/uvm")
print(f"生成 {len(files)} 个 UVM 文件")

# 4. cocotb 测试
cocotb = CocotbEmitter()
test_code = cocotb.emit_test(dut)
with open("output/counter/test_counter.py", "w") as f:
    f.write(test_code)
```

### 10.7 通用 Prompt 模板

#### 模板 A：新设计（一次性）

```
使用 RTLCraft 框架实现以下模块：

模块：{name}
规格：
  端口：{端口列表，含宽度和方向}
  行为：{功能描述}

步骤：
1. 将模块类写入 {filepath}.py
2. 在 __main__ 中创建 Simulator 定向测试，覆盖：
   - 复位行为
   - 所有主要操作模式
   - 边界情况（零、最大值、环绕）
3. 运行并验证所有断言通过
4. 如果有任何断言失败，诊断并修复后再继续
5. 运行 PPAAnalyzer 并报告门数 + 逻辑深度
6. 用 VerilogEmitter 生成 Verilog
```

#### 模板 B：Bug 修复

```
{module} 的仿真失败：

错误信息：{确切错误信息}
失败时信号 trace：{相关信号值}
期望值：{期望值}
实际值：{实际值}

读取 {filepath}.py 的源代码，在 @self.seq 或 @self.comb 逻辑块中
定位根因，进行最小化修复。重新运行仿真验证。
```

#### 模板 C：PPA 优化

```
{module} 功能已验证，但需要面积/时序优化。

当前指标：
  门数：{N}
  逻辑深度：{D}
  目标：门数 < {target_gates}, 深度 < {target_depth}

阅读 {filepath}.py 的源代码，识别优化机会：
- 可简化的冗余 MUX 级联
- 可使用更高效实现的运算符
- 死代码或未使用的信号

应用优化，重新运行 PPA 分析，报告前后对比。
```

#### 模板 D：覆盖率提升

```
{module} 的 pyUVM 测试平台覆盖率不完整：

未覆盖的 bin：
{未覆盖 bin 列表}

为每个未覆盖的 bin 编写定向测试用例，专门验证该场景。
将它们添加到测试的 run_phase 方法中。
重新运行测试并报告更新后的覆盖率。

如果某个 bin 无法覆盖，解释原因（不可达状态、互斥条件等）。
```

#### 模板 E：完整流程（端到端）

```
使用 RTLCraft 设计并验证以下模块：

模块：{name}
规格：{完整规格说明}

执行完整流程：
1. 用 Python DSL 编写 RTL → {filepath}.py
2. 用定向测试仿真 → 修复任何 bug
3. 运行 PPA 静态分析 → 如需则优化
4. 创建 pyUVM 测试平台含覆盖率 → 达成所有 bin
5. 生成 Verilog，Lint，并用 ABC 进行综合检查
6. 生成 SV UVM 测试平台和 cocotb 测试
7. 所有输出保存到 {output_dir}/

报告：最终门数、逻辑深度、覆盖率%、测试数量、
所有生成文件的路径。
```

### 10.8 进阶：覆盖率驱动的自动调试

对于复杂设计，AI 可以利用覆盖率缺口**发现**定向测试遗漏的 bug：

```python
# AI 生成随机测试并观察覆盖率缺口
for seed in range(100):
    random.seed(seed)
    # 驱动随机输入 ...
    if dut 失败:
        print(f"发现 BUG，seed={seed}")
        print(f"  a={a}, b={b}, op={op}")
        print(f"  期望={ref_model(a,b,op)}, 实际={result}")
        # AI 读取此信息，诊断、修复
```

这正是 RTLCraft 发现 ALU 减法 bug 的方式：随机测试发现当 `a < b` 时 `a - b` 产生错误结果，因为 AI 使用了无符号减法而没有正确处理借位。覆盖率缺口（"带借位减法" bin 未被定向测试覆盖）通过随机种子扫描被暴露。

### 10.9 AI 编码助手最佳实践

| 实践 | 原因 |
|------|------|
| **每次编辑后立即运行** | 立即捕获 bug，而非批量重新生成 |
| **使用断言而非 print** | 断言给出结构化错误，AI 可诊断 |
| **每轮只修一个问题** | 避免连锁修改引入新 bug |
| **编辑前先读取源码** | AI 应该读要修改的文件，而非猜测 |
| **保留已有测试** | 添加新测试时不要破坏已有测试 |
| **复用标准库** | `SyncFIFO`、`BarrelShifter`、`CRC` 等已验证——直接复用 |
| **Prompt 要具体** | "修复第20行的使能判断" 优于 "让它能工作" |

---

## 11. 常见问题

### Q: AI 生成的代码跑不起来怎么办？

RTLCraft 的所有 API 都有类型检查和运行时验证。如果 AI 生成错误代码（例如宽度不匹配），Python 会立即抛出异常。将异常信息反馈给 AI，它通常能在 1-2 轮内自我修复。

### Q: 仿真速度和外部工具比如何？

Python AST 解释器对于小型设计比 cocotb+Icarus 快约 70 倍（<1000 cycle 级）。对于大型设计，可以使用 `cocotbgen` 生成 cocotb 测试，用外部仿真器运行。

### Q: 如何确保生成的 Verilog 是可综合的？

RTLCraft 的 DSL 设计时就考虑了可综合性：
- `@self.comb` 生成 `always @(*)`
- `@self.seq` 生成 `always @(posedge clk)`
- `<<=` 根据上下文自动选择阻塞/非阻塞赋值
- `VerilogLinter` 可以检查并自动修复常见问题

### Q: 可以用其他 AI 工具吗？

可以。任何能执行 Python 代码的 AI 助手（Claude Code、Kimi Code、Cursor 等）都可以配合 RTLCraft 使用。关键是 AI 能：
1. 读取代码
2. 执行代码
3. 查看执行结果
4. 修改代码

---

## 12. 相关资源

- [README_CN.md](README_CN.md) — 项目总览
- [skills/skills.md](skills/skills.md) — Skills 目录
- [paper/main.pdf](paper/main.pdf) — 研究论文
