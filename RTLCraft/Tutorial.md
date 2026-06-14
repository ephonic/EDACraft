# RTLCraft Tutorial — From Specification to Silicon

> **A hands-on guide to the Spec2RTL workflow**: how to go from a natural-language or YAML specification to verified Verilog RTL using RTLCraft's white-box framework, AI agents, and the domain-specific skills library.

---

## Table of Contents

1. [What is Spec2RTL?](#what-is-spec2rtl)
2. [Agent-Human Collaboration Model](#agent-human-collaboration-model)
3. [The 6-Phase Workflow](#the-6-phase-workflow)
   - Phase 0: Spec Ingestion & Architecture Definition
   - Phase 1: Architecture Simulation
   - Phase 2: AgentPackage Generation
   - Phase 3: DSL Implementation
   - Phase 4: PPA Optimization
   - Phase 5: Code Generation & Final Verification
4. [Three-Layer Forward Design Methodology](#three-layer-forward-design-methodology)
   - The Problem
   - Layer 1: Functional Model
   - Layer 2: Cycle-Level Model
   - Layer 3: DSL (rtlgen Modules)
   - Cross-Layer Verification
   - Concrete Example: ALU
   - Verification Philosophy
5. [Cross-Layer Constraint & Intent Framework](#cross-layer-constraint--intent-framework)
   - Motivation
   - Core Abstractions
   - Forward Propagation
   - Backward Validation & Feedback
   - Design Scaffold
   - Usage Example
6. [Skills Library](#skills-library)
   - Overview
   - DSL Module Inventory (192 modules)
   - Per-Domain Skill Details
7. [Architecture Framework Reference](#architecture-framework-reference)
8. [Configuration System](#configuration-system)
9. [Technology Node Library](#technology-node-library)
10. [Files Reference](#files-reference)

---

## What is Spec2RTL?

**Spec2RTL** is RTLCraft's end-to-end design methodology that bridges the gap between high-level specifications and synthesizable RTL:

```
Spec (YAML / PDF / Natural Language)
    ↓
Architecture Definition (ArchDefinition with PEs & Interconnects)
    ↓
Architecture Simulation (IPC, stall analysis, bottleneck detection)
    ↓
AgentPackage Generation (skeleton + golden tests + implementation steps)
    ↓
DSL Implementation (Python → AST → verified against behavior model)
    ↓
PPA Optimization (AST-level analysis + ABC synthesis feedback)
    ↓
Code Generation (Verilog + lint + documentation bundle)
```

**Design Philosophy**:
- **Architecture-agnostic**: works for CPUs, GPGPUs, NPUs, protocol controllers, stream processors, algorithm blocks
- **Behavior-first**: the behavior function IS the golden reference for RTL verification
- **Agent-human collaboration**: agent executes, human decides at checkpoints
- **PPA analysis based on AST**: synthesis is expensive and unnecessary for agent optimization

The current implementation also exposes a reviewable lowering slice:

```text
SpecIR
  -> BehaviorIR
  -> CycleIR
  -> MicroArchitectureIR (via ArchitectureIR)
  -> StructuralIR
  -> DSL AST
```

For each generated PE type, `rtlgen.skill_ppa` writes both JSON sidecars and a markdown review bundle so the human can inspect each lowering stage before sign-off.

---

## Agent-Human Collaboration Model

| Role | Responsibility | Why |
|------|---------------|-----|
| **Human** | Provide spec document, define PPA targets, approve architecture, review key implementations, confirm correctness | Business requirements, trade-off judgment, final accountability |
| **Agent** | Parse spec → generate architecture → simulate → generate skeletons → fill DSL logic → run tests → optimize → generate Verilog → produce documentation | Repetitive execution, large-scale pattern matching, iterative optimization |

**Principle**: Agent prepares, human decides. Agent executes, human reviews. Agent never auto-approves a checkpoint.

---

## The 6-Phase Workflow

The agent **must** execute these phases in order. It **must not** skip any phase. At each checkpoint, it **must** produce the specified output and **must stop** for human approval.

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 0: Spec Ingestion & Architecture Definition (Agent)           │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Output: ArchDefinition with all PEs, interconnects, model     │  │
│  │       Architecture report (markdown)                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 0 — Human reviews ArchDefinition, approves or modifies  │
│                              ▼                                      │
│  Phase 1: Architecture Simulation (Framework + Agent analysis)      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Run:  ArchSimulator.run_with_workload(...)                     │  │
│  │ Output: Performance report (IPC, stalls, bottlenecks)         │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 1 — Human reviews performance report                    │
│                              ▼                                      │
│  Phase 2: AgentPackage Generation (Framework → Agent review)        │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Run:  ArchSkeletonGenerator.generate_all(arch)                │  │
│  │ Output: AgentPackage per PE (skeleton, golden tests, steps)   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 2 — Human reviews implementation_steps for key modules  │
│                              ▼                                      │
│  Phase 3: DSL Implementation (Agent-driven)                         │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ For each AgentPackage: follow steps → fill DSL → verify       │  │
│  │ Coverage: ≥95% state/branch/input coverage per module          │  │
│  │ Output: Completed DSL Modules + verification report           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 3 — Human reviews completed DSL, flags issues           │
│                              ▼                                      │
│  Phase 4: PPA Optimization (Agent-driven, iterative)                │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ PPAOptimizer.analyze() → agent modifies AST → re-analyze      │  │
│  │ Max 3 iterations                                              │  │
│  │ Output: Optimized Modules + before/after PPA report           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 4 — Human reviews PPA results                           │
│                              ▼                                      │
│  Phase 5: Code Generation & Final Verification (Framework + Agent)  │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ VerilogEmitter.emit() → VerilogLinter → Integration test      │  │
│  │ Output: Verilog files + lint report + documentation bundle    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ▼                                      │
│  CHECKPOINT 5 — Human approves final output                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Phase 0: Spec Ingestion & Architecture Definition

**Trigger**: Human provides a spec document (PDF, Markdown, natural language).

**Agent task**: Parse the spec, extract architecture components, construct `ArchDefinition`.

#### 0.1 Architecture Extraction

The agent analyzes the spec document and identifies:
1. **ProcessingElements**: module boundaries, port names/widths, internal structures
2. **Interconnect topology**: signal connections between modules
3. **Domain type**: ISA (CPU/GPGPU/NPU) / Protocol (DDR/HDMI/PCIe) / Stream (video/image) / Algorithm (LDPC/FFT)
4. **Behavior templates**: select appropriate behavior function templates from the framework library
5. **ModelProvider**: configure the appropriate domain model (RV32ISS, GPGPUModel, etc.)

#### 0.2 ProcessingElement Definition

**Key principle**: The agent does **NOT** write behavior functions from scratch.
Like gem5's pre-built SimObjects with verified C++ behavior, the framework provides a library of pre-built Python behavior templates. The agent **SELECTS** the right template and **CONFIGURES** parameters from the spec. This ensures behavior correctness.

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

# Agent selects templates and configures parameters from spec
arch = ArchDefinition(
    name="C910",
    description="T-Head C910 RV64IMAFDC superscalar out-of-order core",
    isa="riscv",
    processing_elements=[
        ProcessingElement(
            name="IFU", pe_type="ifu",
            pipeline_stage="fetch", issue_width=3, latency=5,
            inputs=[...],
            outputs=[...],
            state=[
                StateDesc("pc", "int", "Program counter", rtl_type="reg",
                          rtl_width=40, default=0),
                StateDesc("bht_history", "int", "Global branch history",
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
        # IDU, IU, LSU, RTU, PRegFile similarly defined...
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

#### 0.3 GPGPU/Protocol Extensions

For architectures beyond CPU pipelines (GPGPUs, protocol controllers, stream processors), the framework provides additional constructs:

**HandshakeSpec** — Valid/Ready Flow Control:
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

**QueueSpec** — FIFO Buffer Between Stages:
```python
InterconnectSpec(
    src_pe="lsu", dst_pe="l1_dcache",
    signals=[...],
    flow_type="fifo",
    queue=QueueSpec(depth=8, almost_full_threshold=6,
                    flow_control="valid_ready"),
)
```

**Multi-Instance PE** (GPGPU Per-Warp/Per-SM):
```python
warp_sched_multi = ProcessingElement(
    name="warp_scheduler", pe_type="warp_scheduler",
    num_instances=8,                  # Generates warp_scheduler[0]..[7]
    instance_id_template="i",
    ...
)
```

#### CHECKPOINT 0

Agent **must stop** here and present the architecture definition report to the human. Human reviews PE list, ports, interconnect topology, and PPA targets, then **approves** or **requests changes**.

---

### Phase 1: Architecture Simulation

**Trigger**: Human approved ArchDefinition at Checkpoint 0.

**Framework task**: Run cycle-accurate simulation via `ArchSimulator`.

```python
from rtlgen import ArchSimulator

sim = ArchSimulator(arch)
results = sim.run(num_cycles=100, init_inputs={"rst_n": 1})
report = sim.run_with_workload(
    workload=[0x00000013, 0x00100093, 0x00300113, ...],
    max_cycles=10000
)
```

**Agent output**: Performance analysis report with IPC, stall cycles, per-PE metrics, bottleneck analysis, and recommendations.

#### CHECKPOINT 1

Human reviews IPC and bottlenecks, then **approves** or **requests architecture changes**.

---

### Phase 2: AgentPackage Generation

**Trigger**: Human approved simulation report at Checkpoint 1.

**Framework task**: Generate `AgentPackage` for each PE via `ArchSkeletonGenerator`.

```python
from rtlgen import ArchSkeletonGenerator

gen = ArchSkeletonGenerator()
packages = gen.generate_all(arch)

ifu_pkg = packages["IFU"]
```

Each `AgentPackage` contains:

| Field | Type | Purpose |
|-------|------|---------|
| `pe` | ProcessingElement | The architecture definition of this module |
| `behavioral_reference` | Callable | Runnable cycle-accurate behavior model (golden reference) |
| `dsl_skeleton` | Module | DSL Module with ports + state variables declared, logic = TODO |
| `golden_tests` | List[dict] | 100+ test vectors with {inputs → expected_outputs} |
| `performance_targets` | dict | {max_latency, min_throughput, target_freq, ...} |
| `interconnect_interface` | dict | {upstream: [...], downstream: [...]} — signal connections |
| `implementation_steps` | List[str] | Incremental TODO steps for RTL implementation |
| `generate_loops` | List[GenerateLoopPattern] | Replication patterns for per-warp/per-SM instantiation |
| `submodule_decomposition` | dict | Hierarchical PE sub-modules and internal connections |

#### CHECKPOINT 2

Human reviews `implementation_steps` for key modules, then **approves** or **modifies steps**.

---

### Phase 3: DSL Implementation

**Trigger**: Human approved AgentPackages at Checkpoint 2.

**Agent task**: For each AgentPackage, follow `implementation_steps`, fill in DSL logic, verify against behavioral reference.

```python
pkg = packages["IFU"]

# Step 1: Study the behavioral reference
ref = pkg.behavioral_reference
ctx = CycleContext(inputs={"rst_n": 1, "pc": 0x1000})

# Step 2: Fill in DSL logic (agent implements each step)
# Step 3: Verify against reference
# Step 4: Run golden tests
```

**Coverage requirement**: ≥95% state/branch/input coverage per module.

**How correctness is guaranteed**:
1. **Behavior model is the spec**: The behavior function IS the golden reference
2. **Golden tests from behavior model**: 100+ test vectors generated automatically
3. **Per-step verification**: Each implementation step includes a verification sub-step
4. **Checkpoint 3 human review**: Human reviews the completed DSL

#### CHECKPOINT 3

Human reviews completed DSL modules, flags issues. Agent **must not** proceed without approval.

---

### Phase 4: PPA Optimization

**Trigger**: Human approved DSL at Checkpoint 3.

**Agent task**: Optimize PPA using AST-level analysis + ABC synthesis feedback.

```python
from rtlgen import PPAOptimizer, PPAScore, PPAGoal

optimizer = PPAOptimizer(dut, spec)
result = optimizer.optimize(max_iterations=3)
```

**7-level PPA optimization strategies**:

| Strategy | Level | What It Does |
|----------|-------|-------------|
| PipelineInsertion | AST | Insert registers to break long paths |
| ResourceSharing | AST | Share operators across mutually exclusive paths |
| BitwidthReduction | RTL | Remove redundant width extensions |
| OperatorSelection | AST | Swap adder/multiplier implementations |
| MuxBalancing | RTL | Rebalance large mux trees |
| FSMEncodingSelect | Arch | Select binary/one-hot/gray encoding |
| SynthesisFeedback | Tech | ABC netlist area/delay feedback |

#### CHECKPOINT 4

Human reviews PPA before/after comparison, then **approves** or **requests further optimization**.

---

### Phase 5: Code Generation & Final Verification

**Trigger**: Human approved PPA results at Checkpoint 4.

**Framework + Agent task**: Generate Verilog, run lint, produce documentation bundle.

```python
from rtlgen import VerilogEmitter, VerilogLinter

verilog = VerilogEmitter().emit(dut)
lint_result = VerilogLinter().lint(verilog)
```

**Mandatory**: Verilog comment injection for traceability:
```python
from rtlgen import ModuleDocTemplate, fill_doc_template

doc = ModuleDocTemplate(
    module_name="C910_IFU",
    description="3-issue superscalar instruction fetch unit",
    author="RTLCraft Agent",
    version="1.0",
    parameters={"FETCH_WIDTH": 3, "BTB_ENTRIES": 64},
    interfaces={"ifu_idu": "Stream: instruction bundle to IDU"},
)
fill_doc_template(dut, doc)
```

**Generated output**:
- Verilog files (`*.v`)
- Lint report
- Architecture report
- Verification report
- PPA report
- Test coverage report

#### CHECKPOINT 5

Human approves final output. Design is complete.

---

## Three-Layer Forward Design Methodology

The preceding Spec2RTL workflow is built on a three-layer abstraction methodology that separates concerns across distinct design phases, with mandatory cross-layer verification at each boundary.

### The Problem

Traditional RTL design has no intermediate verification between specification and implementation. A spec says "ALU adds two numbers," the RTL implements it, and you only find bugs at simulation time — or worse, in silicon. As designs grow (a modern CPU core has 50+ sub-modules), the gap between "what it should do" and "what the RTL does" becomes unmanageable.

RTLCraft addresses this by introducing **two intermediate layers** — Functional and Cycle-Level — that serve as verifiable stepping stones from spec to RTL:

```
Spec (natural language / YAML)
    ↓
 Layer 1 — Functional:    Pure functions, no timing
    ↓  (verified against spec)
 Layer 2 — Cycle-Level:   Register-accurate, with timing
    ↓  (verified: L2==L1 via LayerVerifier)
 Layer 3 — DSL:           Synthesizable rtlgen modules
    ↓  (verified: L3==L2 via LayerVerifier)
 Verilog
```

### Layer 1 — Functional Model

**File**: `skills/cpu/functional.py` (8 functions: `ifu_pcgen_functional`, `ifu_bht_functional`, `iu_alu_functional`, `iu_bju_functional`, `rtu_rob_functional`, ...)

**What**: Pure-Python functions with no timing or state. Each function is a mathematical mapping from inputs to outputs.

**Why**: Serves as the golden reference. Before writing any RTL, you write a 10-line Python function that captures exactly what the hardware should compute. This is trivially verifiable against the spec — just call the function and check results.

**How**:

```python
def iu_alu_functional(**kwargs) -> Callable:
    def func(src0: int = 0, src1: int = 0, opcode: int = 0) -> Dict:
        if opcode == 0: return {"result": src0 + src1}
        if opcode == 1: return {"result": src0 - src1}
        if opcode == 2: return {"result": src0 & src1}
        if opcode == 3: return {"result": src0 | src1}
        return {"result": 0}
    return func
```

**Simulation**: Direct function call — `func(src0=5, src1=3, opcode=0)` → `{"result": 8}`.

**Output**: A **Layer 1→2 guide** is auto-generated (via `generate_layer_guide(module, layer=1, ...)`) documenting the interface (ports, widths), state variables (none at L1), and behavioral descriptions. This guide is saved as a `.md` file and serves as the specification for Layer 2.

### Layer 2 — Cycle-Level Model

**File**: `skills/cpu/cycle_level.py` (86 models: `ifu_cycle`, `iu_alu_cycle`, `ibuf_cycle`, `pcgen_cycle`, `bpred_cycle`, `addrgen_cycle`, `lsu_ctrl_cycle`, ...)

**What**: `CycleContext`-based behavior functions that introduce register boundaries and pipeline timing while remaining pure Python — no RTL constructs.

**Why**: RTL bugs most often come from **timing errors** (wrong pipeline stage, missing register, incorrect handshake timing), not from wrong arithmetic. Layer 2 captures the cycle-accurate behavior — exactly when each signal changes — without the complexity of RTL syntax.

**How**: Each model is a function returning a `Callable[[CycleContext], None]`:

```python
def iu_alu_cycle(**kwargs) -> Callable[[CycleContext], None]:
    """Cycle-accurate ALU model (2-stage pipeline)."""
    def behavior(ctx: CycleContext) -> None:
        rst_n = ctx.get_input('rst_n', 1)
        if rst_n == 0:
            ctx.state['pipe'] = 0; return
        src0 = ctx.get_input('src0', 0); src1 = ctx.get_input('src1', 0)
        op = ctx.get_input('opcode', 0)
        if op == 0: result = src0 + src1
        elif op == 1: result = src0 - src1
        elif op == 2: result = src0 & src1
        else: result = 0
        ctx.state['pipe'] = result
        ctx.set_output('result', ctx.state.get('pipe', 0))
    return behavior
```

The `ctx.state` dict represents **hardware registers** — values persist across clock cycles. `ctx.set_output()` drives module outputs.

**Simulation**: L2 models are wrapped as `_beh_func` and run through the same `Simulator` as L3 DSL modules (see `_cycle_to_beh_func` in `rtlgen/forward.py`). This ensures the comparison framework is identical — no simulation artifacts.

```
Simulator          Simulator
   │                   │
 L2 beh_func       L3 DSL Module
   │                   │
   └─────┬─────┬───────┘
         │     │
   L2 result  L3 result
         │     │
   LayerVerifier.compare(L2, L3)
```

**Output**: A **Layer 2→3 guide** is generated with register names, widths, reset values, FSM states, and pipeline timing diagrams.

### Layer 3 — DSL (rtlgen Modules)

**Directory**: `skills/cpu/layer3_dsl/` (77 files: `alu.py`, `ibuf.py`, `pcgen.py`, `rob.py`, `csr.py`, `tage.py`, `ooo_issue.py`, `mmu_tlb.py`, ...)

**What**: Synthesizable rtlgen DSL `Module` subclasses with `Input`/`Output`/`Reg`/`Wire` ports, `@self.comb`/`@self.seq` logic blocks, and `If`/`Elif`/`Else`/`Switch` control flow — directly translatable to Verilog.

**Why**: This is the actual hardware description. Every signal, register, and logic gate is explicitly declared. The DSL is the **single source of truth** that generates Verilog.

**How**:

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
            with Elif(self.op == 3): self.result <<= self.a | self.b
            with Elif(self.op == 4): self.result <<= self.a ^ self.b
            with Elif(self.op == 5): self.result <<= self.a << self.b[5:0]
            with Elif(self.op == 6): self.result <<= self.a >> self.b[5:0]
            with Else(): self.result <<= Const(0, width)
            self.zero <<= (self.result == 0)
```

**Simulation**: `Simulator(inst, use_xz=False)` — 94 out of 96 Layer 3 classes PASS cross-layer verification.

**Output**: `VerilogEmitter().emit(module)` → 166 `.v` files (~17,700 lines total) in `generated_skill_ppa/cpu/hand_generated/`.

### Cross-Layer Verification

**File**: `rtlgen/forward.py` — `LayerVerifier`

Cross-layer verification is **mandatory**. No module is accepted until L1 == L2 == L3 under identical test vectors:

```python
from rtlgen.forward import LayerVerifier

ok = LayerVerifier.verify(
    module_name="iu_alu",
    l1_func=iu_alu_functional(),
    l2_func=iu_alu_cycle(),
    l3_class=ALU,
    test_cases=[
        {"inputs": {"src0": 5, "src1": 3, "opcode": 0},
         "expect": {"result": 8}},
        {"inputs": {"src0": 10, "src1": 4, "opcode": 1},
         "expect": {"result": 6}},
    ],
)
```

If any layer disagrees:
```
AssertionError: L1!=L2!=L3 cross-layer mismatch!
Design must be consistent across all layers.
Fix Layer 1, 2, or 3 to match.
```

This prevents the common scenario where the RTL "implements" something different from what the spec intended.

### Concrete Example: ALU Through All Three Layers

Here is the complete path from function to Verilog for a 64-bit ALU:

```
Spec: "ALU supports ADD, SUB, AND, OR, XOR, SLL, SRL with zero flag"
```

**Step 1 — Layer 1 (Functional)**:
```python
def alu_l1(**kw):
    ops = {0: kw['src0']+kw['src1'], 1: kw['src0']-kw['src1'],
           2: kw['src0']&kw['src1'], 3: kw['src0']|kw['src1'],
           4: kw['src0']^kw['src1']}
    return {'result': ops.get(kw['opcode'], kw['src0']+kw['src1']),
            'zero': ops.get(kw['opcode'], kw['src0']+kw['src1']) == 0}
```

**Step 2 — Layer 1→2 guide generated** (ports: `src0[64], src1[64], opcode[4]` → `result[64], zero[1]`).

**Step 3 — Layer 2 (Cycle-Level)**: Add pipeline register for timing.
```python
def alu_cycle(**kwargs):
    def behavior(ctx):
        if ctx.get_input('rst_n', 1) == 0:
            ctx.state['pipe'] = 0; return
        src0 = ctx.get_input('src0', 0); src1 = ctx.get_input('src1', 0)
        op = ctx.get_input('op', 0)
        if op == 0: val = src0 + src1
        elif op == 1: val = src0 - src1
        elif op == 2: val = src0 & src1
        elif op == 3: val = src0 | src1
        elif op == 4: val = src0 ^ src1
        else: val = 0
        ctx.state['pipe'] = val
        ctx.set_output('result', ctx.state.get('pipe', 0))
        ctx.set_output('zero', ctx.state.get('pipe', 0) == 0)
    return behavior
```

**Step 4 — Layer 2→3 guide generated** (registers: `pipe[64]`, pipeline stages: 2).

**Step 5 — Layer 3 (DSL)**:
```python
class ALU(Module):
    def __init__(self, width=64):
        super().__init__("alu")
        self.clk = Input(1, "clk"); self.rst_n = Input(1, "rst_n")
        self.op = Input(4, "op")
        self.a = Input(width, "a"); self.b = Input(width, "b")
        self.result = Output(width, "result")
        self.zero = Output(1, "zero")
        r_pipe = Reg(width, "r_pipe")

        with self.seq(self.clk, ~self.rst_n):
            with If(~self.rst_n):
                r_pipe <<= 0
            with Else():
                with If(self.op == 0): r_pipe <<= self.a + self.b
                with Elif(self.op == 1): r_pipe <<= self.a - self.b
                with Elif(self.op == 2): r_pipe <<= self.a & self.b
                with Elif(self.op == 3): r_pipe <<= self.a | self.b
                with Elif(self.op == 4): r_pipe <<= self.a ^ self.b
                with Else(): r_pipe <<= 0

        with self.comb:
            self.result <<= r_pipe
            self.zero <<= (r_pipe == 0)
```

**Step 6 — Cross-Layer Verification**:
```python
LayerVerifier.verify('alu', alu_l1, ALU,
    test_cases=[...], l2_func=alu_cycle())
# ✓ alu: L1==L2==L3 consistent
```

**Step 7 — Verilog Generation**:
```python
from rtlgen import VerilogEmitter
v = VerilogEmitter().emit(ALU())
# → 100+ lines of synthesizable Verilog
# → generated_skill_ppa/cpu/hand_generated/alu_ALU.v
```

### Verification Philosophy

| Layer | What It Verifies | How | Failure Mode |
|-------|------------------|-----|--------------|
| L1 | Functional correctness | `assert func(input) == expected_output` | Wrong algorithm |
| L2 | Timing correctness | `assert L2_output == L1_output` (same inputs, same values, after N cycles) | Wrong pipeline depth, missing register |
| L3 | RTL correctness | `assert L3_output == L2_output` (same inputs, same timing) | Wrong DSL syntax, wrong signal wiring |

The key insight: **each layer adds exactly one new concern**. L1 adds function. L2 adds time. L3 adds hardware syntax. If verification fails at L2, the bug is in timing, not arithmetic. If it fails at L3, the bug is in RTL syntax or wiring, not timing. This makes debugging linear and predictable.

---

## Cross-Layer Constraint & Intent Framework

### Motivation

In a production Spec2RTL flow, requirements are not just test vectors: they are **constraints** and **verification intents** that must hold across all representation layers. A power budget defined at specification time must still be satisfied after synthesis; a division-by-zero rule must be traceable from the ISS golden model down to the generated UVM sequence.

The Cross-Layer Constraint & Intent Framework makes these requirements first-class IR artifacts. It provides:

- First-class `IRConstraint` objects attached to any `IREntity` (`Module`, `Signal`, etc.).
- Bidirectional propagation: forward refinement (SpecIR → Verilog) and backward validation (Verilog → SpecIR).
- Structured feedback (`ConstraintFeedback`) when lower layers cannot meet an upper-layer constraint.
- A standardized `DesignScaffold` loop: propose → propagate → generate → validate → resolve → commit.
- Human/AI ownership tracking on every constraint and decision.

### Core Abstractions

```python
from rtlgen import (
    IRConstraint, FunctionalConstraint, PerformanceConstraint,
    PowerConstraint, TimingConstraint, VerificationIntent,
    ConstraintPropagator, ConstraintFeedback, DesignGate,
    DesignDecision, DesignScaffold, IREntity, LayerEmitter,
)
```

| Class | Purpose |
|-------|---------|
| `IRConstraint` | Base constraint object: uid, name, category, layer, expr, target, owner, derived_from. |
| `FunctionalConstraint` / `PerformanceConstraint` / `PowerConstraint` / `TimingConstraint` | Typed subclasses. |
| `VerificationIntent` | A constraint that materializes as a testbench artifact (UVM sequence, SVA, cocotb test). |
| `IREntity` | Mixin attached to `Module` and `Signal`; stores constraints. |
| `ConstraintPropagator` | Registers forward/backward transforms between named layers. |
| `ConstraintFeedback` | Issue object with severity (INFO/WARNING/VIOLATION/BLOCKER) and suggested resolutions. |
| `DesignGate` | Checkpoint between two layers; can emit feedback and stop the flow. |
| `DesignDecision` | Records an architecture decision with rationale, alternatives, and impacted constraints. |
| `LayerEmitter` | Generates per-layer artifacts from constraints. |
| `DesignScaffold` | Standard agent loop with compliance checklist. |

### Forward Propagation

Forward propagation refines an abstract constraint into progressively more concrete constraints:

```
SpecIR → BehaviorIR → CycleIR → ArchitectureIR → StructuralIR → DSL → Verilog
```

Example: a SpecIR rule `DIV by zero -> -1` becomes a BehaviorIR ISS test, an ArchitectureIR invariant on `div_result`, a StructuralIR monitor, and finally a Verilog UVM sequence.

Register a transform:

```python
propagator = ConstraintPropagator()
propagator.register_forward("SpecIR", "BehaviorIR", my_transform)
```

### Backward Validation & Feedback

Backward validation checks whether the implementation can satisfy the original constraints. When it cannot, the framework emits structured feedback instead of silently producing wrong RTL.

```python
propagator.register_backward("SpecIR", "Verilog", check_power_feasibility)
```

If the check returns a `ConstraintFeedback` with severity `BLOCKER`, the `DesignScaffold` stops and requires resolution.

### Design Scaffold

The `DesignScaffold` enforces a repeatable agent workflow:

```python
scaffold = DesignScaffold(propagator, emitter, layers=...
scaffold.register_entity(my_module)
scaffold.register_gate(power_gate)
scaffold.record_decision(decision)
ok, feedback = scaffold.run(resolver=my_resolver)
checklist = scaffold.compliance_checklist()
```

Compliance items include: has entities, has constraints, has decisions, forward propagated, artifacts generated, no unresolved blockers.

### Usage Example

```python
from rtlgen import (
    Module, FunctionalConstraint, PowerConstraint,
    ConstraintPropagator, DesignScaffold, LayerEmitter,
)

class MyEmitter(LayerEmitter):
    def emit(self, entity, layer):
        # Return {filename: content} for the given layer
        return {}

propagator = ConstraintPropagator()
# ... register transforms ...

m = Module("core")
m.add_constraint(FunctionalConstraint(
    uid="REQ-001", name="safe_div", layer="SpecIR",
    expr="DIV by zero returns -1", target="core",
))

scaffold = DesignScaffold(propagator, MyEmitter())
scaffold.register_entity(m)
ok, feedback = scaffold.run()
```

See `earphone/design_earphone.py` for a complete end-to-end example using the Earphone SoC.

---

## Skills Library

### Overview

The framework uses a two-layer architecture:

```
rtlgen/                    ← BASE FRAMEWORK (abstractions only)
├── core.py                Module, Signal, Input/Output/Wire/Reg
├── logic.py               If/Else/Switch/When/Mux/Cat
├── sim.py                 Simulator
├── codegen.py             VerilogEmitter
├── lint.py                VerilogLinter
├── pipeline.py            Handshake, Pipeline
├── protocols.py           Bundle, AXI4, APB, etc.
├── arch_def.py            ProcessingElement, ArchDefinition, ModelProvider
├── arch_sim.py            ArchSimulator (abstract engine)
├── arch_skel.py           ArchSkeletonGenerator (skeleton templates)
├── behaviors.py           Base template registry + generic templates
├── lib.py                 FSM, SyncFIFO, Arbiter (universal components)
├── ram.py                 SRAM primitives
└── mem_timing.py          DDR3Timing, ns_to_cycles

skills/                    ← DOMAIN EXTENSIONS (implementations)
├── cpu/                   C910 RISC-V superscalar OoO core
├── dsp/                   DSP suite (signed multipliers, I2S, DDS, CIC)
├── fft/                   Radix-2^2 SDF FFT accelerator
├── gpgpu/                 Ventus GPGPU compute cluster
├── image/isp/             Infinite-ISP v1.1 image signal processor
├── npu/                   Neural Processing Unit
├── noc/                   Mesh Network-on-Chip
├── codec/video/           xk265 H.265/HEVC CTU-level encoder
├── codec/ldpc/            WiMax 802.16e LDPC decoder
├── mem/cam/               Content Addressable Memory
├── mem/ddr3/              DDR3 memory controller
└── interfaces/            Protocol interfaces (AXI, SPI, UART, BTLE, ...)
```

### TemplateRegistry

```python
from rtlgen import TemplateRegistry

# Check available templates
TemplateRegistry.list()
# → ['fifo', 'datapath', 'axi_handshake', 'ifu', 'alu', ...]

# Get a template by name
tpl = TemplateRegistry.get("memory_controller")

# Skills register their templates at import time:
# from skills.cpu.behaviors import *  # auto-registers ifu, alu, etc.
```

### DSL Module Inventory

The `skills/` directory contains a library of **192 DSL Module classes** across **19 `dsl_modules.py` files**. Each module is a complete RTL definition with Input/Output/Reg/Wire port declarations, `seq`/`comb` behavioral logic, and `instantiate` structural hierarchy calls.

| Domain | Skill Path | Modules | Key Parameters |
|--------|-----------|---------|---------------|
| CPU | `skills/cpu/dsl_modules.py` | 7 | PA_WIDTH=40, VA_WIDTH=39, DATA_WIDTH=64 |
| DSP | `skills/dsp/dsl_modules.py` | 12 | Signed multipliers, I2S, DDS, CIC |
| FFT | `skills/fft/dsl_modules.py` | 7 | Radix-2^2 SDF |
| GPGPU | `skills/gpgpu/dsl_modules.py` | 24 | NUM_SM=2, NUM_WARP=8 |
| Image | `skills/image/isp/dsl_modules.py` | 23 | RAW_W=12, MAC_W=22 |
| NPU | `skills/npu/dsl_modules.py` | 11 | NTILE=7, NDPE=40, EW=8, ACCW=32 |
| NoC | `skills/noc/dsl_modules.py` | 15 | FLIT_WIDTH=64, MESH_SIZE=8 |
| Codec/Video | `skills/codec/video/dsl_modules.py` | 38 | LCU_SIZE=64, IME_COST_WIDTH=28 |
| Codec/LDPC | `skills/codec/ldpc/dsl_modules.py` | 6 | N=24, M=12, prec=4 |
| Mem/CAM | `skills/mem/cam/dsl_modules.py` | 5 | DATA_WIDTH=64, ADDR_WIDTH=5 |
| Mem/DDR3 | `skills/mem/ddr3/dsl_modules.py` | 4 | DFI sequencer, timing controller |
| I/F BTLE | `skills/interfaces/btle/dsl_modules.py` | 15 | CRC-24, GFSK, whitening |
| I/F SPI | `skills/interfaces/spi/dsl_modules.py` | 11 | CPOL/CPHA, Master/Slave |
| I/F UART | `skills/interfaces/uart/dsl_modules.py` | 3 | AXI-Stream TX/RX |
| I/F Wishbone | `skills/interfaces/wishbone/dsl_modules.py` | 2 | Reg slice, MUX-2 |
| I/F AXI-S | `skills/interfaces/axis/dsl_modules.py` | 3 | Register, adapter, broadcast |
| I/F AXI | `skills/interfaces/axi/dsl_modules.py` | 2 | DP RAM, AXIL RAM |
| I/F I2C | `skills/interfaces/i2c/dsl_modules.py` | 1 | 7-bit address slave |
| I/F PCIe | `skills/interfaces/pcie/dsl_modules.py` | 3 | Pulse merge, FC counter |

**Usage:**
```python
# Direct import from dsl_modules
from skills.codec.video.dsl_modules import EncCtrl, ImeTop, FetchRefLuma

# Or via __init__.py (where available)
from skills.dsp import DSP_MULT, CIC_DECIMATOR
from skills.interfaces.uart import UART_TX, UART_RX

# Instantiate and emit Verilog
from rtlgen import VerilogEmitter
m = EncCtrl()
verilog = VerilogEmitter().emit(m)
```

All modules use `ModuleDocTemplate` + `fill_doc_template` for Verilog comment injection, and reference constants are included at the top of each `dsl_modules.py`.

### Per-Domain Skill Details

#### CPU — `skills/cpu/`

T-Head C910 RV64IMAFDC superscalar out-of-order core:
- **dsl_modules.py**: 7 DSL Module classes — `C910IFU`, `C910IDU`, `C910IU`, `C910LSU`, `C910RTU`, `C910PRegFile`, `C910Core`
- **behaviors.py**: 8 behavior templates — `ifu`, `idu`, `alu`, `lsu`, `rob`, `regfile`, `bpu`, `issue_queue`
- **models.py**: `RV32ISS`, `RV32State`, `CPUModel`
- **arch_templates.py**: `Embedded`, `InOrder`, `OutOfOrder`, `MultiCore` templates
- **skeleton_templates.py**: 9 PE type step lists
- **design_flow.py**: Full Spec2RTL flow script
- **design_wizard.py**: Interactive design wizard

#### DSP — `skills/dsp/`

DSP suite (signed multipliers, I2S, DDS, CIC):
- **dsl_modules.py**: 12 classes — `DSP_MULT`, `IQ_JOIN`, `IQ_SPLIT`, `I2S_CTRL`, `PHASE_ACCUMULATOR`, `DSP_IQ_MULT`, `I2S_RX`, `I2S_TX`, `SINE_DDS_LUT`, `SINE_DDS`, `CIC_DECIMATOR`, `CIC_INTERPOLATOR`
- **models.py**: 12 golden reference models
- **behaviors.py**: 12 behavior templates
- **arch_templates.py**: `build_dsp_arch()`, `DSP_SuiteModel`
- **skeleton_templates.py**: 12 PE type step lists

#### FFT — `skills/fft/`

Radix-2² SDF FFT accelerator:
- **dsl_modules.py**: 7 classes — `FFTButterfly`, `FFTDelayBuffer`, `FFTMultiply`, `FFTTwiddle`, `FFTSdfUnit`, `FFTSdfUnit2`, `FFTController`
- **models.py**: 7 golden reference models
- **behaviors.py**: 7 behavior templates
- **arch_templates.py**: `build_fft_arch()`, `FFTSuiteModel`
- **skeleton_templates.py**: 7 PE type step lists

#### GPGPU — `skills/gpgpu/`

Ventus GPGPU compute cluster:
- **dsl_modules.py**: 24 classes — `WarpScheduler`, `DecodeUnit`, `Scoreboard`, `IBuffer`, `IBuffer2Issue`, `Issue`, `OperandCollector`, `SIMTStack`, `vALU`, `sALU`, `LSU`, `MUL`, `SFU`, `TC`, `vFPU`, `Writeback`, `InstructionCache`, `L1DCache`, `SharedMemory`, `ClusterToL2Arb`, `L2Distribute`, `CTAScheduler`, `SMWrapper`, `GPGPUTop`
- **behaviors.py**: `cta_scheduler_template`, `warp_scheduler_template`
- **models.py**: `GPUThread`, `GPUWarp`, `GPUState`, `GPGPUModel`
- **arch_templates.py**: `BasicGpuTemplate`, `ComputeClusterTemplate`, `StreamProcessorTemplate`
- **skeleton_templates.py**: 8 PE type step lists

#### Image/ISP — `skills/image/isp/`

Infinite-ISP v1.1 image signal processor:
- **dsl_modules.py**: 23 classes — `ISPAXIStreamIn`, `ISPCrop`, `ISPDPC`, `ISPBLC`, `ISPOECF`, `ISPDG`, `ISPLSC`, `ISPBNR`, `ISPWB`, `ISPAWBStats`, `ISPDemosaic`, `ISPCCM`, `ISPGamma`, `ISPAEStats`, `ISPCSC`, `ISPLDCI`, `ISPSharpen`, `ISPNR2D`, `ISPScale`, `ISPYUV`, `ISPAXIStreamOut`, `ISPAPBRegs`, `ISPController`
- **models.py**: `ISPModel` golden simulator
- **behaviors.py**: 22 behavior templates
- **arch_templates.py**: `build_isp_arch()`, `ISP_Model`
- **skeleton_templates.py**: 22 PE type step lists

#### NPU — `skills/npu/`

Neural Processing Unit:
- **dsl_modules.py**: 11 classes — `TopScheduler`, `GenericScheduler`, `MVUScheduler`, `EVRFScheduler`, `MFUScheduler`, `LDScheduler`, `MVU`, `MFU`, `EVRF`, `LD`, `NPUTop`
- **behaviors.py**: Generic `scheduler_template` + factory wrappers (14 templates)
- **models.py**: `MACArrayModel`, `NPUModel`, activation functions
- **arch_templates.py**: `NpuArchParams`, `Basic/DualPipeline/MultiTile` templates
- **skeleton_templates.py**: 6 PE type step lists
- **design_flow.py**: Full Spec2RTL Phase 0-5 flow
- **design_wizard.py**: Interactive design wizard with auto-classification

#### NoC — `skills/noc/`

Mesh Network-on-Chip:
- **dsl_modules.py**: 15 classes — `Buffer`, `Counter`, `RouteFunc`, `CrossBar`, `ST`, `OutEnGen`, `SelectGen`, `SetAlloc`, `STControler`, `VCAlloc`, `InputUnit`, `OutputUnit`, `Router`, `ProcessNode`, `Network`
- **models.py**: `FlitState`, `RouterState`, `RouterModel`, `NoCModel`
- **behaviors.py**: 14 behavior templates
- **arch_templates.py**: `build_noc_arch()`, `NoC_Model`
- **skeleton_templates.py**: 14 PE type step lists

#### Codec/Video — `skills/codec/video/`

xk265 H.265/HEVC CTU-level encoder:
- **dsl_modules.py**: 38 classes — `EncCtrl`, `PreiTop`, `PosiTop`, `ImeTop`, `FmeTop`, `RecTop`, `DbsaoTop`, `CabacTop`, `FetchTop`, `EncCore`, `Xk265Top`, 8 IME submodules, 6 POSI submodules, 4 REC submodules, 3 DBSAO submodules, 3 CABAC submodules, 3 FETCH submodules
- **models.py**: 38 cycle-accurate Python simulators
- **behaviors.py**: 9 pipeline stage behavior templates
- **arch_templates.py**: `CodecArchParams`, `Baseline/HighPerf/LowPower` templates
- **skeleton_templates.py**: 12 PE type step lists

#### Codec/LDPC — `skills/codec/ldpc/`

WiMax 802.16e LDPC decoder (Min-Sum):
- **dsl_modules.py**: 6 classes — `QuantizedAdder`, `QuantizedSubber`, `Comparator`, `CheckNode`, `VarNode`, `LDPC_Decoder`
- **models.py**: `CheckNode_Model`, `VarNode_Model`, `LDPCDecoder_Model`
- **behaviors.py**: 6 behavior templates
- **arch_templates.py**: `build_ldpc_arch()`, `build_ldpc_params()`

#### Mem/CAM — `skills/mem/cam/`

Content Addressable Memory:
- **dsl_modules.py**: 5 classes — `PriorityEncoder`, `RamDP`, `CamSRL`, `CamBRAM`, `CAM`
- **models.py**: `CAMModel`
- **arch_templates.py**: `build_cam_arch()`, `CAM_Model`

#### Mem/DDR3 — `skills/mem/ddr3/`

DDR3 memory controller:
- **dsl_modules.py**: 4 classes — `DDR3FIFO`, `DDR3DFISeq`, `DDR3Core`, `DDR3Controller`
- **models.py**: `DDR3CoreModel`, `DDR3DFISeqModel`, `DDR3Model`
- **behaviors.py**: `memory_controller_template`, `dfi_sequencer_template`
- **arch_templates.py**: `build_ddr3_arch()`, `DDR3_Model`

#### Interfaces

| Protocol | Path | Modules | Description |
|----------|------|---------|-------------|
| BTLE | `skills/interfaces/btle/` | 15 | Bluetooth Low Energy PHY — CRC-24, GFSK, whitening |
| SPI | `skills/interfaces/spi/` | 11 | APB-based SPI controller (Master/Slave) — CPOL/CPHA |
| UART | `skills/interfaces/uart/` | 3 | AXI-Stream UART TX/RX |
| Wishbone | `skills/interfaces/wishbone/` | 2 | Reg slice, MUX-2 |
| AXI-Stream | `skills/interfaces/axis/` | 3 | Register, adapter, broadcast |
| AXI | `skills/interfaces/axi/` | 2 | DP RAM, AXIL RAM |
| I2C | `skills/interfaces/i2c/` | 1 | 7-bit address slave |
| PCIe | `skills/interfaces/pcie/` | 3 | Pulse merge, FC counter |
| Ethernet | `skills/interfaces/ethernet/` | — | PTP timestamp extraction (arch templates only) |
| AXI-Lite | `skills/interfaces/axi_lite/` | — | Shares AXIL_RAM in `axi/dsl_modules.py` |

### Adding a New Domain Skill

1. Create `skills/<domain>/behaviors.py` with behavior template functions
2. Register: `TemplateRegistry.register("<pe_type>", my_template)`
3. Create `skills/<domain>/skeleton_templates.py` with implementation step lists
4. Register: `register_<domain>_skeleton_steps(arch_skel._TEMPLATE_STEPS)`
5. Create `skills/<domain>/dsl_modules.py` with DSL Module class definitions
6. Export DSL modules in `skills/<domain>/__init__.py` (if no circular import risk)

---

## Architecture Framework Reference

### ProcessingElement

```python
ProcessingElement(
    name="IFU",
    pe_type="ifu",                    # For template lookup
    pipeline_stage="fetch",
    issue_width=3,
    latency=5,
    inputs=[PortDesc("clk", "input", 1), ...],
    outputs=[PortDesc("ifu_idu_vld", "output", 1), ...],
    state=[StateDesc("pc", "int", "PC", rtl_type="reg", rtl_width=40), ...],
    behavior=ifu_template(...),       # Pre-built behavior template
    can_stall=True,
    num_instances=1,                  # For GPGPU: generate for i=0..N-1
    instance_id_template="i",
)
```

### CycleContext

```python
def ifu_behavior(ctx: CycleContext):
    if ctx.inputs["rst_n"] == 0:
        ctx.state["pc"] = 0
        return
    # ... fetch logic ...
    ctx.retire(1)  # Increment retirement counter for IPC
```

### ModelProvider — 5 Domain Types

| Type | Class | Use Case |
|------|-------|----------|
| ISA | `ISA_Model(iss=RV32ISS())` | CPUs with instruction sets |
| Protocol | `Protocol_Model(...)` | Bus controllers, memory interfaces |
| Stream | `Stream_Model(...)` | Video/image pipelines |
| Algorithm | `Algorithm_Model(...)` | LDPC, FFT, crypto |
| Memory | `MemoryModel(...)` | DDR3, SRAM controllers |

### ArchDefinition → BehavioralSpec Bridge

```python
arch = ArchDefinition(...)

# Convert to BehavioralSpec for decomposition framework
from rtlgen.decomposition import BehavioralSpec
spec = BehavioralSpec.from_arch_definition(arch)
```

---

## Configuration System

XiangShan-style parameter system for architecture exploration:

```python
from rtlgen import ConfigSpec, Config, PEParams, PresetSpecs

# Flat parameter specification
spec = ConfigSpec({
    "FetchWidth": 3,
    "BTBEntries": 64,
    "BHTEntries": 512,
    "RASEntries": 16,
})

# Hierarchical config with parent inheritance
config = Config(
    name="C910Config",
    parent=PresetSpecs.rv64_core(),  # Inherit defaults
    overrides={
        "FetchWidth": 3,
        "BTBEntries": 64,
    },
)

# Fluent builder
params = PEParams().with_issue_width(3).with_btb(64).with_bht(512)
```

**PresetSpecs**:
- `rv32_core`: 32-bit embedded core
- `rv64_core`: 64-bit application core
- `high_perf_core`: wide-issue, large ROB
- `embedded_core`: small area, low power

---

## Technology Node Library

```python
from rtlgen import TechNode

# Available nodes: 180nm, 130nm, 90nm, 65nm, 45nm, 28nm, 22nm, 14nm, 10nm, 7nm, 5nm
node = TechNode("7nm")

print(node.gate_delay)       # ~7.5 ps per FO4 inverter
print(node.cell_area)        # ~0.03 um² per NAND2
print(node.wire_delay_per_um) # ~0.2 ps/um
print(node.max_freq)         # ~3.5 GHz
print(node.pipeline_recommendation)  # "3-4 stages for 1GHz"
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `rtlgen/arch_def.py` | `ProcessingElement`, `StateDesc`, `PortDesc`, `CycleContext`, `InterconnectSpec`, `HandshakeSpec`, `QueueSpec`, `ArchDefinition`, `AgentPackage`, `ModelProvider`, `ISA_Model`, `Protocol_Model`, `Stream_Model`, `Algorithm_Model`, `MemoryModel`, `MemoryControllerSpec`, `CoverageTracker`, `FuConfig`, `ExuConfig`, `SchedulerConfig` |
| `rtlgen/arch_sim.py` | `ArchSimulator` — cycle-accurate architecture simulation engine. Features: `_HandshakeState`, `_FifoQueue`, `_expand_instances()`, `set_scoreboard()`, IPC from `total_retired / total_cycles`. **CRITICAL**: `run()` requires `init_inputs={"rst_n": 1}`. |
| `rtlgen/arch_skel.py` | `ArchSkeletonGenerator` — generates AgentPackage per PE with DSL skeleton, golden tests, implementation steps. **`GenerateLoopPattern`** for per-warp/per-SM generate loops. |
| `rtlgen/decomposition.py` | `BehavioralSpec`, `StrategySpec`, `ConnectionSpec`, `DecompositionResult`, `SystemSimulator`, gem5-style hierarchy specs, `ModuleDoc`, `TopLevelDoc`, `PPAViolation` |
| `rtlgen/core.py` | `Module`, `Signal`, `Input/Output/Wire/Reg`, `BehavioralModule`, `BlackBoxModule`, `BehavioralRTLPair`, `ModelVersion`, `ModelRegistry`, `SourceLoc`, `IntentContext` |
| `rtlgen/sim.py` | `Simulator` — single-module RTL simulation |
| `rtlgen/sim_jit.py` | `JITSimulator` — 50–500× acceleration with transparent fallback |
| `rtlgen/ppa_optimizer.py` | `PPAOptimizer`, `OptimizationGuide`, `PPAScore`, `PPAGoal` |
| `rtlgen/codegen.py` | `VerilogEmitter`, `EmitProfile`, `ModuleDocTemplate`, `fill_doc_template` |
| `rtlgen/lint.py` | `VerilogLinter`, `LintIssue`, `LintResult` |
| `rtlgen/spec_ir.py` | `SpecIR`, `BehaviorIR`, `CycleIR`, `StructuralIR`, `ArchitectureIR`, `VerificationPlanIR`, `PortSpec`, `FunctionSpec`, `PPASpec`, `TimingSpec`, `VerificationSpec` |
| `rtlgen/dsl_gen.py` | `DSLGenerator` — SpecIR + ArchitectureIR → DSL Module, including deterministic hierarchical wrappers |
| `rtlgen/dsl_sim.py` | `DSLSimValidator` — static completeness + simulation-driven DSL validation |
| `rtlgen/verifier.py` | `Verifier` — syntax/lint/smoke/behavior verification levels with repair context support |
| `rtlgen/processor_models.py` | `RV32ISS`, `GPGPUModel`, `CPUModel`, `BehavioralModelFactory` |
| `rtlgen/iss_base.py` | `ISSBase` — abstract ISS interface (any ISA) |
| `rtlgen/behaviors.py` | Pre-built behavior templates: `ifu`, `idu`, `alu`, `lsu`, `rob`, `regfile`, `datapath`, `fifo`, `axi_handshake`, `bpu`, `issue_queue`, `pipeline_connect`, `circular_queue`, `writeback_arbiter` |
| `rtlgen/tech_library.py` | `TechNode` — process node characterization (180nm–5nm) |
| `rtlgen/mem_timing.py` | `DDR3Timing` (JEDEC timing database), `ns_to_cycles()` |
| `rtlgen/params.py` | XiangShan-style config: `ConfigSpec`, `Config`, `PEParams`, `PresetSpecs` |

---

## License Notice

The RTLCraft framework code (Python DSL, AST, simulators, and generators) is licensed under a custom MIT License. Personal use and research are permitted. **Commercial use requires prior authorization.** For commercial licensing, please contact the author and Fudan University (State Key Laboratory of Integrated Chips and Systems): efouth@gmail.com

The `skills/` directory contains Python DSL modules that are re-implementations inspired by third-party open-source Verilog reference designs. **The copyright of the original reference RTL designs belongs to their respective original authors.** Users must comply with the license terms of each original project. See [skills/README.md](skills/README.md) for full attribution.

See [LICENSE](LICENSE) for details.
