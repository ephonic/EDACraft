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

### Bidirectional Flow: Verilog ↔ pyRTL

RTLCraft supports a **bidirectional workflow**:

- **Forward**: Python DSL → AST → Verilog / SV / UVM / Testbench / Simulation
- **Reverse**: Verilog Repo → Python DSL (via `VerilogImporter`, requires pyverilog), converting legacy codebases into maintainable Python descriptions

This makes RTLCraft a **living tool chain** — capable of both green-field design and brown-field refactoring.

---

## Feature Overview

| Module | Capability | Status |
|--------|-----------|--------|
| `core` + `logic` | Python DSL → AST (signals, modules, logic control, state machines) | ✅ Mature |
| `codegen` | AST → Verilog-2001 / SystemVerilog (with submodule dedup) | ✅ Mature |
| `lint` | Post-generation lint + auto-fix (7 rules) | ✅ Mature |
| `sim` | Python AST interpreter (4-state logic, multi-clock, VCD export) | ✅ Mature |
| `ppa` | AST-based logic depth / gate count / fanout / dead signal analysis | ✅ Available |
| `blifgen` + `synth` | ABC logic synthesis integration (BLIF → optimized netlist) | ✅ Available |
| `uvmgen` | SV UVM testbench auto-generation (interface / agent / env / test) | ✅ Available |
| `pyuvm` + `pyuvm_sim` | Native Python UVM framework + simulator driver | ✅ Available |
| `pyuvmgen` | Python UVM → SystemVerilog transpiler | ✅ Available |
| `cocotbgen` | cocotb test framework auto-generation | ✅ Available |
| `uvmvip` | APB / AXI4-Lite / AXI4 VIP generation | ✅ Available |
| `regmodel` | UVM RAL register model generation | ✅ Available |
| `pipeline` | Pipeline engine (auto handshake + back-pressure) | ✅ Available |
| `lib` | FSM / FIFO / Arbiter / BarrelShifter / LFSR / CRC / Divider | ✅ Available |
| `protocols` | AXI4 / AXI4-Lite / AXI4-Stream / APB / AHB-Lite / Wishbone | ✅ Available |
| `ram` | Single-port / simple dual-port RAM wrappers | ✅ Available |
| `cosim` | Python ↔ iverilog co-simulation | ✅ Available |
| `verilog_import` | Verilog / SV → Python DSL (requires pyverilog) | ⚠️ Optional |
| `netlist` | Gate-level netlist parsing | ✅ Available |
| `liberty` | Liberty standard cell library parsing & generation | ✅ Available |
| `lef` | LEF physical library parsing & generation | ✅ Available |

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

---

## Skills Directory

`skills/` is RTLCraft's **hardware design reference library**, collecting reusable domain-specific modules and tutorials:

| Directory | Content | Status |
|-----------|---------|--------|
| `fundamentals/` | Standard library (FSM, FIFO, Arbiter), API tutorials | ✅ Available |
| `arithmetic/` | Multipliers (KO-3 recursive tree), SHA3, FP8 ALU | ✅ Available |
| `codec/` | 8b10b encoder/decoder (sequential/combinational) | ✅ Available |
| `control/` | FSM matrix multiplication, traffic-light FSM | ✅ Available |
| `cpu/boom/` | BOOM-style OoO RISC-V core (RV32I) | ✅ Available |
| `cpu/npu/` | NPU (systolic array + tensor core + compiler) | ✅ Available |
| `cryptography/` | ChaCha20 stream cipher | ✅ Available |
| `synthesis/` | ABC synthesis integration tutorial | ✅ Available |
| `verification/` | Debug tools, simulation tutorials | ✅ Available |
| `gpgpu/` | GPGPU core (ALU array + warp scheduler + tensor core) | ✅ Available |
| `memory-storage/` | SRAM / Cache / DMA (planned) | 📋 Reserved |
| `image/` | ISP / image filtering / DCT (planned) | 📋 Reserved |
| `video/` | Video codec / HDMI (planned) | 📋 Reserved |
| `accelerators/` | Domain-specific accelerators (planned) | 📋 Reserved |
| `physical-design/` | Floorplan / placement / routing / DFT (planned) | 📋 Reserved |
| `npu/` | NPU top-level (planned) | 📋 Reserved |

Each skill directory contains a `SKILL.md`, Python source files, and design documentation.

---

## Project Structure

```
RTLCraft/
├── rtlgen/                   # Core framework
│   ├── core.py               # Signal / Module / Parameter / AST
│   ├── logic.py              # If / Else / Switch / ForGen / StateTransition
│   ├── codegen.py            # VerilogEmitter
│   ├── lint.py               # VerilogLinter (7 rules + auto-fix)
│   ├── sim.py                # Simulator (AST interpreter, 4-state logic)
│   ├── cosim.py              # Python ↔ iverilog co-simulation
│   ├── verilog_import.py     # Verilog → Python importer (optional)
│   ├── ppa.py                # PPAAnalyzer
│   ├── blifgen.py            # BLIF generation (bit-level expansion)
│   ├── synth.py              # ABC integration
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
├── skills/                   # Hardware design reference library
│   ├── fundamentals/
│   ├── arithmetic/
│   ├── codec/
│   ├── control/
│   ├── cpu/
│   ├── cryptography/
│   ├── gpgpu/
│   └── ...
├── pyRTL.md                  # Complete API specification
├── README_CN.md              # Chinese version
├── README.md                 # This file (English)
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

# 5. Run skill examples
cd ../../arithmetic/multipliers
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

---

## Roadmap

- **C++ Simulation Engine**: Boost simulation speed 50-500x via pybind11
- **CDC Modules**: Gray code counter, full async FIFO implementation
- **TrueDualPortRAM**: Both ports read/write capable
- **CHISEL Export**: AST → FIRRTL backend
- **Backend Completion**: Gate sizing, global/detailed routing, RC extraction

---

## AI-Driven Automated RTL Generation

RTLCraft supports end-to-end automation with AI coding assistants (Claude Code / Kimi Code):

1. **Spec → Python RTL**: AI generates Python DSL code from natural-language specifications
2. **Functional Validation**: Built-in AST interpreter + pyUVM framework — coverage reports feed back to AI
3. **PPA Optimization**: AST-based static analysis + ABC synthesis — area/timing reports guide AI optimization
4. **Code Generation**: Automatic output of Verilog / SV UVM Testbench / cocotb tests

For the full tutorial, see [RTLGEN.md](RTLGEN.md).

---

## License

This project uses a custom MIT License. Personal use and research are permitted. **Commercial use requires prior authorization.**
For commercial licensing, please contact the author and Fudan University (State Key Laboratory of Integrated Chips and Systems): efouth@gmail.com

See [LICENSE](LICENSE) for details.

---

## Related Documentation

- [skills/skills.md](skills/skills.md) — Skills directory overview
- [README_CN.md](README_CN.md) — Chinese version of this document
