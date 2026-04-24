# rtlgen — Python API for Verilog RTL Generation

> 一套面向对象、装饰器驱动的 Python API，用于描述可综合的 Verilog / SystemVerilog 数字逻辑。
> 这不是一个黑盒生成器，而是一个**白盒框架**——让代码（Code / LLM）能够直接理解、操作和演化 RTL 的抽象语法树（AST）。

---

## 设计哲学

### 白盒工具：让 Code 做 Reasoning

传统的 HLS（高层次综合）工具是**黑盒**：你写 C++/Python，它吐 Verilog，中间发生了什么你不知道，出了问题也无法调试。

rtlgen 走的是相反方向——它是一个**白盒框架**：

- **AST 完全透明**：Python 层构建的每一个 `Signal`、`Module`、`Assign` 都是显式的 AST 节点，你可以随时遍历、修改、打印。
- **Code 可读可写**：LLM 或开发者不仅能生成 rtlgen 代码，还能读取已有设计的结构，进行增量修改、重构、优化。
- **工具与设计协同演化**：仿真器、PPA 分析器、综合器、后端工具全部基于同一套 AST，任何一端的改动都能即时反馈到其他端。

```python
# 白盒：你可以直接访问模块的 AST
dut._inputs      # 所有输入端口的字典
dut._comb_blocks # 所有组合逻辑块的列表
dut._seq_blocks  # 所有时序逻辑块的列表
```

### 从 Verilog 到 pyRTL 的双向流动

rtlgen 支持**双向工作流**：

- **正向**：Python DSL → AST → Verilog / SV / UVM / Testbench / 仿真
- **逆向**：Verilog Repo → Python DSL（通过 `VerilogImporter`），将遗留代码库一键转换为可维护的 Python 描述

这让 rtlgen 成为一个**活的工具链**——既能从零开始设计，也能接管和重构已有项目。

---

## 功能全景

| 模块 | 能力 | 状态 |
|------|------|------|
| `core` + `logic` | Python DSL → AST | ✅ 成熟 |
| `codegen` | AST → Verilog-2001 / SystemVerilog | ✅ 成熟 |
| `sim` + `sim_jit` | Python AST 解释器 + JIT 编译（~7x 加速） | ✅ 可用 |
| `uvmgen` + `pyuvmgen` | UVM testbench 自动生成（SV + Python 双后端） | ✅ 可用 |
| `pyuvm` + `pyuvm_sim` | 原生 Python UVM 框架 + 仿真器驱动 | ✅ 可用 |
| `ppa` | 基于 AST 的逻辑深度 / 门数 / 扇出 / 死信号分析 | ✅ 可用 |
| `lint` | Verilog 生成后 lint + 自动修复 | ✅ 可用 |
| `blifgen` + `synth` | ABC 逻辑综合集成（BLIF → 优化网表） | ✅ 可用 |
| `liberty` + `lef` | 标准单元库 / 物理库解析与生成 | ✅ 可用 |
| `netlist` + `timing` | 门级网表解析 + 静态时序分析 | ✅ 可用 |
| `sizing` + `placement` | 门尺寸优化 + 解析式布局 | ✅ 可用 |
| `routing` + `rc` | 全局/详细布线 + RC 提取 | ✅ 可用 |
| `rcextract` | 寄生参数提取 → RTL 反馈引擎 | ✅ 可用 |
| `cosim` | Python ↔ iverilog 协同仿真 | ✅ 可用 |
| `verilog_import` | Verilog / SV Repo → Python DSL | ✅ 可用 |
| `cocotbgen` | cocotb 测试生成 | ✅ 可用 |
| `svagen` | SVA 断言生成 | ✅ 可用 |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB / Wishbone | ✅ 可用 |
| `lib` | FSM / FIFO / Arbiter / Shifter / LFSR / CRC / Divider | ✅ 可用 |
| `pipeline` | 流水线引擎（自动握手 + 级间寄存器） | ✅ 可用 |
| `ram` | 单口 / 双口 RAM 封装 | ✅ 可用 |
| `regmodel` | UVM RAL 寄存器模型生成 | ✅ 可用 |

---

## 安装

### 依赖

```bash
# 核心依赖（必须）
pip install pyverilog

# 仿真与 JIT（可选）
pip install numpy

# 逻辑综合（需要 iverilog + ABC）
brew install iverilog abc    # macOS
apt-get install iverilog abc # Ubuntu

# pyUVM 仿真（可选）
pip install cocotb
```

### 使用 Code（LLM / Agent）

rtlgen 专为 Code 使用而设计。推荐的工作方式：

1. **让 Code 读取 `pyRTL.md`** — 完整的 API 规范文档
2. **让 Code 浏览 `examples/`** — 从简单计数器到复杂加速器的设计模式
3. **让 Code 查看 `skills/`** — 可复用的硬件设计模块库
4. **让 Code 直接调用 API** — 生成、仿真、综合、评估，全部在 Python 中完成

