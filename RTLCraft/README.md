# RTLCraft (rtlgen) — Python API for Verilog RTL Generation

> An object-oriented, decorator-driven Python API for describing synthesizable Verilog / SystemVerilog digital logic.
> This is not a black-box generator, but a **white-box framework** — enabling AI agents and developers to directly understand, manipulate, and evolve the RTL abstract syntax tree (AST).

---

## Design Philosophy

### White-Box Tooling: Let Code Do Reasoning

Traditional HLS (High-Level Synthesis) tools are **black boxes**: you write C++/Python, they spit out Verilog, and you have no visibility into the intermediate representation. When something breaks, you cannot debug it.

RTLCraft takes the opposite approach — it is a **white-box framework**:

- **Fully transparent AST**: Every `Input`, `Output`, `Reg`, `Wire`, `Assign`, `IfNode`, and `SwitchNode` is an explicit Python AST node that you can traverse, inspect, modify, and print at any time.
- **Code-readable and Code-writable**: Both LLMs and developers can read existing design structure, perform incremental modifications, refactoring, and optimization.
- **Tool-design co-evolution**: The simulator (JIT + AST interpreter), PPA analyzer, UVM generator, and Verilog emitter all operate on the same AST. Changes propagate to all tools instantly.

```python
# White-box: directly access the module's AST
dut._inputs       # dict of all input ports → {name: Input}
dut._comb_blocks  # list of combinational logic blocks → [[Assign, IfNode, ...]]
dut._seq_blocks   # list of sequential blocks → [(clk, rst, async, active_low, [stmt...])]
```

### Three-Layer Forward-Design Methodology

RTLCraft uses a three-layer metamodel to bridge the gap between abstract specification and synthesizable RTL:

```
Specification (Python/comments)
    ↓
Layer 1 — Functional Model (functional.py)
    Pure Python functions, no timing, no clock.
    Type: Callable[**kwargs, Dict[str, int]]
    Sim: direct function call (ns-level)
    Verification: algorithm correctness
    ↓
Layer 2 — Cycle-Level Model (cycle_level.py)  
    CycleContext-based closures, register-accurate with timing.
    Type: Callable[[CycleContext], None]
    Sim: ArchSimulator (μs-level)
    Verification: pipeline timing, handshake, FSM
    ↓
Layer 3 — RTL DSL Model (layer3_dsl/*.py)
    Module subclasses with Input/Output/Reg/Wire, synthesizable.
    Sim: Simulator with JIT (ms-level, ~45μs/step)
    Verification: bit-exact, cycle-exact
    ↓
Verilog (via VerilogEmitter)
```

**Cross-layer consistency**: The same test program must produce identical results at all three layers (L1 == L2 == L3). This is enforced by `test_consistency.py`.

### PPA-Driven Optimization Loop

```
DSL Module → VerilogEmitter → Verilog
    ↓
Static AST Analysis:
  - logic_depth (critical path)
  - gate_count (equivalent NAND2 gates)
  - reg_bits (sequential area)
  - fanout (wire load)
  - dead_signals (wasted area)
    ↓
Suggestions → AI Agent modifies DSL code
    ↓
Re-emit, re-verify → converge
```

### Verification Stack

```
┌─────────────────────────────────────────────┐
│  sim.py JIT (45μs/step) — 快速原型验证        │
│  Simulator(rf, use_xz=True) — X/Z 传播       │
│  Golden trace → UVM scoreboard 自动对接      │
│  PPAAnalyzer — 静态/动态 PPA 分析            │
│  VerilogLinter — 设计规则检查                │
└─────────────────────────────────────────────┘
```

### Micro-Architecture Template Library

RTLCraft ships with 22 parameterized, production-inspired hardware templates in `rtlgen/lib.py`:

| Category | Templates |
|----------|-----------|
| **Pipeline** | `PipelineShift` (configurable depth + valid/ready) |
| **FIFO** | `SyncFIFO`, `AsyncFIFO` (Gray-code CDC) |
| **Arbiter** | `RoundRobinArbiter`, `FixedPriorityArbiter` |
| **Memory** | `DualPortRAM`, `CAM`, `DirectMappedCache`, `SetAssocCache` |
| **ALU** | `MAC` (pipelined), `SignedMultiplier`, `MultiCyclePath` |
| **Control** | `MultiCycleFSM`, `PipelineInterlock`, `StateTransition` |
| **CDC** | `SyncCell`, `PulseSynchronizer`, `AsyncResetRel`, `GrayCounter` |
| **Misc** | `EdgeDetector`, `ClockGate`, `OneHotMux`, `BypassNetwork`, `LUT` |

### AI Agent Capabilities

The framework is specifically designed for LLM-driven hardware design:

| Capability | How | Why |
|-----------|-----|-----|
| **Read design structure** | `module._comb_blocks`, `module._seq_blocks` | Understand existing circuits |
| **Modify incrementally** | Insert/remove pipeline stages, change widths | ECO, optimization |
| **Verify iteratively** | `sim.step()` → `sim.get_int()` → agent check | Fix bugs autonomously |
| **PPA feedback** | `PPAAnalyzer.report()` → agent reads → edits DSL | Timing closure |
| **Checkpoint/revert** | `CheckpointStore.snapshot()` before tool calls | Failure recovery |
| **Episodic memory** | `EpisodicMemory.record()` → `format_for_prompt()` | Learn from past mistakes |
| **Layer attribution** | `AnnotatedToolCall(layer, trace_id)` | Debug which layer caused failure |

### Agent Runtime Modules

RTLCraft includes three runtime modules for agent-driven workflows:

| Module | File | Purpose |
|--------|------|---------|
| **CheckpointStore** | `rtlgen/checkpoint.py` | Git-backed snapshot/revert before each tool call. `snapshot(layer, state)` creates a git commit; `revert(id)` restores any prior state. |
| **EpisodicMemory** | `rtlgen/memory.py` | Cross-session learning. `record()` writes episodes to JSONL in real time; `save_session()` aggregates error/success patterns into `.rtlcraft/memory/patterns/`; `format_for_prompt()` injects past lessons into the system prompt. |
| **Layer contracts** | `rtlgen/contracts.py` | Layer enum (L1 Spec / L2 Plan / L3 Exec), `AnnotatedToolCall(layer, trace_id, retry_count)`, `LayerTracer` for full execution path reconstruction. |

