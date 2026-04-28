# RTLCraft (rtlgen) — Python API for Verilog RTL 生成

> 一套面向对象、装饰器驱动的 Python API，用于描述可综合的 Verilog / SystemVerilog 数字逻辑。
> 这不是一个黑盒生成器，而是一个**白盒框架**——让代码（LLM / Agent）能够直接理解、操作和演化 RTL 的抽象语法树（AST）。

---

## 设计哲学

### 白盒工具：让 Code 做 Reasoning

RTLCraft 是一个**白盒框架**：

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
| `core` + `logic` | Python DSL → AST（信号、模块、逻辑控制、状态机） | ✅ 成熟 |
| `codegen` | AST → Verilog-2001 / SystemVerilog（含子模块去重） | ✅ 成熟 |
| `lint` | Verilog 生成后 lint + 自动修复（7 条规则） | ✅ 成熟 |
| `sim` | Python AST 解释器（4 态逻辑、多时钟、VCD 导出） | ✅ 成熟 |
| `ppa` | 基于 AST 的逻辑深度 / 门数 / 扇出 / 死信号分析 | ✅ 可用 |
| `blifgen` + `synth` | ABC 逻辑综合集成（BLIF → 优化网表） | ✅ 可用 |
| `uvmgen` | SV UVM testbench 自动生成（interface / agent / env / test） | ✅ 可用 |
| `pyuvm` + `pyuvm_sim` | 原生 Python UVM 框架 + 仿真器驱动 | ✅ 可用 |
| `pyuvmgen` | Python UVM → SystemVerilog 转译器 | ✅ 可用 |
| `cocotbgen` | cocotb 测试框架自动生成 | ✅ 可用 |
| `uvmvip` | APB / AXI4-Lite / AXI4 VIP 生成 | ✅ 可用 |
| `regmodel` | UVM RAL 寄存器模型生成 | ✅ 可用 |
| `pipeline` | 流水线引擎（自动握手 + 反压） | ✅ 可用 |
| `lib` | FSM / FIFO / Arbiter / BarrelShifter / LFSR / CRC / Divider | ✅ 可用 |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB-Lite / Wishbone | ✅ 可用 |
| `ram` | 单口 / 简单双口 RAM 封装 | ✅ 可用 |
| `cosim` | Python ↔ iverilog 协同仿真 | ✅ 可用 |
| `verilog_import` | Verilog / SV → Python DSL（需 pyverilog） | ⚠️ 可选依赖 |
| `netlist` | 门级网表解析 | ✅ 可用 |
| `liberty` | Liberty 标准单元库解析与生成 | ✅ 可用 |
| `lef` | LEF 物理库解析与生成 | ✅ 可用 |

---

## 核心 API 设计思路

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
- 断点调试（add_breakpoint / run_until_break）

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

---

## Skills 目录

`skills/` 是 RTLCraft 的**硬件设计参考库**，收集可复用的领域特定模块和教程：

| 目录 | 内容 | 状态 |
|------|------|------|
| `fundamentals/` | 标准库（FSM、FIFO、Arbiter）、API 教程 | ✅ 可用 |
| `arithmetic/` | 乘法器（KO-3 递归树）、SHA3、FP8 ALU | ✅ 可用 |
| `codec/` | 8b10b 编解码器（顺序/组合） | ✅ 可用 |
| `control/` | FSM 矩阵乘法、交通灯 FSM | ✅ 可用 |
| `cpu/boom/` | BOOM 风格乱序 RISC-V 核心（RV32I） | ✅ 可用 |
| `cpu/npu/` | NPU（脉动阵列 + Tensor Core + 编译器） | ✅ 可用 |
| `cryptography/` | ChaCha20 流密码 | ✅ 可用 |
| `synthesis/` | ABC 综合集成教程 | ✅ 可用 |
| `verification/` | 调试工具、仿真教程 | ✅ 可用 |
| `gpgpu/` | GPGPU 核心（ALU 阵列 + Warp 调度器 + Tensor Core） | ✅ 可用 |
| `memory-storage/` | SRAM / Cache / DMA（规划中） | 📋 预留 |
| `image/` | ISP / 图像滤波 / DCT（规划中） | 📋 预留 |
| `video/` | 视频编解码 / HDMI（规划中） | 📋 预留 |
| `accelerators/` | 领域特定加速器（规划中） | 📋 预留 |
| `physical-design/` | 布局布线 / DFT（规划中） | 📋 预留 |
| `npu/` | NPU 顶层（规划中） | 📋 预留 |

每个 Skill 目录包含 `SKILL.md` 说明文档、Python 源文件和设计文档。

---

## 项目结构

```
RTLCraft/
├── rtlgen/                   # 核心框架
│   ├── core.py               # Signal / Module / Parameter / AST
│   ├── logic.py              # If / Else / Switch / ForGen / StateTransition
│   ├── codegen.py            # VerilogEmitter（Verilog 代码生成）
│   ├── lint.py               # VerilogLinter（7 条规则 + auto-fix）
│   ├── sim.py                # Simulator（AST 解释器，4 态逻辑）
│   ├── cosim.py              # Python ↔ iverilog 协同仿真
│   ├── verilog_import.py     # Verilog → Python 导入（可选）
│   ├── ppa.py                # PPAAnalyzer（静态/动态分析）
│   ├── blifgen.py            # BLIF 网表生成（位级展开）
│   ├── synth.py              # ABC 综合集成
│   ├── netlist.py            # 门级网表解析
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
├── skills/                   # 硬件设计参考库
│   ├── fundamentals/
│   ├── arithmetic/
│   ├── codec/
│   ├── control/
│   ├── cpu/
│   ├── cryptography/
│   ├── gpgpu/
│   └── ...
├── pyRTL.md                  # 完整 API 规范文档
├── README_CN.md              # 本文档（中文）
├── README.md                 # English version
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

# 5. 运行技能示例
cd ../../arithmetic/multipliers
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

---

## 扩展方向

- **C++ 仿真引擎**：通过 pybind11 提升仿真速度 50-500x
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

详细教程请查看 [RTLGEN_CN.md](RTLGEN_CN.md)。

---

## 许可协议

本项目采用自定义 MIT 许可证。允许个人学习和研究使用，但**禁止未经授权的商业用途**。
如需商用，请联系作者与复旦大学（集成芯片与系统全国重点实验室）：efouth@gmail.com

详见 [LICENSE](LICENSE) 文件。

---

## 相关文档

- [RTLGEN_CN.md](RTLGEN_CN.md) — AI 自动 RTL 生成教程（中文版）
- [RTLGEN.md](RTLGEN.md) — Automated RTL Generation Tutorial (English)
- [skills/skills.md](skills/skills.md) — Skills 目录总览