```python
# Code 可以直接这样开始
from rtlgen import Module, Input, Output, Reg, VerilogEmitter, Simulator

class MyModule(Module):
    def __init__(self):
        super().__init__("MyModule")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.data = Output(8, "data")
        self.reg = Reg(8, "reg")

        @self.comb
        def _out():
            self.data <<= self.reg

        @self.seq(self.clk, self.rst)
        def _seq():
            self.reg <<= self.reg + 1

# 生成 Verilog
dut = MyModule()
print(VerilogEmitter().emit(dut))

# 仿真验证
sim = Simulator(dut)
sim.reset()
for i in range(10):
    sim.step()
    print(f"cycle {i}: data = {sim.get_int('data')}")
```

---

## 核心 API 设计思路

### 1. Python DSL：装饰器 + 上下文管理器

rtlgen 的设计目标是用**最 Pythonic 的方式**描述硬件，同时保持**完全可综合**的语义。

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
- `with If(...)` / `with Switch(...)`：上下文管理器让条件分支代码读起来像 Python，生成的是标准 Verilog `if/else` / `case`
- `ForGen`：在模块顶层生成 `generate for`，在 always 块内生成 `integer for`

### 2. 仿真引擎：AST 解释器 + JIT 编译器

rtlgen 内置了两级仿真后端：

#### 2.1 AST 解释器（`Simulator`）

基于 Python 的 AST 遍历解释器，支持完整的 rtlgen 语义：

```python
from rtlgen import Simulator

sim = Simulator(dut)
sim.reset()                    # 自动检测 rst/rst_n
sim.poke("a", 0x12)           # Verilator 风格 API
sim.poke("b", 0x34)
sim.step()                     # 推进一个时钟周期
assert sim.peek("result") == 0x46
```

**特性**：
- 层次化设计自动 `flatten`
- Memory 读写直接支持
- Trace 输出（table / VCD 格式）
- 多时钟域仿真
- X/Z 四态逻辑支持

#### 2.2 JIT 编译器（`sim_jit`）

将 AST 扁平化为 Python lambda 数组，消除解释开销：

```bash
# 默认启用 JIT
export RTLGEN_NO_JIT=0
```

| 设计 | AST 速度 | JIT 速度 | 加速比 |
|------|---------|---------|--------|
| NPU (NeuralAccel) | ~268 cps | ~1897 cps | **7.0x** |
| BOOM (简化核) | ~151 cps | ~610 cps | **4.0x** |

JIT 在 `Simulator` 初始化时自动编译，编译失败则静默回退到 AST 解释器。

#### 2.3 Python ↔ iverilog 协同仿真（`cosim`）

对同一个设计，同时在 Python `Simulator` 和 `iverilog` 中执行相同测试向量，逐 cycle 对比输出，确保 Python 仿真与 Verilog 语义一致。

### 3. UVM / Testbench 生成

rtlgen 支持**双后端 UVM**：

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

### 5. 逻辑综合

rtlgen 集成了 **ABC**（Berkeley Logic Synthesis and Verification Group）逻辑综合工具：

```python
from rtlgen import BLIFEmitter, ABCSynthesizer

# 生成 BLIF
blif = BLIFEmitter().emit(dut)

# 用 ABC 综合
synth = ABCSynthesizer()
result = synth.synthesize(blif, script="resyn2")
print(result.netlist)
```

支持：
- BLIF 网表生成
- ABC 脚本自定义（`resyn`, `resyn2`, `resyn3`, `if` 等）
- 门级网表解析（`netlist` 模块）
- 标准单元库解析（Liberty 格式）
- 静态时序分析（STA）

### 6. 后端能力（ placement → routing → signoff ）

rtlgen 包含一套**教学级后端流程**，从网表到 GDSII 的全链路：

```python
from rtlgen import (
    GateSizer, AnalyticalPlacer,
    GlobalRouter, DetailedRouter,
    FastRCExtractor, TimingAnalyzer
)

# 1. 门尺寸优化
sizer = GateSizer(liberty_lib)
sized_netlist = sizer.size(netlist, target_delay=1.0)

# 2. 解析式布局（EPlace-style 二次规划）
placer = AnalyticalPlacer()
placement = placer.place(sized_netlist, core_area=(0, 0, 1000, 1000))

# 3. 全局布线 + 详细布线
router = GlobalRouter()
routing = router.route(placement, placement.nets)

# 4. RC 提取
detailed_rc = DetailedRCExtractor(lef, tech_file)
rc_result = detailed_rc.extract(placement, routing)

# 5. 时序反馈 → RTL 优化
feedback = RTLFeedbackEngine()
report = feedback.analyze(rc_result, timing=TimingAnalyzer())
# 生成 RTL 修改建议：如某条路径需要插入 pipeline stage
```

**注意**：后端模块为教学/研究用途，精度与商业工具（ICC2/Innovus）有差距，但完整展示了从 RTL 到物理设计的流程。

### 7. Verilog → pyRTL 逆向导入

将遗留 Verilog / SystemVerilog 代码库转换为 rtlgen Python DSL：

```python
from rtlgen import VerilogImporter

importer = VerilogImporter("/path/to/verilog/repo")
importer.scan_repo()                          # 递归扫描 .v / .sv
importer.emit_repo("/output", package_name="imported")
```