```python
from rtlgen.checkpoint import CheckpointStore
from rtlgen.memory import EpisodicMemory
from rtlgen.contracts import Layer, AnnotatedToolCall, LayerTracer

store = CheckpointStore(".")
ckpt = store.snapshot(layer=3, state={"tool": "bash"}, summary="before sim")
# ... execute ...
state = store.revert(ckpt)  # restore on failure
```

    L1!=L2!=L3 → AssertionError, design blocked.
    ↓
Verilog (~17,700 lines, generated_skill_ppa/cpu/hand_generated/)
```

#### Layer 1 — Functional Model

File: `skills/cpu/functional.py` (8 functions)

Pure-Python functions that describe **what** the hardware does, with no timing or cycle information. Each function takes keyword arguments and returns a dict of outputs:

```python
def iu_alu_functional(**kwargs) -> Callable:
    def func(src0: int = 0, src1: int = 0, opcode: int = 0) -> Dict:
        if opcode == 0: return {"result": src0 + src1}
        if opcode == 1: return {"result": src0 - src1}
        if opcode == 2: return {"result": src0 & src1}
        return {"result": src0 + src1}
    return func
```

**Simulation**: direct function call — `func(src0=5, src1=3, opcode=0)` → `{"result": 8}`.

**Purpose**: Captures architectural intent as the golden reference for downstream layers. A **Layer 1→2 guide** (`.md`) is auto-generated documenting ports, state variables, and behavioral descriptions.

#### Layer 2 — Cycle-Level Model

File: `skills/cpu/cycle_level.py` (86 models)

CycleContext-based models describing **when** each operation happens — register-accurate, with pipeline timing, written in pure Python:

```python
def iu_alu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pipe'] = 0; return
        src0 = ctx.get_input('src0', 0); src1 = ctx.get_input('src1', 0)
        ctx.state['pipe'] = src0 + src1
        ctx.set_output('result', ctx.state.get('pipe', 0))
    return behavior
```

**Simulation**: wrapped as `_beh_func` → `Simulator` (JIT disabled). Uses the same Simulator framework as Layer 3 for direct comparison.

**Purpose**: Introduces timing and register boundaries without RTL commitment. Verified against L3 via `LayerVerifier`. A **Layer 2→3 guide** is generated with register names, widths, and FSM states.

#### Layer 3 — DSL (rtlgen Modules)

Directory: `skills/cpu/layer3_dsl/` (77 files)

Synthesizable rtlgen DSL modules — `Module`, `Input`, `Output`, `Reg`, `Wire`, `If/Elif/Else`:

```python
class ALU(Module):
    def __init__(self, width=64):
        super().__init__("alu")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.op = Input(4, "op")
        self.a = Input(width, "a"); self.b = Input(width, "b")
        self.result = Output(width, "result")
        self.zero = Output(1, "zero")
        with self.comb:
            with If(self.op == 0): self.result <<= self.a + self.b
            with Elif(self.op == 1): self.result <<= self.a - self.b
            with Elif(self.op == 2): self.result <<= self.a & self.b
            with Else(): self.result <<= Const(0, width)
            self.zero <<= (self.result == 0)
```

**Simulation**: `Simulator(inst, use_xz=False)` — 94/96 classes PASS.

**Output**: `VerilogEmitter().emit(module)` → 166 Verilog `.v` files (~17,700 lines).

#### Cross-Layer Verification (Mandatory)

`rtlgen/forward.py` — `LayerVerifier`

```python
from rtlgen.forward import LayerVerifier

