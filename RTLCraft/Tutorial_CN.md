# RTLCraft 教程 — 从规格到硅片

> **Spec2RTL 工作流实践指南**：如何使用 RTLCraft 白盒框架、AI Agent 和领域特定 Skills 库，将自然语言或 YAML 规格转化为经过验证的 Verilog RTL。

---

## 目录

1. [什么是 Spec2RTL？](#什么是-spec2rtl)
2. [Agent-人类协作模型](#agent-人类协作模型)
3. [六阶段工作流](#六阶段工作流)
   - 第 0 阶段：规格摄入与架构定义
   - 第 1 阶段：架构仿真
   - 第 2 阶段：AgentPackage 生成
   - 第 3 阶段：DSL 实现
   - 第 4 阶段：PPA 优化
   - 第 5 阶段：代码生成与最终验证
4. [Skills 库](#skills-库)
   - 概述
   - DSL 模块清单（192 个模块）
   - 各域 Skill 详情
5. [架构框架参考](#架构框架参考)
6. [配置系统](#配置系统)
7. [工艺节点库](#工艺节点库)
8. [文件参考](#文件参考)

---

## 什么是 Spec2RTL？

**Spec2RTL** 是 RTLCraft 的端到端设计方法论，弥合高层次规格与可综合 RTL 之间的鸿沟：

```
规格（YAML / PDF / 自然语言）
    ↓
架构定义（ArchDefinition，含 PE 与互连）
    ↓
架构仿真（IPC、停顿分析、瓶颈检测）
    ↓
AgentPackage 生成（骨架 + 黄金测试 + 实现步骤）
    ↓
DSL 实现（Python → AST → 与行为模型验证）
    ↓
PPA 优化（AST 级分析 + ABC 综合反馈）
    ↓
代码生成（Verilog + lint + 文档包）
```

**设计哲学**：
- **架构无关**：适用于 CPU、GPGPU、NPU、协议控制器、流处理器、算法模块
- **行为优先**：行为函数本身就是 RTL 验证的黄金参考
- **Agent-人类协作**：Agent 执行，人类在检查点决策
- **基于 AST 的 PPA 分析**：综合代价昂贵，Agent 优化无需等待综合

---

## Agent-人类协作模型

| 角色 | 职责 | 原因 |
|------|------|------|
| **人类** | 提供规格文档、定义 PPA 目标、审批架构、审查关键实现、确认正确性 | 业务需求、权衡判断、最终责任 |
| **Agent** | 解析规格 → 生成架构 → 仿真 → 生成骨架 → 填充 DSL 逻辑 → 运行测试 → 优化 → 生成 Verilog → 产出文档 | 重复执行、大规模模式匹配、迭代优化 |

**原则**：Agent 准备，人类决策。Agent 执行，人类审查。Agent 从不自动批准检查点。

---

## 六阶段工作流

Agent **必须**按顺序执行这些阶段，**不得**跳过任何阶段。在每个检查点，Agent **必须**产出指定输出并**必须停止**等待人类批准。

```
┌─────────────────────────────────────────────────────────────────────┐
│  第 0 阶段：规格摄入与架构定义（Agent）                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 输出：ArchDefinition（含所有 PE、互连、模型）                    │  │
│  │       架构报告（markdown）                                      │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 0 — 人类审查 ArchDefinition，批准或修改                       │
│                              ▼                                      │
│  第 1 阶段：架构仿真（框架 + Agent 分析）                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 运行：ArchSimulator.run_with_workload(...)                     │  │
│  │ 输出：性能报告（IPC、停顿、瓶颈）                                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 1 — 人类审查性能报告                                         │
│                              ▼                                      │
│  第 2 阶段：AgentPackage 生成（框架 → Agent 审查）                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 运行：ArchSkeletonGenerator.generate_all(arch)                │  │
│  │ 输出：每个 PE 的 AgentPackage（骨架、黄金测试、步骤）            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 2 — 人类审查关键模块的 implementation_steps                   │
│                              ▼                                      │
│  第 3 阶段：DSL 实现（Agent 驱动）                                    │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 对每个 AgentPackage：按步骤 → 填充 DSL → 验证                   │  │
│  │ 覆盖率：每个模块 ≥95% 状态/分支/输入覆盖率                        │  │
│  │ 输出：完成的 DSL 模块 + 验证报告                                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 3 — 人类审查完成的 DSL，标记问题                             │
│                              ▼                                      │
│  第 4 阶段：PPA 优化（Agent 驱动，迭代）                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ PPAOptimizer.analyze() → Agent 修改 AST → 重新分析              │  │
│  │ 最多 3 次迭代                                                   │  │
│  │ 输出：优化后的模块 + 优化前后 PPA 报告                            │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 4 — 人类审查 PPA 结果                                        │
│                              ▼                                      │
│  第 5 阶段：代码生成与最终验证（框架 + Agent）                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ VerilogEmitter.emit() → VerilogLinter → 集成测试                │  │
│  │ 输出：Verilog 文件 + lint 报告 + 文档包                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  检查点 5 — 人类批准最终输出                                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 第 0 阶段：规格摄入与架构定义

**触发条件**：人类提供规格文档（PDF、Markdown、自然语言）。

**Agent 任务**：解析规格，提取架构组件，构建 `ArchDefinition`。

#### 0.1 架构提取

Agent 分析规格文档并识别：
1. **ProcessingElements**：模块边界、端口名/位宽、内部结构
2. **互连拓扑**：模块间信号连接
3. **域类型**：ISA（CPU/GPGPU/NPU）/ 协议（DDR/HDMI/PCIe）/ 流（视频/图像）/ 算法（LDPC/FFT）
4. **行为模板**：从框架库中选择合适的行为函数模板
5. **ModelProvider**：配置合适的域模型（RV32ISS、GPGPUModel 等）

#### 0.2 ProcessingElement 定义

**关键原则**：Agent **不**从零编写行为函数。
如同 gem5 的预构建 C++ SimObject，框架提供预构建的 Python 行为模板库。Agent **选择**合适的模板并从规格中**配置**参数。这确保了行为正确性。

```python
from rtlgen import (
    ProcessingElement, StateDesc, PortDesc, CycleContext,
    InterconnectSpec, HandshakeSpec, QueueSpec, ArchDefinition,
    ISA_Model, Protocol_Model, Stream_Model, Algorithm_Model,
    ifu_template, idu_template, alu_template, lsu_template,
    rob_template, regfile_template, datapath_template, fifo_template,
    bpu_template, issue_queue_template, pipeline_connect_template,
    circular_queue_template, writeback_arbiter_template,
    ConfigSpec, Config, PEParams, PresetSpecs,
    TechNode,
)
from rtlgen.processor_models import RV32ISS

# Agent 选择模板并从规格中配置参数
arch = ArchDefinition(
    name="C910",
    description="T-Head C910 RV64IMAFDC 超标量乱序核心",
    isa="riscv",
    processing_elements=[
        ProcessingElement(
            name="IFU", pe_type="ifu",
            pipeline_stage="fetch", issue_width=3, latency=5,
            inputs=[...],
            outputs=[...],
            state=[
                StateDesc("pc", "int", "程序计数器", rtl_type="reg",
                          rtl_width=40, default=0),
                StateDesc("bht_history", "int", "全局分支历史",
                          rtl_type="reg", rtl_width=8),
            ],
            behavior=ifu_template(
                fetch_width=3,
                pc_reset_value=0,
                btb_entries=64,
                bht_entries=512,
                ras_entries=16,
                ibuf_depth=16,
            ),
        ),
        # IDU、IU、LSU、RTU、PRegFile 类似定义...
    ],
    interconnects=[
        InterconnectSpec("IFU", "IDU", signals=[
            PortDesc("ifu_idu_ib_inst0_data", "output", 73),
            PortDesc("ifu_idu_ib_inst0_vld", "output", 1),
        ], flow_type="stream", delay_cycles=0),
    ],
    model=ISA_Model(iss=RV32ISS()),
    ppa_targets={"max_area": 50000, "target_freq": 1e9, "min_ipc": 2.0},
)
```

#### 0.3 GPGPU/协议扩展

对于 CPU 流水线之外的架构（GPGPU、协议控制器、流处理器），框架提供额外的构造：

**HandshakeSpec** — Valid/Ready 流控：
```python
InterconnectSpec(
    src_pe="cta_scheduler", dst_pe="warp_scheduler",
    signals=[...],
    flow_type="handshake",
    handshake=HandshakeSpec(
        valid_signal="dispatch_valid",
        ready_signal="warp_ready",
    ),
)
```

**QueueSpec** — 级间 FIFO 缓冲：
```python
InterconnectSpec(
    src_pe="lsu", dst_pe="l1_dcache",
    signals=[...],
    flow_type="fifo",
    queue=QueueSpec(depth=8, almost_full_threshold=6,
                    flow_control="valid_ready"),
)
```

**多实例 PE**（GPGPU Per-Warp/Per-SM）：
```python
warp_sched_multi = ProcessingElement(
    name="warp_scheduler", pe_type="warp_scheduler",
    num_instances=8,                  # 生成 warp_scheduler[0]..[7]
    instance_id_template="i",
    ...
)
```

#### 检查点 0

Agent **必须在此停止**并向人类呈现架构定义报告。人类审查 PE 列表、端口、互连拓扑和 PPA 目标，然后**批准**或**请求修改**。

---

### 第 1 阶段：架构仿真

**触发条件**：人类在检查点 0 批准了 ArchDefinition。

**框架任务**：通过 `ArchSimulator` 运行周期精确仿真。

```python
from rtlgen import ArchSimulator

sim = ArchSimulator(arch)
results = sim.run(num_cycles=100, init_inputs={"rst_n": 1})
report = sim.run_with_workload(
    workload=[0x00000013, 0x00100093, 0x00300113, ...],
    max_cycles=10000
)
```

**Agent 输出**：性能分析报告，含 IPC、停顿周期、各 PE 指标、瓶颈分析和建议。

#### 检查点 1

人类审查 IPC 和瓶颈，然后**批准**或**请求架构修改**。

---

### 第 2 阶段：AgentPackage 生成

**触发条件**：人类在检查点 1 批准了仿真报告。

**框架任务**：通过 `ArchSkeletonGenerator` 为每个 PE 生成 `AgentPackage`。

```python
from rtlgen import ArchSkeletonGenerator

gen = ArchSkeletonGenerator()
packages = gen.generate_all(arch)

ifu_pkg = packages["IFU"]
```

每个 `AgentPackage` 包含：

| 字段 | 类型 | 用途 |
|-------|------|---------|
| `pe` | ProcessingElement | 该模块的架构定义 |
| `behavioral_reference` | Callable | 可运行的周期精确行为模型（黄金参考） |
| `dsl_skeleton` | Module | 已声明端口和状态变量的 DSL 模块，逻辑待填充 |
| `golden_tests` | List[dict] | 100+ 测试向量 {inputs → expected_outputs} |
| `performance_targets` | dict | {max_latency, min_throughput, target_freq, ...} |
| `interconnect_interface` | dict | {upstream: [...], downstream: [...]} — 信号连接 |
| `implementation_steps` | List[str] | RTL 实现的增量 TODO 步骤 |
| `generate_loops` | List[GenerateLoopPattern] | Per-warp/Per-SM 实例化的复制模式 |
| `submodule_decomposition` | dict | 层次化 PE 子模块及内部连接 |

#### 检查点 2

人类审查关键模块的 `implementation_steps`，然后**批准**或**修改步骤**。

---

### 第 3 阶段：DSL 实现

**触发条件**：人类在检查点 2 批准了 AgentPackages。

**Agent 任务**：对每个 AgentPackage，按 `implementation_steps` 填充 DSL 逻辑，并与行为参考验证。

```python
pkg = packages["IFU"]

# 第 1 步：研究行为参考
ref = pkg.behavioral_reference
ctx = CycleContext(inputs={"rst_n": 1, "pc": 0x1000})

# 第 2 步：填充 DSL 逻辑（Agent 实现每一步）
# 第 3 步：与参考模型验证
# 第 4 步：运行黄金测试
```

**覆盖率要求**：每个模块 ≥95% 状态/分支/输入覆盖率。

**正确性如何保证**：
1. **行为模型即规格**：行为函数本身就是黄金参考
2. **从行为模型生成的黄金测试**：自动生成 100+ 测试向量
3. **每步验证**：每个实现步骤都包含验证子步骤
4. **检查点 3 人类审查**：人类审查完成的 DSL

#### 检查点 3

人类审查完成的 DSL 模块，标记问题。Agent **未经批准不得继续**。

---

### 第 4 阶段：PPA 优化

**触发条件**：人类在检查点 3 批准了 DSL。

**Agent 任务**：使用 AST 级分析 + ABC 综合反馈优化 PPA。

```python
from rtlgen import PPAOptimizer, PPAScore, PPAGoal

optimizer = PPAOptimizer(dut, spec)
result = optimizer.optimize(max_iterations=3)
```

**7 级 PPA 优化策略**：

| 策略 | 层级 | 作用 |
|----------|-------|-------------|
| PipelineInsertion | AST | 插入寄存器打断长路径 |
| ResourceSharing | AST | 互斥路径间共享算子 |
| BitwidthReduction | RTL | 去除冗余位宽扩展 |
| OperatorSelection | AST | 切换加法器/乘法器实现 |
| MuxBalancing | RTL | 重新平衡大 Mux 树 |
| FSMEncodingSelect | Arch | 选择二进制/独热/格雷编码 |
| SynthesisFeedback | Tech | ABC 网表面积/延迟反馈 |

#### 检查点 4

人类审查 PPA 优化前后对比，然后**批准**或**请求进一步优化**。

---

### 第 5 阶段：代码生成与最终验证

**触发条件**：人类在检查点 4 批准了 PPA 结果。

**框架 + Agent 任务**：生成 Verilog，运行 lint，产出文档包。

```python
from rtlgen import VerilogEmitter, VerilogLinter

verilog = VerilogEmitter().emit(dut)
lint_result = VerilogLinter().lint(verilog)
```

**强制要求**：Verilog 注释注入以确保可追溯性：
```python
from rtlgen import ModuleDocTemplate, fill_doc_template

doc = ModuleDocTemplate(
    module_name="C910_IFU",
    description="3-issue 超标量取指单元",
    author="RTLCraft Agent",
    version="1.0",
    parameters={"FETCH_WIDTH": 3, "BTB_ENTRIES": 64},
    interfaces={"ifu_idu": "Stream: 到 IDU 的指令包"},
)
fill_doc_template(dut, doc)
```

**生成输出**：
- Verilog 文件（`*.v`）
- Lint 报告
- 架构报告
- 验证报告
- PPA 报告
- 测试覆盖率报告

#### 检查点 5

人类批准最终输出。设计完成。

---

## Skills 库

### 概述

框架采用双层架构：

```
rtlgen/                    ← 基础框架（仅抽象）
├── core.py                Module, Signal, Input/Output/Wire/Reg
├── logic.py               If/Else/Switch/When/Mux/Cat
├── sim.py                 Simulator
├── codegen.py             VerilogEmitter
├── lint.py                VerilogLinter
├── pipeline.py            Handshake, Pipeline
├── protocols.py           Bundle, AXI4, APB 等
├── arch_def.py            ProcessingElement, ArchDefinition, ModelProvider
├── arch_sim.py            ArchSimulator（抽象引擎）
├── arch_skel.py           ArchSkeletonGenerator（骨架模板）
├── behaviors.py           基础模板注册表 + 通用模板
├── lib.py                 FSM, SyncFIFO, Arbiter（通用组件）
├── ram.py                 SRAM 原语
└── mem_timing.py          DDR3Timing, ns_to_cycles

skills/                    ← 领域扩展（具体实现）
├── cpu/                   玄铁 C910 RISC-V 超标量乱序核心
├── dsp/                   DSP 套件（有符号乘法器、I2S、DDS、CIC）
├── fft/                   Radix-2² SDF FFT 加速器
├── gpgpu/                 乘影 Ventus GPGPU 计算集群
├── image/isp/             Infinite-ISP v1.1 图像信号处理器
├── npu/                   神经网络处理单元
├── noc/                   网格片上网络
├── codec/video/           xk265 H.265/HEVC CTU 级编码器
├── codec/ldpc/            WiMax 802.16e LDPC 解码器
├── mem/cam/               内容寻址存储器
├── mem/ddr3/              DDR3 存储控制器
└── interfaces/            协议接口（AXI、SPI、UART、BTLE……）
```

### TemplateRegistry

```python
from rtlgen import TemplateRegistry

# 查看可用模板
TemplateRegistry.list()
# → ['fifo', 'datapath', 'axi_handshake', 'ifu', 'alu', ...]

# 按名称获取模板
tpl = TemplateRegistry.get("memory_controller")

# Skills 在导入时自动注册模板：
# from skills.cpu.behaviors import *  # 自动注册 ifu, alu 等
```

### DSL 模块清单

`skills/` 目录包含 **192 个 DSL 模块类**，分布在 **19 个 `dsl_modules.py` 文件**中。每个模块都是完整的 RTL 定义，含 Input/Output/Reg/Wire 端口声明、`seq`/`comb` 行为逻辑和 `instantiate` 结构层次调用。

| 领域 | Skill 路径 | 模块数 | 关键参数 |
|--------|-----------|---------|---------------|
| CPU | `skills/cpu/dsl_modules.py` | 7 | PA_WIDTH=40, VA_WIDTH=39, DATA_WIDTH=64 |
| DSP | `skills/dsp/dsl_modules.py` | 12 | 有符号乘法器、I2S、DDS、CIC |
| FFT | `skills/fft/dsl_modules.py` | 7 | Radix-2² SDF |
| GPGPU | `skills/gpgpu/dsl_modules.py` | 24 | NUM_SM=2, NUM_WARP=8 |
| 图像 | `skills/image/isp/dsl_modules.py` | 23 | RAW_W=12, MAC_W=22 |
| NPU | `skills/npu/dsl_modules.py` | 11 | NTILE=7, NDPE=40, EW=8, ACCW=32 |
| NoC | `skills/noc/dsl_modules.py` | 15 | FLIT_WIDTH=64, MESH_SIZE=8 |
| 编解码/视频 | `skills/codec/video/dsl_modules.py` | 38 | LCU_SIZE=64, IME_COST_WIDTH=28 |
| 编解码/LDPC | `skills/codec/ldpc/dsl_modules.py` | 6 | N=24, M=12, prec=4 |
| 存储/CAM | `skills/mem/cam/dsl_modules.py` | 5 | DATA_WIDTH=64, ADDR_WIDTH=5 |
| 存储/DDR3 | `skills/mem/ddr3/dsl_modules.py` | 4 | DFI 序列器、时序控制器 |
| 接口/BTLE | `skills/interfaces/btle/dsl_modules.py` | 15 | CRC-24、GFSK、whitening |
| 接口/SPI | `skills/interfaces/spi/dsl_modules.py` | 11 | CPOL/CPHA、主/从模式 |
| 接口/UART | `skills/interfaces/uart/dsl_modules.py` | 3 | AXI-Stream TX/RX |
| 接口/Wishbone | `skills/interfaces/wishbone/dsl_modules.py` | 2 | Reg slice、MUX-2 |
| 接口/AXI-S | `skills/interfaces/axis/dsl_modules.py` | 3 | 寄存器、适配器、广播 |
| 接口/AXI | `skills/interfaces/axi/dsl_modules.py` | 2 | DP RAM、AXIL RAM |
| 接口/I2C | `skills/interfaces/i2c/dsl_modules.py` | 1 | 7 位地址从机 |
| 接口/PCIe | `skills/interfaces/pcie/dsl_modules.py` | 3 | Pulse merge、FC counter |

**使用方法**：
```python
# 直接从 dsl_modules 导入
from skills.codec.video.dsl_modules import EncCtrl, ImeTop, FetchRefLuma

# 或通过 __init__.py（如可用）
from skills.dsp import DSP_MULT, CIC_DECIMATOR
from skills.interfaces.uart import UART_TX, UART_RX

# 实例化并生成 Verilog
from rtlgen import VerilogEmitter
m = EncCtrl()
verilog = VerilogEmitter().emit(m)
```

所有模块使用 `ModuleDocTemplate` + `fill_doc_template` 进行 Verilog 注释注入，参考常量包含在每个 `dsl_modules.py` 顶部。

### 各域 Skill 详情

#### CPU — `skills/cpu/`

玄铁 C910 RV64IMAFDC 超标量乱序核心：
- **dsl_modules.py**：7 个 DSL 模块类 — `C910IFU`、`C910IDU`、`C910IU`、`C910LSU`、`C910RTU`、`C910PRegFile`、`C910Core`
- **behaviors.py**：8 个行为模板 — `ifu`、`idu`、`alu`、`lsu`、`rob`、`regfile`、`bpu`、`issue_queue`
- **models.py**：`RV32ISS`、`RV32State`、`CPUModel`
- **arch_templates.py**：`Embedded`、`InOrder`、`OutOfOrder`、`MultiCore` 模板
- **skeleton_templates.py**：9 个 PE 类型步骤列表
- **design_flow.py**：完整 Spec2RTL 流程脚本
- **design_wizard.py**：交互式设计向导

#### DSP — `skills/dsp/`

DSP 套件（有符号乘法器、I2S、DDS、CIC）：
- **dsl_modules.py**：12 个类 — `DSP_MULT`、`IQ_JOIN`、`IQ_SPLIT`、`I2S_CTRL`、`PHASE_ACCUMULATOR`、`DSP_IQ_MULT`、`I2S_RX`、`I2S_TX`、`SINE_DDS_LUT`、`SINE_DDS`、`CIC_DECIMATOR`、`CIC_INTERPOLATOR`
- **models.py**：12 个黄金参考模型
- **behaviors.py**：12 个行为模板
- **arch_templates.py**：`build_dsp_arch()`、`DSP_SuiteModel`
- **skeleton_templates.py**：12 个 PE 类型步骤列表

#### FFT — `skills/fft/`

Radix-2² SDF FFT 加速器：
- **dsl_modules.py**：7 个类 — `FFTButterfly`、`FFTDelayBuffer`、`FFTMultiply`、`FFTTwiddle`、`FFTSdfUnit`、`FFTSdfUnit2`、`FFTController`
- **models.py**：7 个黄金参考模型
- **behaviors.py**：7 个行为模板
- **arch_templates.py**：`build_fft_arch()`、`FFTSuiteModel`
- **skeleton_templates.py**：7 个 PE 类型步骤列表

#### GPGPU — `skills/gpgpu/`

乘影 Ventus GPGPU 计算集群：
- **dsl_modules.py**：24 个类 — `WarpScheduler`、`DecodeUnit`、`Scoreboard`、`IBuffer`、`IBuffer2Issue`、`Issue`、`OperandCollector`、`SIMTStack`、`vALU`、`sALU`、`LSU`、`MUL`、`SFU`、`TC`、`vFPU`、`Writeback`、`InstructionCache`、`L1DCache`、`SharedMemory`、`ClusterToL2Arb`、`L2Distribute`、`CTAScheduler`、`SMWrapper`、`GPGPUTop`
- **behaviors.py**：`cta_scheduler_template`、`warp_scheduler_template`
- **models.py**：`GPUThread`、`GPUWarp`、`GPUState`、`GPGPUModel`
- **arch_templates.py**：`BasicGpuTemplate`、`ComputeClusterTemplate`、`StreamProcessorTemplate`
- **skeleton_templates.py**：8 个 PE 类型步骤列表

#### 图像/ISP — `skills/image/isp/`

Infinite-ISP v1.1 图像信号处理器：
- **dsl_modules.py**：23 个类 — `ISPAXIStreamIn`、`ISPCrop`、`ISPDPC`、`ISPBLC`、`ISPOECF`、`ISPDG`、`ISPLSC`、`ISPBNR`、`ISPWB`、`ISPAWBStats`、`ISPDemosaic`、`ISPCCM`、`ISPGamma`、`ISPAEStats`、`ISPCSC`、`ISPLDCI`、`ISPSharpen`、`ISPNR2D`、`ISPScale`、`ISPYUV`、`ISPAXIStreamOut`、`ISPAPBRegs`、`ISPController`
- **models.py**：`ISPModel` 黄金仿真器
- **behaviors.py**：22 个行为模板
- **arch_templates.py**：`build_isp_arch()`、`ISP_Model`
- **skeleton_templates.py**：22 个 PE 类型步骤列表

#### NPU — `skills/npu/`

神经网络处理单元：
- **dsl_modules.py**：11 个类 — `TopScheduler`、`GenericScheduler`、`MVUScheduler`、`EVRFScheduler`、`MFUScheduler`、`LDScheduler`、`MVU`、`MFU`、`EVRF`、`LD`、`NPUTop`
- **behaviors.py**：通用 `scheduler_template` + 工厂包装器（14 个模板）
- **models.py**：`MACArrayModel`、`NPUModel`、激活函数
- **arch_templates.py**：`NpuArchParams`、`Basic/DualPipeline/MultiTile` 模板
- **skeleton_templates.py**：6 个 PE 类型步骤列表
- **design_flow.py**：完整 Spec2RTL 第 0-5 阶段流程
- **design_wizard.py**：带自动分类的交互式设计向导

#### NoC — `skills/noc/`

网格片上网络：
- **dsl_modules.py**：15 个类 — `Buffer`、`Counter`、`RouteFunc`、`CrossBar`、`ST`、`OutEnGen`、`SelectGen`、`SetAlloc`、`STControler`、`VCAlloc`、`InputUnit`、`OutputUnit`、`Router`、`ProcessNode`、`Network`
- **models.py**：`FlitState`、`RouterState`、`RouterModel`、`NoCModel`
- **behaviors.py**：14 个行为模板
- **arch_templates.py**：`build_noc_arch()`、`NoC_Model`
- **skeleton_templates.py**：14 个 PE 类型步骤列表

#### 编解码/视频 — `skills/codec/video/`

xk265 H.265/HEVC CTU 级编码器：
- **dsl_modules.py**：38 个类 — `EncCtrl`、`PreiTop`、`PosiTop`、`ImeTop`、`FmeTop`、`RecTop`、`DbsaoTop`、`CabacTop`、`FetchTop`、`EncCore`、`Xk265Top`、8 个 IME 子模块、6 个 POSI 子模块、4 个 REC 子模块、3 个 DBSAO 子模块、3 个 CABAC 子模块、3 个 FETCH 子模块
- **models.py**：38 个周期精确 Python 仿真器
- **behaviors.py**：9 个流水线阶段行为模板
- **arch_templates.py**：`CodecArchParams`、`Baseline/HighPerf/LowPower` 模板
- **skeleton_templates.py**：12 个 PE 类型步骤列表

#### 编解码/LDPC — `skills/codec/ldpc/`

WiMax 802.16e LDPC 解码器（Min-Sum）：
- **dsl_modules.py**：6 个类 — `QuantizedAdder`、`QuantizedSubber`、`Comparator`、`CheckNode`、`VarNode`、`LDPC_Decoder`
- **models.py**：`CheckNode_Model`、`VarNode_Model`、`LDPCDecoder_Model`
- **behaviors.py**：6 个行为模板
- **arch_templates.py**：`build_ldpc_arch()`、`build_ldpc_params()`

#### 存储/CAM — `skills/mem/cam/`

内容寻址存储器：
- **dsl_modules.py**：5 个类 — `PriorityEncoder`、`RamDP`、`CamSRL`、`CamBRAM`、`CAM`
- **models.py**：`CAMModel`
- **arch_templates.py**：`build_cam_arch()`、`CAM_Model`

#### 存储/DDR3 — `skills/mem/ddr3/`

DDR3 存储控制器：
- **dsl_modules.py**：4 个类 — `DDR3FIFO`、`DDR3DFISeq`、`DDR3Core`、`DDR3Controller`
- **models.py**：`DDR3CoreModel`、`DDR3DFISeqModel`、`DDR3Model`
- **behaviors.py**：`memory_controller_template`、`dfi_sequencer_template`
- **arch_templates.py**：`build_ddr3_arch()`、`DDR3_Model`

#### 接口

| 协议 | 路径 | 模块数 | 描述 |
|----------|------|---------|-------------|
| BTLE | `skills/interfaces/btle/` | 15 | 蓝牙低功耗 PHY — CRC-24、GFSK、whitening |
| SPI | `skills/interfaces/spi/` | 11 | APB SPI 控制器（主/从）— CPOL/CPHA |
| UART | `skills/interfaces/uart/` | 3 | AXI-Stream UART TX/RX |
| Wishbone | `skills/interfaces/wishbone/` | 2 | Reg slice、MUX-2 |
| AXI-Stream | `skills/interfaces/axis/` | 3 | 寄存器、适配器、广播 |
| AXI | `skills/interfaces/axi/` | 2 | DP RAM、AXIL RAM |
| I2C | `skills/interfaces/i2c/` | 1 | 7 位地址从机 |
| PCIe | `skills/interfaces/pcie/` | 3 | Pulse merge、FC counter |
| 以太网 | `skills/interfaces/ethernet/` | — | PTP 时间戳提取（仅架构模板） |
| AXI-Lite | `skills/interfaces/axi_lite/` | — | 与 `axi/dsl_modules.py` 共享 AXIL_RAM |

### 添加新领域 Skill

1. 创建 `skills/<domain>/behaviors.py`，编写行为模板函数
2. 注册：`TemplateRegistry.register("<pe_type>", my_template)`
3. 创建 `skills/<domain>/skeleton_templates.py`，编写实现步骤列表
4. 注册：`register_<domain>_skeleton_steps(arch_skel._TEMPLATE_STEPS)`
5. 创建 `skills/<domain>/dsl_modules.py`，编写 DSL 模块类定义
6. 在 `skills/<domain>/__init__.py` 中导出 DSL 模块（如无循环导入风险）

---

## 架构框架参考

### ProcessingElement

```python
ProcessingElement(
    name="IFU",
    pe_type="ifu",                    # 用于模板查找
    pipeline_stage="fetch",
    issue_width=3,
    latency=5,
    inputs=[PortDesc("clk", "input", 1), ...],
    outputs=[PortDesc("ifu_idu_vld", "output", 1), ...],
    state=[StateDesc("pc", "int", "PC", rtl_type="reg", rtl_width=40), ...],
    behavior=ifu_template(...),       # 预构建行为模板
    can_stall=True,
    num_instances=1,                  # GPGPU：生成 for i=0..N-1
    instance_id_template="i",
)
```

### CycleContext

```python
def ifu_behavior(ctx: CycleContext):
    if ctx.inputs["rst_n"] == 0:
        ctx.state["pc"] = 0
        return
    # ... 取指逻辑 ...
    ctx.retire(1)  # 增加退休计数器以计算 IPC
```

### ModelProvider — 5 种域类型

| 类型 | 类 | 用例 |
|------|-------|----------|
| ISA | `ISA_Model(iss=RV32ISS())` | 带指令集的 CPU |
| 协议 | `Protocol_Model(...)` | 总线控制器、存储接口 |
| 流 | `Stream_Model(...)` | 视频/图像流水线 |
| 算法 | `Algorithm_Model(...)` | LDPC、FFT、密码学 |
| 存储 | `MemoryModel(...)` | DDR3、SRAM 控制器 |

### ArchDefinition → BehavioralSpec 桥接

```python
arch = ArchDefinition(...)

# 转换为分解框架的 BehavioralSpec
from rtlgen.decomposition import BehavioralSpec
spec = BehavioralSpec.from_arch_definition(arch)
```

---

## 配置系统

香山风格参数系统，用于架构探索：

```python
from rtlgen import ConfigSpec, Config, PEParams, PresetSpecs

# 扁平参数规格
spec = ConfigSpec({
    "FetchWidth": 3,
    "BTBEntries": 64,
    "BHTEntries": 512,
    "RASEntries": 16,
})

# 带父继承的层次化配置
config = Config(
    name="C910Config",
    parent=PresetSpecs.rv64_core(),  # 继承默认值
    overrides={
        "FetchWidth": 3,
        "BTBEntries": 64,
    },
)

# 流式构建器
params = PEParams().with_issue_width(3).with_btb(64).with_bht(512)
```

**PresetSpecs**：
- `rv32_core`：32 位嵌入式核心
- `rv64_core`：64 位应用核心
- `high_perf_core`：宽发射、大 ROB
- `embedded_core`：小面积、低功耗

---

## 工艺节点库

```python
from rtlgen import TechNode

# 可用节点：180nm, 130nm, 90nm, 65nm, 45nm, 28nm, 22nm, 14nm, 10nm, 7nm, 5nm
node = TechNode("7nm")

print(node.gate_delay)       # ~7.5 ps 每个 FO4 反相器
print(node.cell_area)        # ~0.03 um² 每个 NAND2
print(node.wire_delay_per_um) # ~0.2 ps/um
print(node.max_freq)         # ~3.5 GHz
print(node.pipeline_recommendation)  # "3-4 级流水线 @ 1GHz"
```

---

## 文件参考

| 文件 | 用途 |
|------|---------|
| `rtlgen/arch_def.py` | `ProcessingElement`、`StateDesc`、`PortDesc`、`CycleContext`、`InterconnectSpec`、`HandshakeSpec`、`QueueSpec`、`ArchDefinition`、`AgentPackage`、`ModelProvider`、`ISA_Model`、`Protocol_Model`、`Stream_Model`、`Algorithm_Model`、`MemoryModel`、`MemoryControllerSpec`、`CoverageTracker`、`FuConfig`、`ExuConfig`、`SchedulerConfig` |
| `rtlgen/arch_sim.py` | `ArchSimulator` — 周期精确架构建模仿真引擎。特性：`_HandshakeState`、`_FifoQueue`、`_expand_instances()`、`set_scoreboard()`、IPC 从 `total_retired / total_cycles` 计算。**关键**：`run()` 需要 `init_inputs={"rst_n": 1}`。 |
| `rtlgen/arch_skel.py` | `ArchSkeletonGenerator` — 为每个 PE 生成 AgentPackage（含 DSL 骨架、黄金测试、实现步骤）。**`GenerateLoopPattern`** 用于 per-warp/per-SM generate 循环。 |
| `rtlgen/decomposition.py` | `BehavioralSpec`、`StrategySpec`、`ConnectionSpec`、`DecompositionResult`、`SystemSimulator`、gem5 风格层次规格、`ModuleDoc`、`TopLevelDoc`、`PPAViolation` |
| `rtlgen/core.py` | `Module`、`Signal`、`Input/Output/Wire/Reg`、`BehavioralModule`、`BlackBoxModule`、`BehavioralRTLPair`、`ModelVersion`、`ModelRegistry`、`SourceLoc`、`IntentContext` |
| `rtlgen/sim.py` | `Simulator` — 单模块 RTL 仿真 |
| `rtlgen/sim_jit.py` | `JITSimulator` — 50–500× 加速，透明回退 |
| `rtlgen/ppa_optimizer.py` | `PPAOptimizer`、`OptimizationGuide`、`PPAScore`、`PPAGoal` |
| `rtlgen/codegen.py` | `VerilogEmitter`、`EmitProfile`、`ModuleDocTemplate`、`fill_doc_template` |
| `rtlgen/lint.py` | `VerilogLinter`、`LintIssue`、`LintResult` |
| `rtlgen/spec_ir.py` | `SpecIR`、`ArchitectureIR`、`PortSpec`、`FunctionSpec`、`PPASpec`、`TimingSpec`、`VerificationSpec` |
| `rtlgen/dsl_gen.py` | `DSLGenerator` — SpecIR + ArchitectureIR → DSL 模块 |
| `rtlgen/processor_models.py` | `RV32ISS`、`GPGPUModel`、`CPUModel`、`BehavioralModelFactory` |
| `rtlgen/iss_base.py` | `ISSBase` — 抽象 ISS 接口（任意 ISA） |
| `rtlgen/behaviors.py` | 预构建行为模板：`ifu`、`idu`、`alu`、`lsu`、`rob`、`regfile`、`datapath`、`fifo`、`axi_handshake`、`bpu`、`issue_queue`、`pipeline_connect`、`circular_queue`、`writeback_arbiter` |
| `rtlgen/tech_library.py` | `TechNode` — 工艺节点特征（180nm–5nm） |
| `rtlgen/mem_timing.py` | `DDR3Timing`（JEDEC 时序数据库）、`ns_to_cycles()` |
| `rtlgen/params.py` | 香山风格配置：`ConfigSpec`、`Config`、`PEParams`、`PresetSpecs` |

---

## 许可声明

RTLCraft 框架代码（Python DSL、AST、仿真器、生成器）采用自定义 MIT 许可证。允许个人学习和研究使用，但**禁止未经授权的商业用途**。如需商用，请联系作者与复旦大学（集成芯片与系统全国重点实验室）：efouth@gmail.com

`skills/` 目录中的 Python DSL 模块是基于第三方开源 Verilog 参考设计重新实现的。**原始参考 RTL 设计的版权归各自原作者所有。** 使用相关 IP 时必须遵守原始项目的许可证条款。完整的来源归属请见 [skills/README.md](skills/README.md)。

详见 [LICENSE](LICENSE) 文件。