**预处理兼容性**：内置 iverilog 宏展开 + SV 语法修复（`for (integer ...)`, `i++`, `'0` 等），支持 44/44 个复杂 EU 模块（含 `generate-for`、参数化宽度、子模块实例化）的完整转换。

---

## Skills 目录

`skills/` 是 rtlgen 的**硬件设计参考库**，收集可复用的领域特定模块和教程：

| 目录 | 内容 |
|------|------|
| `fundamentals/` | 标准库（FSM、FIFO、Arbiter）、API 教程 |
| `arithmetic/` | 乘法器（Karatsuba-Ofman）、SHA3、FP8 ALU |
| `cpu/` | RISC-V 核心、BOOM 风格 OoO CPU、分支预测器 |
| `npu/` | Systolic Array、Tensor Core、量化引擎、NeuralAccel 顶层 |
| `cryptography/` | 流密码、分组密码、后量子密码原语 |
| `codec/` | 线码、熵编码、压缩/解压 |
| `control/` | FSM、计数器、调度、流水线控制 |
| `memory-storage/` | SRAM 控制器、Cache、DMA、存储接口 |
| `video/` | 视频编解码器、显示流水线、HDMI/DP 控制器 |
| `image/` | ISP、图像滤波、缩放/旋转、DCT |
| `gpgpu/` | Shader Core、Warp 调度器、内存合并 |
| `accelerators/` | 领域特定加速器（ML 推理、信号处理） |
| `verification/` | 调试工具、测试平台模式、形式验证辅助 |
| `synthesis/` | ABC 集成、时序分析、面积估算流程 |
| `physical-design/` | Floorplan、布局、布线、DFT、Signoff |

每个 Skill 目录包含 `SKILL.md` 说明文档、Python 源文件和测试用例。

---

## 项目结构

```
rtlgen/
├── rtlgen/              # 核心框架
│   ├── core.py          # Signal / Module / Parameter / AST
│   ├── logic.py         # If / Else / Switch / ForGen / Mux / Cat
│   ├── codegen.py       # VerilogEmitter
│   ├── lint.py          # VerilogLinter
│   ├── sim.py           # Simulator (AST interpreter)
│   ├── sim_jit.py       # JITSimulator (flattened lambdas)
│   ├── cosim.py         # Python ↔ iverilog co-simulation
│   ├── verilog_import.py# Verilog → Python importer
│   ├── ppa.py           # PPAAnalyzer
│   ├── blifgen.py       # BLIF generation
│   ├── synth.py         # ABC integration
│   ├── netlist.py       # Gate-level netlist
│   ├── timing.py        # Static timing analysis
│   ├── sizing.py        # Gate sizing
│   ├── placement.py     # Analytical placement
│   ├── routing.py       # Global / detailed routing
│   ├── rc.py            # RC extraction
│   ├── rcextract.py     # Parasitic extraction → RTL feedback
│   ├── uvmgen.py        # SV UVM testbench generation
│   ├── pyuvm.py         # Native Python UVM framework
│   ├── pyuvmgen.py      # Python UVM testbench generation
│   ├── pyuvm_sim.py     # Python UVM simulation driver
│   ├── cocotbgen.py     # cocotb test generation
│   ├── svagen.py        # SVA assertion generation
│   ├── protocols.py     # AXI4 / APB / AHB / Wishbone
│   ├── pipeline.py      # Pipeline engine
│   ├── lib.py           # FSM / FIFO / Arbiter / etc.
│   ├── ram.py           # RAM wrappers
│   └── regmodel.py      # UVM RAL register model
├── examples/            # 示例设计（从计数器到加速器）
├── tests/               # pytest 测试套件
├── skills/              # 硬件设计参考库
│   ├── fundamentals/
│   ├── arithmetic/
│   ├── cpu/
│   ├── npu/
│   └── ...
├── pyRTL.md             # 完整 API 规范文档
└── README.md            # 本文件
```

---

## 快速开始

```bash
# 1. 克隆仓库
git clone <repo-url>
cd rtlgen

# 2. 安装核心依赖
pip install pyverilog numpy

# 3. 运行示例
cd examples
python counter.py
python pipeline_adder.py
python fsm_traffic.py

# 4. 运行测试
cd ..
pytest tests/ -v

# 5. 将 Verilog 代码库转换为 Python
cd examples
python -c "
from rtlgen import VerilogImporter
imp = VerilogImporter('../tests/eu')
imp.scan_repo()
imp.emit_repo('./eu_imported', package_name='eu')
print(f'Generated {len(imp.modules)} modules')
"
```

---

## 扩展方向

- **C++ 仿真引擎**：通过 pybind11 将 JIT 加速从 ~7x 提升到 50-500x（见 `cppengine.md`）
- **CDC 模块**：格雷码计数器、异步 FIFO 完整实现
- **TrueDualPortRAM**：两口均可读写
- **CHISEL 导出**：AST → FIRRTL 后端
- **形式验证集成**：SVA + yosys-smtbmc

---

## License

MIT License