ok = LayerVerifier.verify(
    module_name="iu_alu",
    l1_func=iu_alu_functional(),
    l2_func=iu_alu_cycle(),
    l3_class=ALU,
    test_cases=[{
        "inputs": {"src0": 5, "src1": 3, "opcode": 0},
        "expect": {"result": 8},
    }],
)
```

If any layer disagrees, an `AssertionError` is raised — design is **blocked** until all three layers produce identical results for the same test vectors.

### Bidirectional Flow: Verilog ↔ Python DSL

RTLCraft supports a **bidirectional workflow**:

- **Forward**: Python DSL → AST → Verilog / SV / UVM / Testbench / Simulation
- **Reverse**: Verilog Repo → Python DSL (via `VerilogImporter`, requires pyverilog), converting legacy codebases into maintainable Python descriptions

This makes RTLCraft a **living tool chain** — capable of both green-field design and brown-field refactoring.

---

## Feature Overview

| Module | Capability | Status |
|--------|-----------|--------|
| `core` + `logic` | Python DSL → AST (signals, modules, logic control, state machines, type system: signed/unsigned, width inference, intent constraints, source tracking) | ✅ Mature |
| `codegen` | AST → Verilog-2001 / SystemVerilog (with submodule dedup, EmitProfile, source map) | ✅ Mature |
| `lint` | Post-generation lint + auto-fix (14 Verilog-level rules + 8 AST-level rules incl. width_truncation, signed_mix) | ✅ Mature |
| `sim` | Python AST interpreter (4-state logic, multi-clock, VCD export, breakpoint debugging) | ✅ Mature |
| `sim_jit` | Pure-Python JIT accelerator (50–500×), transparent fallback to interpreter | ✅ Available |
| `ppa` | AST-based logic depth / gate count / fanout / dead signal analysis, intent constraint checking | ✅ Available |
| `smt` | SMT-based combinational equivalence checking (z3) | ✅ Available |
| `verification` | BehavioralModelGenerator, DesignRuleChecker, ProtocolDescriptor | ✅ Available |
| `blifgen` + `synth` | ABC logic synthesis integration (BLIF → optimized netlist) | ✅ Available |
| `uvmgen` | SV UVM testbench auto-generation (interface / agent / env / test) | ✅ Available |
| `pyuvm` + `pyuvm_sim` | Native Python UVM framework + simulator driver | ✅ Available |
| `pyuvmgen` | Python UVM → SystemVerilog transpiler | ✅ Available |
| `cocotbgen` | cocotb test framework auto-generation | ✅ Available |
| `uvmvip` | APB / AXI4-Lite / AXI4 VIP generation | ✅ Available |
| `regmodel` | UVM RAL register model generation | ✅ Available |
| `pipeline` | Pipeline engine (auto handshake + back-pressure) | ✅ Available |
| `lib` | FSM / SyncFIFO / AsyncFIFO / Arbiter (FixedPriority + RoundRobin) / Decoder / PriorityEncoder / BarrelShifter / LFSR / CRC / Divider / Counter / EdgeDetector / StreamFIFO / FlatMemory / SpillRegister / RegSlice / CreditFlowControl / ClockGateCell / DataflowPipeline | ✅ Available |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB-Lite / Wishbone | ✅ Available |
| `ram` | Single-port / simple dual-port RAM wrappers | ✅ Available |
| `cosim` | Python ↔ iverilog co-simulation | ✅ Available |
| `verilog_import` | Verilog / SV → Python DSL (requires pyverilog) | ⚠️ Optional |
| `netlist` | Gate-level netlist parsing | ✅ Available |
| `liberty` | Liberty standard cell library parsing & generation | ✅ Available |
| `lef` | LEF physical library parsing & generation | ✅ Available |
| `passes` | PassManager framework (LintPass, ConstantFoldPass, DeadCodeElimPass) | ✅ Available |
| `registry` | Component registry with metadata (tags, area, latency, search) | ✅ Available |
| `behaviors` | TemplateRegistry for reusable behavior templates | ✅ Available |
| `params` | XiangShan-inspired parameter presets, fluent PEParams builder | ✅ Available |
| `arch_def` | Universal PE model (FuConfig / ExuConfig / Param / PEParams / Array / RegPool / PortGroup), CycleContext with memory/cache/register file/FIFO models | ✅ Available |
| `arch_planner` | Architecture Planner (SpecIR → ArchitectureIR, 4 categories) | ✅ Available |
| `dsl_gen` | DSL Skeleton Generator (ArchitectureIR → Module, 4 categories) | ✅ Available |
| `arch_sim` | Architecture-level simulator with back-pressure, IPC tracking, hazard detection | ✅ Available |
| `arch_skel` | PE-type-specific sub-module decomposition (28 connections for perf_core), implementation steps with behavior tags, hierarchical interconnection maps | ✅ Available |
| `ppa_optimizer` | PPA Score + 6 optimization strategies (pipeline, sharing, bitwidth, operator, mux, FSM) | ✅ Available |
| `verif_gen` | Verification Generator (reference model, directed/random tests, coverage, protocol checks) | ✅ Available |
| `decomposition` | Gem5-style hierarchy decomposition, pre-PPA violation detection | ✅ Available |
| `spec_ir` | Spec / Behavior / Cycle / Structural / Architecture IR dataclasses + OptimizableOp nodes | ✅ Available |
| `spec_extractor` | Spec Completer + SpecExtractor (YAML, templates, natural language) | ✅ Available |
| **`gen_requirement`** | ModuleRequirement, ReferenceSummary, GenerationContext, SubModuleInfo, ImplementationStep — structured data flow between layers | ✅ Available |
| **`behavior_extract`** | Behavior requirement extraction from ProcessingElement — detects valid/ready, state, control, and datapath patterns | ✅ Available |
| **`reference_extractor`** | Extracts structured summaries + actual code snippets from reference DSL modules in the skills library | ✅ Available |
| **`behavior_roundtrip`** | DSL-to-behavior adapter with full Simulator step() (comb+seq); event-level trace comparison between behavioral model and generated DSL | ✅ Available |
| **`skill_ppa`** | Skill-guided pipeline orchestrator: behaviors → arch → skeleton → agent_gen → PPA → verify → DSL → RTL → lint, with structured IR sidecars, review bundle export, and LLM iterative self-correction | ✅ Available |
| **`skill_retriever`** | Skill retrieval engine with sub-module-level matching and fine-grained relevance scoring | ✅ Available |
| **`dsl_parser`** | Safe DSL code parser with isolated namespace, syntax validation, and module instantiation | ✅ Available |
| **`prompt_builder`** | Serializes GenerationContext into 9-section Claude agent prompt (spec, references with code snippets, rules, verification, sub-modules, steps, skeleton state, DSL syntax, task) | ✅ Available |
| **`pattern_extractor`** | AST-level pattern extraction from DSL source (FSM, handshakes, pipelines, round-robin, FIFO, scoreboard) | ✅ Available |

---

## Core API Design

### 1. Python DSL: Decorators + Context Managers

RTLCraft's goal is to describe hardware in the **most Pythonic way** while maintaining **fully synthesizable** semantics.

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

**Key design decisions**:
- `<<=` operator: unified representation for blocking (`=`) and non-blocking (`<=`) assignments, automatically inferred from target signal type (`Wire`/`Reg`) and context (`@comb`/`@seq`)
- `with If(...)` / `with Switch(...)`: context managers make conditional branches read like Python, while generating standard Verilog `if/else` / `case`
- `ForGen`: generates `generate for` at module top level, and `integer for` inside always blocks
- `StateTransition`: resolves multi-assignment ambiguity in FSM by collecting `(condition, next_value)` pairs into a single priority Mux chain

### 2. Simulation Engine: AST Interpreter

Built-in Python AST traversal interpreter supporting full RTL semantics:

```python
from rtlgen import Simulator

sim = Simulator(dut)
sim.reset()                    # auto-detect rst/rst_n
sim.poke("a", 0x12)           # Verilator-style API
sim.poke("b", 0x34)
sim.step()                     # advance one clock cycle
assert sim.peek("result") == 0x46
```

**Features**:
- Hierarchical designs automatically flattened
- Direct Memory read/write support
- Trace output (table / VCD format)
- Multi-clock domain simulation
- X/Z four-state logic support
- Breakpoint debugging (`add_breakpoint` / `run_until_break`)

#### 2.1 JIT Simulation Acceleration (`sim_jit`)

```python
from rtlgen.sim_jit import JITSimulator

# 50–500× faster than AST interpreter, transparent fallback
sim = JITSimulator(dut)
sim.reset()
sim.poke("a", 0x12)
sim.step(1000)  # bulk cycle advance
```

### 3. UVM / Testbench Generation

#### 3.1 SystemVerilog UVM (`uvmgen`)

```python
from rtlgen import UVMEmitter

files = UVMEmitter().emit_full_testbench(dut)
# Generates: *_if.sv, *_pkg.sv, *_transaction.sv, *_driver.sv,
#            *_monitor.sv, *_agent.sv, *_scoreboard.sv, *_env.sv,
#            *_test.sv, tb_top.sv
```

#### 3.2 Native Python UVM (`pyuvm` + `pyuvm_sim`)

Run complete UVM testbenches in Python (component tree, sequence, TLM, phase, objection), with `Simulator` as the underlying driver:

```python
from rtlgen.pyuvm import UVMTest, UVMSequence, uvm_do, delay

class MyTest(UVMTest):
    async def run_phase(self, phase):
        seq = MySequence("seq")
        await seq.start(self.env.agent.sequencer)
