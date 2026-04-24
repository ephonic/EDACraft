# rtlgen — Python API for Verilog RTL Generation

> An object-oriented, decorator-driven Python API for describing synthesizable Verilog / SystemVerilog digital logic.
> This is not a black-box generator, but a **white-box framework** — enabling Code / LLMs to directly understand, manipulate, and evolve the RTL abstract syntax tree (AST).

---

## Design Philosophy

### White-Box Tooling: Let Code Do Reasoning

Traditional HLS (High-Level Synthesis) tools are **black boxes**: you write C++/Python, they spit out Verilog, and you have no idea what happened in between. When something breaks, you cannot debug it.

rtlgen takes the opposite approach — it is a **white-box framework**:

- **Fully transparent AST**: Every `Signal`, `Module`, and `Assign` created in Python is an explicit AST node that you can traverse, inspect, modify, and print at any time.
- **Code-readable and Code-writable**: LLMs and developers can not only generate rtlgen code, but also read the structure of existing designs, perform incremental modifications, refactoring, and optimization.
- **Tool-design co-evolution**: The simulator, PPA analyzer, synthesizer, and backend tools all operate on the same AST. Changes at any end instantly propagate to all other ends.

```python
# White-box: you can directly access the module's AST
dut._inputs       # dict of all input ports
dut._comb_blocks  # list of all combinational logic blocks
dut._seq_blocks   # list of all sequential logic blocks
```

### Bidirectional Flow: Verilog ↔ pyRTL

rtlgen supports a **bidirectional workflow**:

- **Forward**: Python DSL → AST → Verilog / SV / UVM / Testbench / Simulation
- **Reverse**: Verilog Repo → Python DSL (via `VerilogImporter`), converting legacy codebases into maintainable Python descriptions in one step

This makes rtlgen a **living tool chain** — capable of both green-field design and brown-field refactoring.

---

## Feature Overview

| Module | Capability | Status |
|--------|-----------|--------|
| `core` + `logic` | Python DSL → AST | ✅ Mature |
| `codegen` | AST → Verilog-2001 / SystemVerilog | ✅ Mature |
| `sim` + `sim_jit` | Python AST interpreter + JIT compiler (~7x speedup) | ✅ Available |
| `uvmgen` + `pyuvmgen` | UVM testbench auto-generation (SV + Python dual backend) | ✅ Available |
| `pyuvm` + `pyuvm_sim` | Native Python UVM framework + simulator driver | ✅ Available |
| `ppa` | AST-based logic depth / gate count / fanout / dead signal analysis | ✅ Available |
| `lint` | Post-generation lint + auto-fix | ✅ Available |
| `blifgen` + `synth` | ABC logic synthesis integration (BLIF → optimized netlist) | ✅ Available |
| `liberty` + `lef` | Standard cell library / physical library parsing & generation | ✅ Available |
| `netlist` + `timing` | Gate-level netlist parsing + static timing analysis | ✅ Available |
| `sizing` + `placement` | Gate sizing optimization + analytical placement | ✅ Available |
| `routing` + `rc` | Global / detailed routing + RC extraction | ✅ Available |
| `rcextract` | Parasitic extraction → RTL feedback engine | ✅ Available |
| `cosim` | Python ↔ iverilog co-simulation | ✅ Available |
| `verilog_import` | Verilog / SV Repo → Python DSL | ✅ Available |
| `cocotbgen` | cocotb test generation | ✅ Available |
| `svagen` | SVA assertion generation | ✅ Available |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB / Wishbone | ✅ Available |
| `lib` | FSM / FIFO / Arbiter / Shifter / LFSR / CRC / Divider | ✅ Available |
| `pipeline` | Pipeline engine (automatic handshake + inter-stage registers) | ✅ Available |
| `ram` | Single-port / dual-port RAM wrappers | ✅ Available |
| `regmodel` | UVM RAL register model generation | ✅ Available |

---

## Installation

### Dependencies

