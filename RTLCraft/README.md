# RTLCraft (rtlgen) — Python API for Verilog RTL Generation

> An object-oriented, decorator-driven Python API for describing synthesizable Verilog / SystemVerilog digital logic.
> This is not a black-box generator, but a **white-box framework** — enabling Code / LLMs to directly understand, manipulate, and evolve the RTL abstract syntax tree (AST).

---

## Design Philosophy

### White-Box Tooling: Let Code Do Reasoning

Traditional HLS (High-Level Synthesis) tools are **black boxes**: you write C++/Python, they spit out Verilog, and you have no idea what happened in between. When something breaks, you cannot debug it.

RTLCraft takes the opposite approach — it is a **white-box framework**:

- **Fully transparent AST**: Every `Signal`, `Module`, and `Assign` created in Python is an explicit AST node that you can traverse, inspect, modify, and print at any time.
- **Code-readable and Code-writable**: LLMs and developers can not only generate code, but also read the structure of existing designs, perform incremental modifications, refactoring, and optimization.
- **Tool-design co-evolution**: The simulator, PPA analyzer, synthesizer, and other tools all operate on the same AST. Changes at any end instantly propagate to all other ends.

```python
# White-box: you can directly access the module's AST
dut._inputs       # dict of all input ports
dut._comb_blocks  # list of all combinational logic blocks
dut._seq_blocks   # list of all sequential logic blocks
```

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
| `arch_def` | Universal PE model (FuConfig / ExuConfig / Param / PEParams / Array / RegPool / PortGroup), works for CPU, GPGPU, NPU, protocol controllers | ✅ Available |
| `arch_planner` | Architecture Planner (SpecIR → ArchitectureIR, 4 categories) | ✅ Available |
| `dsl_gen` | DSL Skeleton Generator (ArchitectureIR → Module, 4 categories) | ✅ Available |
| `arch_sim` | Architecture-level simulator with back-pressure, IPC tracking, hazard detection | ✅ Available |
| `arch_skel` | PE-type-specific step guides, auto Array vs Reg selection | ✅ Available |
| `ppa_optimizer` | PPA Score + 6 optimization strategies (pipeline, sharing, bitwidth, operator, mux, FSM) | ✅ Available |
| `verif_gen` | Verification Generator (reference model, directed/random tests, coverage, protocol checks) | ✅ Available |
| `decomposition` | Gem5-style hierarchy decomposition, pre-PPA violation detection | ✅ Available |
| `spec_ir` | Spec IR / Architecture IR / OptimizableOp dataclasses | ✅ Available |
| `spec_extractor` | Spec Completer + SpecExtractor (YAML, templates, natural language) | ✅ Available |

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
from rtlgen.arch_def import PEParams, FuConfig, ExuConfig, Array, RegPool, PortGroup

params = PEParams()
params.add_fu(FuConfig("alu", ops=["add", "sub", "and", "or"], latency=1))
params.add_fu(FuConfig("mul", ops=["mul"], latency=3))
params.add_exu(ExuConfig("exu0", fus=["alu", "mul"], issue_width=2))

# Auto Array (combinational) vs Reg (sequential) selection
pool = RegPool("regfile", entries=32, width=64)
array = Array("sram", entries=1024, width=128)
```

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

`arch_skel` provides PE-type-specific step guides (in Chinese) for CPU, GPGPU, NPU, and protocol controller implementation.

### 12. Architecture Simulation (`arch_sim`)

Architecture-level simulator with back-pressure modeling and IPC tracking:

```python
from rtlgen.arch_sim import ArchSimulator

sim = ArchSimulator(dut)
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

For the full tutorial, see [Tutorial.md](Tutorial.md).

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

Closed-loop spec-to-RTL flow: **YAML/NL Spec → Spec IR → Architecture IR → DSL → RTL AST → Verification → PPA Optimization → Verilog**.

```python
from rtlgen import (
    SpecIR, SpecCompleter, SpecExtractor,
    ArchitecturePlanner, DSLGenerator,
    PPAOptimizer, PPAScore, PPAGoal,
    ReferenceModel, TestGenerator, VerificationRunner, CoverageTracker,
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
# → pipelined_datapath, 3 stages, wallace mul + carry_lookahead adder

# Step 4: Generate RTL skeleton
# dut = DSLGenerator(completed, arch).generate()

# Step 5: Verify functional correctness
ref = ReferenceModel(completed)
assert ref.evaluate(a=10, b=20, c=5) == 205

tg = TestGenerator(completed)
tests = tg.generate_directed()  # zero, max, boundary, powers of 2
random_tests = tg.generate_random(count=100, seed=42)

ct = CoverageTracker(completed)
for t in random_tests[:20]:
    ct.sample(t.inputs)

# Step 6: PPA score + optimization loop
goal = PPAGoal(max_logic_depth=completed.timing.latency_max)
score = PPAScore.compute(ppa_report, goal)

optimizer = PPAOptimizer(module, spec)
result = optimizer.optimize(max_iterations=10)

# Step 7: Synthesis feedback (ABC → structured JSON)
synth = ABCSynthesizer()
feedback = synth.parse_feedback(synth_result)
# → {"area": N, "depth": D, "suggestion": "..."}
```

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
| `gpgpu/` | Ventus GPGPU (乘影) — ALU array, warp scheduler, tensor core | ✅ Available |
| `image/isp/` | Infinite-ISP v1.1 image signal processor | ✅ Available |
| `interfaces/axi/` | AXI4 full master/slave | ✅ Available |
| `interfaces/axi_lite/` | AXI4-Lite slave RAM | ✅ Available |
| `interfaces/axis/` | AXI-Stream | ✅ Available |
| `interfaces/btle/` | Bluetooth Low Energy baseband | ✅ Available |
| `interfaces/ethernet/` | Ethernet MAC + PCS/PMA | ✅ Available |
| `interfaces/i2c/` | I2C master/slave | ✅ Available |
| `interfaces/pcie/` | PCIe DMA + AXI bridge | ✅ Available |
| `interfaces/spi/` | SPI master/slave | ✅ Available |
| `interfaces/uart/` | AXI-Stream UART | ✅ Available |
| `interfaces/wishbone/` | Wishbone bus | ✅ Available |
| `mem/cam/` | Content-addressable memory | ✅ Available |
| `mem/ddr3/` | DDR3 SDRAM controller | ✅ Available |
| `noc/` | 2D mesh Network-on-Chip | ✅ Available |
| `npu/` | Intel FPGA-NPU | ✅ Available |