```

This means you can **rapidly debug UVM platform logic in Python**, then export to SV for delivery to VCS/Questa/Xcelium.

#### 3.3 Python UVM → SV Transpilation (`pyuvmgen`)

Transpile Python UVM test code to standard SystemVerilog, including `uvm_component_utils`, `uvm_object_utils` macros, clocking blocks, etc.

### 4. AST-Based PPA Performance Evaluation

No need to wait for synthesis — perform rapid PPA analysis at the Python layer based on AST:

```python
from rtlgen import PPAAnalyzer

ppa = PPAAnalyzer(dut)
print(ppa.logic_depth("result"))    # critical path logic depth
print(ppa.gate_count())             # estimated gate count
print(ppa.fanout_analysis())        # high fanout signals
print(ppa.dead_signals())           # dead signal detection
print(ppa.toggle_rates())           # toggle rate estimation
```

All analysis is based on AST structure, completing in **seconds**, suitable for rapid architectural iteration in early design stages.

PPA-aware components enable automated optimization:
```python
from rtlgen.ppa import PPAAwareComponent, OptimizationAdvisor

class MyAccelerator(PPAAwareComponent):
    def __init__(self):
        super().__init__("MyAccelerator")
        self.advisor = OptimizationAdvisor(self)
        # Advisor suggests implementation strategies based on PPA targets
        strategy = self.advisor.recommend("fifo", target="area")
```

### 5. Logic Synthesis

RTLCraft integrates **ABC** (Berkeley Logic Synthesis and Verification Group):

```python
from rtlgen import BLIFEmitter, ABCSynthesizer

blif = BLIFEmitter().emit(dut)
synth = ABCSynthesizer()
result = synth.synthesize(blif, script="resyn2")
print(result.netlist)
```

Supports BLIF netlist generation, custom ABC scripts, gate-level netlist parsing, Liberty library parsing, and static timing analysis.

### 6. Protocol Bundles & Standard Components

#### 6.1 Protocol Bundles

```python
from rtlgen import AXI4, AXI4Lite, APB, AHBLite, AXI4Stream, Wishbone, Bundle

# All protocols are parameterizable by address/data width
axi = AXI4(id_width=4, addr_width=32, data_width=32, user_width=0)
apb = APB(addr_width=32, data_width=32)
```

Supports `Bundle.flip()` for direction reversal and `Bundle.connect()` for automatic wire mapping.

#### 6.2 Standard Component Library

```python
from rtlgen import FSM, SyncFIFO, AsyncFIFO, RoundRobinArbiter
from rtlgen import Decoder, PriorityEncoder, BarrelShifter, LFSR, CRC, Divider
from rtlgen import Counter, EdgeDetector, FixedPriorityArbiter, StreamFIFO
from rtlgen import FlatMemory, SpillRegister, RegSlice
from rtlgen import CreditFlowControl, ClockGateCell, DataflowPipeline
from rtlgen import SinglePortRAM, SimpleDualPortRAM
```

### 7. Pipeline Engine

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

Automatically generates inter-stage registers, `ready` back-pressure signals, and top-level handshake ports.

### 8. Verilog Import

Convert existing Verilog / SystemVerilog codebases to RTLCraft Python DSL:

```python
from rtlgen import VerilogImporter  # requires: pip install pyverilog

importer = VerilogImporter("/path/to/verilog/repo")
importer.scan_repo()
importer.emit_repo("/output", package_name="imported")
```

Built-in iverilog macro expansion + SV syntax repair (`for (integer ...)`, `i++`, `'0`, etc.).

### 9. SMT Equivalence Checking

Verify combinational equivalence between two module implementations using z3:

```python
from rtlgen.smt import check_combinational_equivalence
from rtlgen.lib import FixedPriorityArbiter

# Compare a hand-optimized arbiter against a naive reference
opt = FixedPriorityArbiter(4)
naive = NaiveArbiter(4)

result = check_combinational_equivalence(opt, naive, outputs={"grant"})
print(result)  # {'equivalent': True} or counterexample
```

Extracts per-output combinational drivers from `@comb` and `@seq` blocks, converts AST to z3 bit-vectors, and checks `ForAll(inputs, outputs_a == outputs_b)`. Supports `Mux`, `Concat`, `Switch`, and automatic width alignment.

---

## Architecture Framework

RTLCraft includes a complete architecture modeling and planning framework for building complex processor-like systems (CPU, GPGPU, NPU, protocol controllers).

### 10. Universal PE Model (`arch_def`)

A domain-agnostic PE (Processing Element) model inspired by XiangShan and gem5:

```python
from rtlgen.arch_def import PEParams, FuConfig, ExuConfig, Array, RegPool, PortGroup, CycleContext

params = PEParams()
params.add_fu(FuConfig("alu", ops=["add", "sub", "and", "or"], latency=1))
params.add_fu(FuConfig("mul", ops=["mul"], latency=3))
params.add_exu(ExuConfig("exu0", fus=["alu", "mul"], issue_width=2))

# Auto Array (combinational) vs Reg (sequential) selection
pool = RegPool("regfile", entries=32, width=64)
array = Array("sram", entries=1024, width=128)
```

#### CycleContext — Behavioral Simulation Engine

`CycleContext` is the central abstraction for cycle-accurate behavioral simulation. Each PE's `behavior(ctx)` function reads inputs, computes using model APIs, and writes outputs:

```python
def my_cpu_behavior(ctx: CycleContext):
    # Access memory/cache/register file models
    instr = ctx.memory_read(ctx.get_state("pc", 0x1000))
    ctx.retire(1)
    ctx.set_state("pc", ctx.get_state("pc") + 4)
```

`CycleContext` provides:
- **Input/Output** dicts for inter-PE communication
- **State/next_state** for sequential registers
- **MemoryModel**, **CacheModel**, **RegisterFileModel**, **FIFO** — pluggable behavioral models
- **Pipeline control**: stall, flush, retirement tracking

### 11. Architecture Planning & Skeleton Generation (`arch_planner` + `dsl_gen` + `arch_skel`)

```python
from rtlgen import SpecIR, ArchitecturePlanner, DSLGenerator

spec = SpecIR.from_yaml("...")
planner = ArchitecturePlanner(spec)
arch = planner.plan()
# → ArchitectureIR with auto-selected adder/multiplier/FSM based on PPA goals

# Generate DSL skeleton from ArchitectureIR
dut = DSLGenerator(spec, arch).generate()
```

`arch_skel` provides:
- **Sub-module decomposition**: hierarchical breakdown with explicit I/O and interconnection maps (e.g., `perf_core` with 28 connections across IFU→IDU→ALU→LSU→WB)
- **Implementation steps**: PE-type-specific step guides with behavior tags and 50-word functional descriptions
- **State variable inference**: automatic Reg vs Array vs Wire selection based on access patterns