```bash
# Core dependency (required)
pip install pyverilog

# Simulation & JIT (optional)
pip install numpy

# Logic synthesis (requires iverilog + ABC)
brew install iverilog abc    # macOS
apt-get install iverilog abc # Ubuntu

# pyUVM simulation (optional)
pip install cocotb
```

### Using with Code (LLM / Agent)

rtlgen is designed for Code-driven development. Recommended workflow:

1. **Let Code read `pyRTL.md`** — complete API specification
2. **Let Code browse `examples/`** — design patterns from simple counters to complex accelerators
3. **Let Code explore `skills/`** — reusable hardware design module library
4. **Let Code call APIs directly** — generate, simulate, synthesize, evaluate, all in Python

```python
# Code can start like this
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

# Generate Verilog
dut = MyModule()
print(VerilogEmitter().emit(dut))

# Simulate
sim = Simulator(dut)
sim.reset()
for i in range(10):
    sim.step()
    print(f"cycle {i}: data = {sim.get_int('data')}")
```

---

## Core API Design

### 1. Python DSL: Decorators + Context Managers

rtlgen's goal is to describe hardware in the **most Pythonic way** while maintaining **fully synthesizable** semantics.

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

### 2. Simulation Engine: AST Interpreter + JIT Compiler

rtlgen includes two levels of simulation backends:

#### 2.1 AST Interpreter (`Simulator`)

Python-based AST traversal interpreter supporting full rtlgen semantics:

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
- Hierarchical designs automatically `flatten`
- Direct Memory read/write support
- Trace output (table / VCD format)
- Multi-clock domain simulation
- X/Z four-state logic support

#### 2.2 JIT Compiler (`sim_jit`)

Flattens AST into Python lambda arrays to eliminate interpretation overhead:

```bash
# JIT is enabled by default
export RTLGEN_NO_JIT=0
```

| Design | AST Speed | JIT Speed | Speedup |
|--------|-----------|-----------|---------|
| NPU (NeuralAccel) | ~268 cps | ~1897 cps | **7.0x** |
| BOOM (simplified core) | ~151 cps | ~610 cps | **4.0x** |

JIT compiles automatically at `Simulator` initialization, falling back silently to AST interpreter on failure.

#### 2.3 Python ↔ iverilog Co-Simulation (`cosim`)

Execute the same test vectors simultaneously in Python `Simulator` and `iverilog`, comparing outputs cycle-by-cycle to ensure Python simulation matches Verilog semantics.

### 3. UVM / Testbench Generation

rtlgen supports **dual-backend UVM**:

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

### 4. AST-Based PPA Performance Evaluation

No need to wait for synthesis completion — perform rapid PPA analysis at the Python layer based on AST:

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

### 5. Logic Synthesis

rtlgen integrates **ABC** (Berkeley Logic Synthesis and Verification Group):

```python
from rtlgen import BLIFEmitter, ABCSynthesizer

# Generate BLIF
blif = BLIFEmitter().emit(dut)

# Synthesize with ABC
synth = ABCSynthesizer()
result = synth.synthesize(blif, script="resyn2")
print(result.netlist)
```

Supports:
- BLIF netlist generation
- Custom ABC scripts (`resyn`, `resyn2`, `resyn3`, `if`, etc.)
- Gate-level netlist parsing (`netlist` module)
- Standard cell library parsing (Liberty format)
- Static timing analysis (STA)

### 6. Backend Capabilities (Placement → Routing → Signoff)

rtlgen includes a **teaching-grade backend flow**, from netlist to GDSII:

```python
from rtlgen import (
    GateSizer, AnalyticalPlacer,
    GlobalRouter, DetailedRouter,
    FastRCExtractor, TimingAnalyzer
)

# 1. Gate sizing optimization
sizer = GateSizer(liberty_lib)
sized_netlist = sizer.size(netlist, target_delay=1.0)

# 2. Analytical placement (EPlace-style quadratic programming)
placer = AnalyticalPlacer()
placement = placer.place(sized_netlist, core_area=(0, 0, 1000, 1000))

# 3. Global + detailed routing
router = GlobalRouter()
routing = router.route(placement, placement.nets)

# 4. RC extraction
detailed_rc = DetailedRCExtractor(lef, tech_file)
rc_result = detailed_rc.extract(placement, routing)

# 5. Timing feedback → RTL optimization
feedback = RTLFeedbackEngine()
report = feedback.analyze(rc_result, timing=TimingAnalyzer())
# Generates RTL modification suggestions: e.g., insert pipeline stage on critical path
```

**Note**: Backend modules are for educational/research purposes. Accuracy is lower than commercial tools (ICC2/Innovus), but the complete RTL-to-physical flow is demonstrated.

### 7. Verilog → pyRTL Reverse Import

Convert legacy Verilog / SystemVerilog codebases to rtlgen Python DSL:

```python
from rtlgen import VerilogImporter

importer = VerilogImporter("/path/to/verilog/repo")
importer.scan_repo()                          # recursively scan .v / .sv
importer.emit_repo("/output", package_name="imported")
```

**Preprocessing compatibility**: Built-in iverilog macro expansion + SV syntax repair (`for (integer ...)`, `i++`, `'0`, etc.), supporting complete conversion of 44/44 complex EU modules (including `generate-for`, parameterized widths, and submodule instantiation).

---

## Skills Directory

`skills/` is rtlgen's **hardware design reference library**, collecting reusable domain-specific modules and tutorials:

| Directory | Content |
|-----------|---------|
| `fundamentals/` | Standard library (FSM, FIFO, Arbiter), API tutorials |
| `arithmetic/` | Multipliers (Karatsuba-Ofman), SHA3, FP8 ALU |
| `cpu/` | RISC-V cores, BOOM-style OoO CPU, branch predictors |
| `npu/` | Systolic Array, Tensor Core, quantization engines, NeuralAccel top |
| `cryptography/` | Stream ciphers, block ciphers, post-quantum crypto primitives |
| `codec/` | Line codes, entropy coding, compression/decompression |
| `control/` | FSM, counters, scheduling, pipeline control |
| `memory-storage/` | SRAM controllers, Cache, DMA, storage interfaces |
| `video/` | Video codecs, display pipelines, HDMI/DP controllers |
| `image/` | ISP, image filtering, resize/rotate, DCT |
| `gpgpu/` | Shader cores, warp schedulers, memory coalescing |
| `accelerators/` | Domain-specific accelerators (ML inference, signal processing) |
| `verification/` | Debug tools, testbench patterns, formal verification helpers |
| `synthesis/` | ABC integration, timing analysis, area estimation flows |
| `physical-design/` | Floorplanning, placement, routing, DFT, signoff |

Each skill directory contains a `SKILL.md`, Python source files, and test cases.

---

## Project Structure

```
rtlgen/
├── rtlgen/              # Core framework
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
├── examples/            # Example designs (counter to accelerator)
├── tests/               # pytest test suite
├── skills/              # Hardware design reference library
│   ├── fundamentals/
│   ├── arithmetic/
│   ├── cpu/
│   ├── npu/
│   └── ...
├── pyRTL.md             # Complete API specification
└── README.md            # This file (Chinese)
└── README_EN.md         # English version
```

---

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd rtlgen

# 2. Install core dependencies
pip install pyverilog numpy

# 3. Run examples
cd examples
python counter.py
python pipeline_adder.py
python fsm_traffic.py

# 4. Run tests
cd ..
pytest tests/ -v

# 5. Convert a Verilog codebase to Python
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

## Roadmap

- **C++ Simulation Engine**: Boost JIT speedup from ~7x to 50-500x via pybind11 (see `cppengine.md`)
- **CDC Modules**: Gray code counter, full async FIFO implementation
- **TrueDualPortRAM**: Both ports read/write capable
- **CHISEL Export**: AST → FIRRTL backend
- **Formal Verification Integration**: SVA + yosys-smtbmc

---

## License

MIT License