Each skill directory contains a `SKILL.md`, `README.md`, Python source files, and design documentation. See [skills/README.md](skills/README.md) for the full index with attribution and licensing.

---

## Project Structure

```
RTLCraft/
├── rtlgen/                   # Core framework (~33K lines)
│   ├── core.py               # Signal / Module / Parameter / AST / Intent / SourceLoc
│   ├── logic.py              # If / Else / Switch / ForGen / StateTransition
│   ├── codegen.py            # VerilogEmitter / EmitProfile / Source Map
│   ├── lint.py               # VerilogLinter (14 Verilog + 8 AST rules + auto-fix)
│   ├── sim.py                # Simulator (AST interpreter, 4-state logic)
│   ├── sim_jit.py            # JIT accelerator (50–500×)
│   ├── cosim.py              # Python ↔ iverilog co-simulation
│   ├── verilog_import.py     # Verilog → Python importer (optional)
│   ├── ppa.py                # PPAAnalyzer + Intent constraint checking
│   ├── verification.py       # BehavioralModelGenerator + DesignRuleChecker + ProtocolDescriptor
│   ├── smt.py                # SMT combinational equivalence checker (z3)
│   ├── blifgen.py            # BLIF generation (bit-level expansion)
│   ├── synth.py              # ABC integration
│   ├── passes.py             # PassManager / LintPass / ConstantFoldPass / DeadCodeElimPass
│   ├── registry.py           # ComponentRegistry / ComponentMeta (21 components)
│   ├── behaviors.py          # TemplateRegistry for reusable behavior templates
│   ├── params.py             # XiangShan-inspired parameter presets
│   ├── spec_ir.py            # SpecIR / ArchitectureIR / OptimizableOp dataclasses
│   ├── spec_extractor.py     # SpecCompleter + SpecExtractor (YAML, templates, NL)
│   ├── arch_def.py           # Universal PE model (FuConfig / ExuConfig / PEParams)
│   ├── arch_planner.py       # Architecture Planner (4 categories)
│   ├── dsl_gen.py            # DSL Skeleton Generator (4 categories)
│   ├── arch_sim.py           # Architecture-level simulator (IPC, back-pressure)
│   ├── arch_skel.py          # PE-type-specific step guides
│   ├── ppa_optimizer.py      # PPA Score + 6 optimization strategies
│   ├── verif_gen.py          # Verification Generator (ref model, tests, coverage)
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
│   └── dpi_runtime.py        # DPI-C runtime
├── skills/                   # Hardware design reference library (21 skills)
├── README.md                 # This file (English)
├── README_CN.md              # Chinese version
├── Tutorial.md               # Spec-to-RTL tutorial with skills details
├── Tutorial_CN.md            # 中文版 Spec2RTL 教程
└── LICENSE                   # License
```

---

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd RTLCraft

# 2. Install core dependencies
pip install pyverilog numpy

# 3. Run tutorial examples
cd skills/fundamentals/tutorials
python counter.py
python pipeline_adder.py
python api_demo.py
python lib_demo.py
python sim_counter_demo.py

# 4. Run skill examples
cd skills/arithmetic/multipliers
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
| `iverilog` | Co-simulation | ⚠️ Optional |
| `abc` | Logic synthesis | ⚠️ Optional |
| `z3-solver` | SMT equivalence checking | ⚠️ Optional |

---

## AI-Driven Automated RTL Generation

RTLCraft supports end-to-end automation with AI coding assistants (Claude Code / Kimi Code):

1. **Spec → Python RTL**: AI generates Python DSL code from natural-language specifications
2. **Functional Validation**: Built-in AST interpreter + pyUVM framework — coverage reports feed back to AI
3. **PPA Optimization**: AST-based static analysis + ABC synthesis — area/timing reports guide AI optimization
4. **Code Generation**: Automatic output of Verilog / SV UVM Testbench / cocotb tests

For the full tutorial, see [Tutorial.md](Tutorial.md).

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