### 12. Architecture Simulation (`arch_sim`)

Architecture-level simulator with back-pressure modeling and IPC tracking:

```python
from rtlgen.arch_sim import ArchSimulator

sim = ArchSimulator(arch)
sim.run(cycles=1000)
print(f"IPC: {sim.ipc}")
print(f"Stall cycles: {sim.stall_cycles}")
```

### 13. PPA Optimization Loop (`ppa_optimizer` + `decomposition`)

```python
from rtlgen import PPAOptimizer, PPAScore, PPAGoal
from rtlgen.decomposition import DecompositionAnalyzer

# Gem5-style hierarchy decomposition with pre-PPA violation detection
analyzer = DecompositionAnalyzer(dut)
violations = analyzer.check_ppa_constraints()

# 6-level optimization strategies
optimizer = PPAOptimizer(dut, spec)
result = optimizer.optimize(max_iterations=10)
```

**7-level PPA optimization strategies:**

| Strategy | Level | What It Does |
|----------|-------|-------------|
| PipelineInsertion | AST | Insert registers to break long paths |
| ResourceSharing | AST | Share operators across mutually exclusive paths |
| BitwidthReduction | RTL | Remove redundant width extensions |
| OperatorSelection | AST | Swap adder/multiplier implementations |
| MuxBalancing | RTL | Rebalance large mux trees |
| FSMEncodingSelect | Arch | Select binary/one-hot/gray encoding |
| SynthesisFeedback | Tech | ABC netlist area/delay feedback |

---

## Skill-Guided AI Generation Pipeline

RTLCraft's `skill_ppa` pipeline implements a **closed-loop, skill-guided RTL generation** flow powered by LLM agents. This is the AI agent workflow for generating RTL from behavior models — complementary to the three-layer verification methodology above.

```
behaviors → arch → skeleton → agent_gen → ppa_analyze → ppa_optimize → verify → repair → dsl_sim → rtl → lint
```

### How It Works

1. **Behavioral Stage** (`behaviors` stage): PE behavior functions are defined as `Callable[[CycleContext], None]` and cycle-accurately simulated via `ArchSimulator` to establish golden reference traces.

2. **Architecture Stage** (`arch` stage): ProcessingElements are organized into a complete architecture with interconnects, Memory/Cache/RegisterFile models, and hierarchical PE relationships.

3. **Skeleton Stage** (`skeleton` stage): Each PE is decomposed into:
   - `ModuleRequirement`: structured port/parameter/behavior specification
   - `SubModuleInfo[]`: hierarchical sub-modules with explicit I/O and interconnection maps
   - `ImplementationStep[]`: ordered tasks with behavior tags and functional descriptions
   - `BehaviorRequirement`: extracted from behavior functions via pattern classifiers

4. **Agent Generation** (`agent_gen` stage):
   - `GenerationContext` is built from all above, plus reference summaries from the skills library
   - `ReferenceExtractor` extracts **actual code snippets** (state declarations, comb/seq logic) from reference DSL modules
   - `prompt_builder` serializes into a 9-section prompt: module spec, reference patterns with code snippets, coding rules, verification contract, sub-module decomposition, implementation steps, skeleton state, DSL syntax reference, generation task
   - Claude API is called to generate DSL code
   - **Iterative self-correction**: if parse fails, errors are fed back to the LLM for repair (up to 2 retries)
   - Successfully parsed modules replace the skeleton

5. **Roundtrip Verification** (`behavior_roundtrip`):
   - Generated DSL is wrapped via `Simulator` (full comb + seq cycle-accurate execution)
   - Both behavioral model and DSL are run through the same test vectors
   - Event-level trace comparison identifies mismatches

```python
from rtlgen.skill_ppa import SkillPPARunner

runner = SkillPPARunner("hetero_riscv4")
runner.run_all()
# → Generates all PEs, verifies against behavioral models, emits RTL
```

### Key Data Structures

| Structure | Purpose |
|-----------|---------|
| `ModuleRequirement` | Structured module spec: name, ports, parameters, behaviors, verification hooks |
| `ReferenceSummary` | Extracted reference abstraction: design intent, interface/state/logic patterns, code snippets |
| `GenerationContext` | Unified agent input: target + references + rules + verification + sub-modules + steps |
| `SubModuleInfo` | Sub-module decomposition: name, type, description, inputs, outputs |
| `ImplementationStep` | Ordered task: name, goal, behavior_tags, keywords |
| `RoundtripResult` | Behavioral comparison: matched/missing/extra events, diffs |

### LLM Agent Integration

```python
# Environment variables for API access
export ANTHROPIC_AUTH_TOKEN="your-key"
export ANTHROPIC_BASE_URL="https://your-proxy"
export ANTHROPIC_MODEL="claude-sonnet-4-20250514"

# Run the full skill-guided pipeline
python -m rtlgen.skill_ppa --skill hetero_riscv4
```

The LLM agent receives a rich prompt containing:
- Complete module specification (ports, parameters, required behaviors)
- Reference patterns from the skills library (design intent, state patterns, logic patterns)
- **Actual code snippets** extracted from reference DSL source files
- Sub-module decomposition with interconnection maps
- Full implementation steps with 50-word functional descriptions
- Existing skeleton state variables
- DSL syntax reference with common error warnings
- Verification contract

On parse failure, the error is fed back with: *"The generated code has parse errors: [error]. Please fix these and output the corrected complete class definition."*

---

## Framework Enhancements

### 14. Type System: Width Inference & Signed Types

**Width Inference**: Binary operations automatically derive result widths matching Verilog semantics:

```python
a = Input(8, "a")
b = Input(8, "b")
result = a + b   # auto 9-bit (carry)
product = a * b  # auto 16-bit
eq = a == b      # auto 1-bit
```

**Signed/Unsigned Casting**: `signal.as_sint()` / `signal.as_uint()` for explicit signedness.

**Lint Rules**: `width_truncation` warns on implicit truncation; `signed_mix` detects unsigned/signed mixing.

### 15. Source Map (Python → Verilog Traceability)

Every `Assign` captures its Python source location:

```python
emitter = VerilogEmitter(emit_source_map=True)
verilog_text, source_map = emitter.emit_design_with_source_map(dut)
# Generated: // rtlcraft: source=my_design.py:42
```

### 16. EmitProfile (Verilog Style Configuration)

