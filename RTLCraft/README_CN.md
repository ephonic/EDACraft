# RTLCraft (rtlgen) — 基于 Python 的 Verilog RTL 生成框架

> 面向对象、装饰器驱动的 Python API，用于描述可综合的 Verilog/SystemVerilog 数字逻辑。
> 这不是黑盒生成器，而是**白盒框架**——让 AI Agent 和开发者可以直接理解、操作和演进 RTL 抽象语法树 (AST)。

---

## 设计理念

### 白盒工具：让代码做推理

传统 HLS（高层次综合）工具是**黑盒**：你写 C++/Python，它吐 Verilog，中间发生了什么你完全不知道。出问题时无法调试。

RTLCraft 走相反的路线——它是**白盒框架**：

- **完全透明的 AST**：每个 `Input`、`Output`、`Reg`、`Wire`、`Assign`、`IfNode`、`SwitchNode` 都是显式的 Python AST 节点，可在任意时刻遍历、检查、修改、打印。
- **代码可读、代码可写**：LLM 和开发者都可以读取现有设计结构，执行增量修改、重构和优化。
- **工具-设计协同进化**：仿真器（JIT + AST 解释器）、PPA 分析器、UVM 生成器、Verilog 发射器都在同一 AST 上操作。任何一端的改动都立即传播到所有其他端。

```python
# 白盒：直接访问模块的 AST
dut._inputs       # 所有输入端口 → {name: Input}
dut._comb_blocks  # 组合逻辑块列表 → [[Assign, IfNode, ...]]
dut._seq_blocks   # 时序逻辑块列表 → [(clk, rst, async, active_low, [stmt...])]
```

### 三层正向设计方法

RTLCraft 使用三层元模型来桥接从高层次规格到可综合 RTL 的鸿沟：

```
规格说明 (Python/注释)
    ↓
第一层 — 功能模型 (functional.py)
    纯 Python 函数，无时序，无时钟。
    类型：Callable[**kwargs, Dict[str, int]]
    仿真：直接函数调用 (纳秒级)
    验证目标：算法正确性
    ↓
第二层 — 周期级模型 (cycle_level.py)
    基于 CycleContext 的闭包，寄存器精确，有时序。
    类型：Callable[[CycleContext], None]
    仿真：ArchSimulator (微秒级)
    验证目标：流水线时序、握手协议、状态机
    ↓
第三层 — RTL DSL 模型 (layer3_dsl/*.py)
    Module 子类，使用 Input/Output/Reg/Wire，可综合。
    仿真：Simulator with JIT (毫秒级，~45μs/步)
    验证目标：比特精确、周期精确
    ↓
Verilog (通过 VerilogEmitter)
```

**跨层一致性**：同一测试程序必须在三个层上产生完全相同的结果（L1 == L2 == L3）。由 `test_consistency.py` 强制保证。

### PPA 驱动优化闭环

```
DSL 模块 → VerilogEmitter → Verilog
    ↓
静态 AST 分析：
  - logic_depth（关键路径长度）
  - gate_count（等效 NAND2 门数）
  - reg_bits（时序面积）
  - fanout（线负载）
  - dead_signals（浪费面积）
    ↓
优化建议 → AI Agent 修改 DSL 代码
    ↓
重新发射、重新验证 → 收敛
```

PPA 分析器可以直接读取 Simulator 的波形 trace 做**动态功耗分析**（toggle rate → 动态功耗热点）。

### 验证技术栈

```
┌──────────────────────────────────────────────────┐
│  sim.py JIT (45μs/步) — 快速原型验证              │
│  Simulator(use_xz=True) — X/Z 传播               │
│  Golden trace → UVM scoreboard 自动对接           │
│  PPAAnalyzer — 静态/动态 PPA 分析                 │
│  VerilogLinter — 设计规则检查                     │
│  test_consistency.py — 三层一致性强制保证          │
└──────────────────────────────────────────────────┘
```

### 微架构模板库

RTLCraft 内置 22 个参数化、工业级硬件模板，位于 `rtlgen/lib.py`：

| 类别 | 模板 |
|----------|-----------|
| **流水线** | `PipelineShift`（可配深度 + valid/ready） |
| **FIFO** | `SyncFIFO`, `AsyncFIFO`（Gray 码 CDC） |
| **仲裁器** | `RoundRobinArbiter`, `FixedPriorityArbiter` |
| **存储器** | `DualPortRAM`, `CAM`, `DirectMappedCache`, `SetAssocCache` |
| **运算** | `MAC`（流水线化）, `SignedMultiplier`, `MultiCyclePath` |
| **控制** | `MultiCycleFSM`, `PipelineInterlock`, `StateTransition` |
| **跨时钟域** | `SyncCell`, `PulseSynchronizer`, `AsyncResetRel`, `GrayCounter` |
| **杂项** | `EdgeDetector`, `ClockGate`, `OneHotMux`, `BypassNetwork`, `LUT` |

### AI Agent 能力

本框架专为 LLM 驱动的硬件设计而设计：

| 能力 | 方式 | 用途 |
|-----------|------|------|
| **读取设计结构** | `module._comb_blocks`, `module._seq_blocks` | 理解现有电路 |
| **增量修改** | 插入/删除流水线级、修改位宽 | ECO、优化 |
| **迭代验证** | `sim.step()` → `sim.get_int()` → agent 检查 | 自主修复 bug |
| **PPA 反馈** | `PPAAnalyzer.report()` → agent 读取 → 编辑 DSL | 时序收敛 |

### 开始使用

```bash
# 安装
pip install -e .

# 运行 Thor GPU 三层一致性测试
python3 skills/thor/test_consistency.py

# PPA 分析
python3 -c "
from rtlgen.ppa import PPAAnalyzer
from rtlgen.lib import MAC
pa = PPAAnalyzer(MAC(width=16))
print(pa.report())
"
```

### 项目结构

```
rtlgen/                    # 核心框架
├── core.py                # AST 节点定义（Expr, Stmt, Signal, Module）
├── sim.py                 # Simulator (JIT + AST interpreter)
├── sim_jit.py             # JIT 编译后端 (~45μs/step)
├── codegen.py             # Verilog/SV 发射器
├── lib.py                 # 22 个微架构模板
├── ppa.py                 # PPA 分析器
├── uvmgen.py              # UVM testbench 生成器
├── uvm_scoreboard.py      # golden trace → UVM 桥接
├── arch_def.py            # ArchDefinition + CycleContext
├── arch_sim.py            # 架构仿真器
├── logic.py               # 控制流 (If/Switch/ForGen)
├── pipeline.py            # 流水线引擎
└── protocols.py           # AXI/APB/Wishbone 协议

skills/                    # 设计技能库 (18 个设计域)
├── thor/                  # Thor GPU (三层参考实现)
├── cpu/                   # RISC-V C910 OoO CPU
├── dsp/                   # 数字信号处理器
├── fft/                   # FFT 加速器
├── noc/                   # 网络片上系统
├── gpgpu/                 # GPGPU
└── ...

ref_rtl/                   # 开源 Verilog 参考实现
├── cpu/                   # T-Head C910
├── dsp/                   # Alex Forencich verilog-dsp
├── gpgpu/                 # Ventus GPGPU
└── ...
```