```python
from rtlgen import EmitProfile, VerilogEmitter

profile = EmitProfile(
    style="sv", always_comb=True, always_ff=True,
    explicit_nettype=True, reset_style="async_low",
)
sv = VerilogEmitter(profile=profile).emit(dut)
```

### 17. Intent Constraints (PPA-Aware Design)

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

### 18. PassManager (Compilation Pipeline)

```python
from rtlgen import PassManager, LintPass, ConstantFoldPass, DeadCodeElimPass

pm = PassManager()
pm.add(LintPass())
pm.add(ConstantFoldPass())
pm.add(DeadCodeElimPass())
results = pm.run(dut)
```

### 19. Component Registry

```python
from rtlgen import ComponentRegistry
arbiters = ComponentRegistry.search(tags=["arbitration"])
small = ComponentRegistry.search(max_area=100)
```

### 20. Spec-Driven RTL Generation (Spec2RTL)

Closed-loop spec-to-RTL flow: **YAML/NL Spec → SpecIR → BehaviorIR → CycleIR → MicroArchitectureIR (`ArchitectureIR`) → StructuralIR → DSL AST → Verification → PPA Optimization → Verilog**.

```python
from rtlgen import (
    SpecIR, SpecCompleter, SpecExtractor,
    ArchitecturePlanner, DSLGenerator,
    PPAOptimizer, PPAScore, PPAGoal,
    ReferenceModel, TestGenerator, CoverageTracker,
)
from rtlgen.synth import ABCSynthesizer

# Step 1: Parse spec (YAML, template, or natural language)
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

# Step 2: Complete spec (auto-infer ports, fill defaults)
completed = SpecCompleter.complete(spec)

# Step 3: Plan architecture (rules-based, PPA-aware)
planner = ArchitecturePlanner(completed)
arch = planner.plan()

# Step 5: Verify functional correctness
ref = ReferenceModel(completed)
assert ref.evaluate(a=10, b=20, c=5) == 205

tg = TestGenerator(completed)
tests = tg.generate_directed()

# Step 6: PPA score + optimization loop
goal = PPAGoal(max_logic_depth=completed.timing.latency_max)
optimizer = PPAOptimizer(module, spec)
result = optimizer.optimize(max_iterations=10)

# Step 7: Synthesis feedback (ABC → structured JSON)
synth = ABCSynthesizer()
feedback = synth.parse_feedback(synth_result)
```

In the skill-driven flow, `rtlgen.skill_ppa` now also emits a reviewable vertical slice for each PE type:

- JSON sidecars in `generated/<skill>/specs/`: `*_review_spec.json`, `*_behaviorir.json`, `*_cycleir.json`, `*_structuralir.json`, `*_specir.json`, `*_arch.json`
- Markdown review bundle in `generated/<skill>/review/`: `01_spec_review.md` through `07_lowering_report.md`
- Layer-to-layer checks recorded in `07_lowering_report.md`, so `dsl_from_spec` no longer hides all-fallback paths behind a PASS

This makes the stream-pipeline MAC path explicitly reviewable and comparable at each lowering stage before broader expansion to ALU/FSM/FIFO/cache/router blocks.

For the full tutorial, see [Tutorial.md](Tutorial.md).

---

## Skills Directory

`skills/` is RTLCraft's **hardware design reference library**, collecting reusable domain-specific modules and tutorials derived from third-party open-source RTL:

| Directory | Content | Status |
|-----------|---------|--------|
| `codec/ldpc/` | WiMax 802.16e LDPC decoder | ✅ Available |
| `codec/video/` | xk265 HEVC decoder (Fudan VIPcore) | ✅ Available |
| `cpu/` | T-Head C910 RISC-V core (Xuantie) | ✅ Available |
| `dsp/` | DSP library (FIR, IIR, CIC, FFT butterfly) | ✅ Available |
| `fft/` | R2²SDF FFT processor | ✅ Available |
| `fundamentals/` | Tutorial skills (counter, pipeline, API demo) | ✅ Available |
| `gpgpu/` | Ventus GPGPU (乘影) — ALU array, warp scheduler, tensor core | ✅ Available |
| `hetero_riscv4/` | Heterogeneous RISC-V SoC (PerfCore + EffCore + NoC + L1 cache + Coherence) | ✅ Available |
| `image/isp/` | Infinite-ISP v1.1 image signal processor | ✅ Available |
| `interfaces/` | AXI4, AXI4-Lite, AXI-Stream, APB, AHB-Lite, BTLE, Ethernet, I2C, PCIe, SPI, UART, Wishbone | ✅ Available |
| `mem/` | CAM, DDR3 SDRAM controller | ✅ Available |
| `noc/` | 2D mesh Network-on-Chip | ✅ Available |
| `npu/` | Intel FPGA-NPU | ✅ Available |
| `riscv64_soc/` | RISC-V 64-bit SoC with cache coherence | ✅ Available |

Each skill directory contains a `skills_index.yaml`, Python DSL modules (`dsl_modules.py`), behavior models (`behaviors.py`), architecture templates, and skeleton templates. See [skills/README.md](skills/README.md) for the full index with attribution and licensing.

---

## Project Structure

```
RTLCraft/
├── rtlgen/                   # Core framework (~40K lines)
│   ├── core.py               # Signal / Module / Parameter / AST / Intent / SourceLoc / Const
│   ├── logic.py              # If / Else / Switch / ForGen / StateTransition
│   ├── codegen.py            # VerilogEmitter / EmitProfile / Source Map / CSE pass
│   ├── lint.py               # VerilogLinter (14 Verilog + 8 AST rules + auto-fix)
│   ├── sim.py                # Simulator (AST interpreter, 4-state logic, JIT)
│   ├── sim_jit.py            # JIT accelerator (50–500×)
│   ├── cosim.py              # Python ↔ iverilog co-simulation
│   ├── verilog_import.py     # Verilog → Python importer (optional)
│   ├── ppa.py                # PPAAnalyzer + Intent constraint checking
│   ├── verification.py       # BehavioralModelGenerator + DesignRuleChecker
│   ├── verifier.py           # 4-level verification + iterative repair loop
│   ├── smt.py                # SMT combinational equivalence checker (z3)
│   ├── blifgen.py            # BLIF generation (bit-level expansion)
│   ├── synth.py              # ABC integration
│   ├── passes.py             # PassManager / LintPass / ConstantFoldPass / DeadCodeElimPass
│   ├── registry.py           # ComponentRegistry / ComponentMeta
│   ├── behaviors.py          # TemplateRegistry for reusable behavior templates
│   ├── params.py             # XiangShan-inspired parameter presets
│   ├── spec_ir.py            # SpecIR / ArchitectureIR / OptimizableOp
│   ├── spec_extractor.py     # SpecCompleter + SpecExtractor
│   ├── arch_def.py           # Universal PE model + CycleContext + models
│   ├── arch_planner.py       # Architecture Planner (4 categories)
│   ├── dsl_gen.py            # DSL Skeleton Generator
│   ├── arch_sim.py           # Architecture-level simulator (IPC, back-pressure)
│   ├── arch_skel.py          # Sub-module decomposition + implementation steps
│   ├── ppa_optimizer.py      # PPA Score + 6 optimization strategies
│   ├── verif_gen.py          # Verification Generator
│   ├── decomposition.py      # Gem5-style hierarchy decomposition
│   ├── netlist.py            # Gate-level netlist
│   ├── liberty.py            # Liberty standard cell library
│   ├── lef.py                # LEF physical library
│   ├── uvmgen.py             # SV UVM testbench generation
│   ├── pyuvm.py              # Native Python UVM framework
│   ├── pyuvmgen.py           # Python UVM → SV transpiler
│   ├── pyuvm_sim.py          # Python UVM simulation driver
│   ├── cocotbgen.py          # cocotb test generation
│   ├── uvmvip.py             # APB/AXI VIP generation
│   ├── protocols.py          # AXI4 / APB / AHB / Wishbone Bundle
│   ├── pipeline.py           # Pipeline engine
│   ├── lib.py                # FSM / FIFO / Arbiter / etc.
│   ├── ram.py                # RAM wrappers
│   ├── regmodel.py           # UVM RAL register model
│   ├── debug.py              # Debug probe utilities
│   ├── dpi_runtime.py        # DPI-C runtime
│   │
│   │── ── Agent Runtime ──
│   ├── checkpoint.py         # CheckpointStore: git-backed snapshot/revert
│   ├── memory.py             # EpisodicMemory: cross-session pattern learning
│   └── contracts.py          # Layer contracts: L1(Spec)/L2(Plan)/L3(Exec) + LayerTracer
│   │
│   │── ── Skill-Guided Generation ──
│   ├── gen_requirement.py    # ModuleRequirement / ReferenceSummary / GenerationContext
│   ├── behavior_extract.py   # Behavior requirement extraction + pattern classifiers
│   ├── reference_extractor.py# Reference summary + code snippet extraction
│   ├── behavior_roundtrip.py # DSL-to-behavior adapter + trace comparison
│   ├── skill_ppa.py          # Pipeline orchestrator + LLM agent integration
│   ├── skill_retriever.py    # Skill retrieval with sub-module matching
│   ├── dsl_parser.py         # Safe DSL code parser
│   ├── prompt_builder.py     # GenerationContext → Claude agent prompt
│   ├── pattern_extractor.py  # AST pattern extraction (FSM, handshake, pipeline)
│   │
│   │── ── Behavioral Models ──
│   ├── cache_model.py        # Cache model (hit/miss/fill/snoop)
│   ├── memory_model.py       # Memory model (read/write/service)
│   ├── regfile_model.py      # Register file model (read/write/forwarding)
│   └── hier_modules.py       # Hierarchical module utilities
│
├── skills/                   # Hardware design reference library (13 skill domains)
│   ├── hetero_riscv4/        # Heterogeneous RISC-V SoC (behaviors, arch, skeleton, DSL)
│   ├── gpgpu/                # Ventus GPGPU
│   ├── cpu/                  # T-Head C910
│   ├── riscv64_soc/          # RISC-V 64-bit SoC
│   ├── noc/                  # Network-on-Chip
│   ├── npu/                  # Intel FPGA-NPU
│   ├── fft/                  # R2²SDF FFT
│   ├── dsp/                  # DSP library
│   ├── codec/                # LDPC + Video codecs
│   ├── image/                # ISP
│   ├── mem/                  # CAM + DDR3
│   ├── interfaces/           # Protocol interfaces
│   └── fundamentals/         # Tutorial skills
│
├── README.md                 # This file (English)
├── README_CN.md              # Chinese version
├── Tutorial.md               # Spec-to-RTL tutorial
├── Tutorial_CN.md            # 中文版 Spec2RTL 教程
└── LICENSE                   # License
```

---

## Quick Start

### Three-Layer Flow Example

Run the complete spec-to-Verilog flow for an ALU:

```bash
# Layer 1: Functional model — pure function, no timing
python -c "
def alu_l1(src0, src1, op):
    ops = {0: src0+src1, 1: src0-src1, 2: src0&src1, 3: src0|src1, 4: src0^src1}
    return {'result': ops.get(op, src0+src1)}
print('L1:', alu_l1(5, 3, 0))  # {'result': 8}
"

# Layer 2: Cycle-level model with register timing
python -c "
from rtlgen.forward import _cycle_to_beh_func
from skills.cpu.cycle_level import iu_alu_cycle
beh = _cycle_to_beh_func(iu_alu_cycle(), ['result'])
beh._advance()
print('L2:', beh({'src0': 5, 'src1': 3}))  # {'result': 8}
"

# Layer 3: DSL → Verilog
python -c "
from rtlgen import VerilogEmitter
from skills.cpu.layer3_dsl.alu import ALU
top = ALU(64)
print(VerilogEmitter().emit(top))
"

# Cross-layer verification: L1==L2==L3 mandatory
python -c "
from rtlgen.forward import LayerVerifier
from skills.cpu.cycle_level import iu_alu_cycle
from skills.cpu.layer3_dsl.alu import ALU

def l1_func(**kw):
    ops = {0: kw['src0']+kw['src1'], 1: kw['src0']-kw['src1'],
           2: kw['src0']&kw['src1'], 3: kw['src0']|kw['src1'], 4: kw['src0']^kw['src1']}
    return {'result': ops.get(kw['opcode'], kw['src0']+kw['src1'])}

ok = LayerVerifier.verify(
    'alu', l1_func, ALU,
    test_cases=[{'inputs': {'src0':5,'src1':3,'opcode':0},
                 'expect': {'result':8}}],
    l2_func=iu_alu_cycle(),
)
print('Cross-layer:', 'PASS' if ok else 'FAIL')
"
```

### Quick Start (Framework)

```bash
# 1. Clone repository
git clone <repo-url>
cd RTLCraft

# 2. Install core dependencies
pip install pyverilog numpy anthropic

# 3. Run tutorial examples
cd skills/fundamentals/tutorials
python counter.py
python pipeline_adder.py
python api_demo.py
python lib_demo.py
python sim_counter_demo.py

# 4. Run skill-guided pipeline (requires ANTHROPIC_AUTH_TOKEN)
export ANTHROPIC_AUTH_TOKEN="your-key"
export ANTHROPIC_BASE_URL="https://your-proxy"  # optional
python -m rtlgen.skill_ppa --skill hetero_riscv4

# 5. Run a single skill's DSL modules
python -c "
from rtlgen import VerilogEmitter
from skills.arithmetic.multipliers.montgomery_mult_384 import MontgomeryMult384
top = MontgomeryMult384()
print(VerilogEmitter().emit_design(top))
"
```

---

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| `pyverilog` | Verilog parsing (verilog_import) | ⚠️ Optional |
| `numpy` | Simulation acceleration | ⚠️ Optional |
| `anthropic` | Claude API for LLM-driven generation | ⚠️ Optional |
| `iverilog` | Co-simulation | ⚠️ Optional |
| `abc` | Logic synthesis | ⚠️ Optional |
| `z3-solver` | SMT equivalence checking | ⚠️ Optional |

---

## AI-Driven Automated RTL Generation

RTLCraft supports end-to-end automation with AI coding assistants (Claude Code / Kimi Code):

1. **Spec → Python RTL**: AI generates Python DSL code from natural-language specifications
2. **Skill-Guided Generation**: Reference code snippets from the skills library are extracted and embedded in prompts, guiding the LLM toward proven patterns
3. **Iterative Self-Correction**: Parse errors are automatically fed back to the LLM for repair, converging on correct code
4. **Behavioral Verification**: Generated DSL is compared against golden behavioral models through event-level trace comparison
5. **PPA Optimization**: AST-based static analysis + ABC synthesis — area/timing reports guide AI optimization
6. **Code Generation**: Automatic output of Verilog / SV UVM Testbench / cocotb tests

For the full tutorial, see [Tutorial.md](Tutorial.md).

---

## Document-Driven SoC Design (Earphone Example)

RTLCraft is evolving from a single-file Spec2RTL script into a **document-driven, layered SoC design flow**. The `earphone/` directory is the pilot project:

```
earphone/
├── flow.py                 # New orchestration entry point
├── specs/                  # Top-level SoC specs and cross-layer reports
├── modules/                # Per-module directories
│   └── rv32/               # Pilot module (migrated first)
│       ├── specs/          # Module spec, test plan, test report
│       ├── src/            # behavior.py (L1), cycle.py (L2), dsl.py (L5) ...
│       └── tests/          # Module-level tests
├── integration/            # Integration tests and docs
├── system/                 # System-level tests and docs
├── top/                    # SoC top-level
└── tb/                     # Shared verification platform
```

Key ideas:

- **One directory per module**: each IP has its own `specs/`, `src/`, and `tests/`.
- **Documents are first-class inputs**: top-level spec drives module specs; module specs drive implementation and tests.
- **Templates**: `doc_templates/` provides industrial-pattern Markdown templates for top-level spec, module spec, test plan, and test report.
- **User confirmation loop**: Agent infers defaults for incomplete user specs and asks for confirmation on high-impact fields.
- **Tests propagate level by level**: L1 behavior tests → L2 cycle tests → L3 DSL tests → L6 Verilog tests → integration → system.

Run the new flow:

```bash
python -m earphone.flow
```

See `plan0614-doc.md` for the detailed roadmap.

---

## Third-Party Attribution

The `skills/` directory contains Python DSL modules that are re-implementations inspired by third-party open-source Verilog reference designs. **The copyright of the original reference RTL designs belongs to their respective original authors.** When using any skill, you must comply with the license terms of the original project.

> **Note**: The original Verilog reference designs are **not** included in this repository. The table below provides attribution and source links so you can independently review the original licenses.

### Verified Sources

| Skill Domain | Original Author / Organization | Source Link | License |
|-------------|-------------------------------|-------------|---------|
| `codec/ldpc` | crboth | <https://github.com/crboth/LDPC_Decoder> | Not specified |
| `codec/video` | VIPcore Group, Fudan University | <https://github.com/openasic-org/xk265> | Open source (see repo) |
| `cpu` (C910) | T-Head Semiconductor (Alibaba Group) | <https://github.com/T-head-Semi/openc910> | Apache-2.0 |
| `cpu` (XiangShan) | OpenXiangShan | <https://github.com/OpenXiangShan/XiangShan> | Mulan PSL v2 |
| `dsp` | Alex Forencich | <https://github.com/alexforencich/verilog-dsp> | MIT |
| `fft` | Nanamaru Namake | <https://github.com/nanamake/r22sdf> | MIT |
| `gpgpu` | THU-DSP-LAB / C*Core Technology (Ventus) | <https://github.com/THU-DSP-LAB/ventus-gpgpu-verilog> | Mulan PSL v2 |
| `hetero_riscv4` | Original work | — | Custom MIT |
| `image/isp` | 10xEngineers (Infinite-ISP) | <https://github.com/10x-Engineers/Infinite-ISP> | Apache-2.0 |
| `mem/cam` | Alex Forencich | <https://github.com/alexforencich/verilog-cam> | MIT |
| `mem/ddr3` | ultraembedded | <https://github.com/ultraembedded/core_ddr3_controller> | Apache-2.0 |
| `noc` | bakhshalipour | <https://github.com/bakhshalipour/NoC-Verilog> | Not specified |
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

## License

This project uses a custom MIT License. Personal use and research are permitted. **Commercial use requires prior authorization.**
For commercial licensing, please contact the author and Fudan University (State Key Laboratory of Integrated Chips and Systems): efouth@gmail.com

**Note on Third-Party IP:** The license above applies only to the RTLCraft framework code itself (the Python DSL, AST, simulators, and generators). It does **not** cover the Python DSL modules in `skills/` that are inspired by third-party reference designs, nor the original Verilog reference designs themselves. Users must independently review and comply with the license terms of each original project before using, modifying, or redistributing those designs. See the attribution table above and [skills/README.md](skills/README.md) for details.

See [LICENSE](LICENSE) for details.

---

## Related Documentation

- [skills/README.md](skills/README.md) — Skills directory overview with full attribution
- [README_CN.md](README_CN.md) — Chinese version of this document
- [Tutorial.md](Tutorial.md) — Spec-to-RTL tutorial with skills details
- [Tutorial_CN.md](Tutorial_CN.md) — 中文版 Spec2RTL 教程
