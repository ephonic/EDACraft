# RTLGEN — Automated RTL Generation with AI Coding Assistants

> Using Claude Code / Kimi Code together with the RTLCraft white-box framework to
> automate the full flow: Spec → RTL Design → Simulation → Optimization → UVM Coverage → Verilog Output.
> The framework and the designs it produces **co-evolve** — each solved problem becomes a reusable component for the next.

---

## 1. Core Philosophy

### 1.1 Six Capabilities of the White-Box Framework

RTLCraft is not just a Verilog generator. It provides six capabilities that, when combined with an AI coding assistant (Claude Code / Kimi Code), enable end-to-end automated RTL design:

| # | Capability | Tool | What It Does |
|---|-----------|------|-------------|
| 1 | **Description** | Python DSL | Object-oriented RTL description — every signal, module, and logic block is an AST node |
| 2 | **Simulation & Debug** | AST Simulator | Cycle-accurate 4-state logic interpreter with VCD waveform export |
| 3 | **Optimization** | PPAAnalyzer + ABC | Static PPA analysis (ms-scale) + Berkeley ABC synthesis for area/timing |
| 4 | **UVM Coverage** | pyUVM | Native Python UVM framework — scoreboard, coverage, directed + random tests |
| 5 | **Co-Evolution** | Protocol bundles, Pipeline, lib | Framework grows alongside designs — verified components become reusable libraries |
| 6 | **Code Generation** | VerilogEmitter, UVMEmitter, CocotbEmitter | Emit Verilog / SV UVM testbench / cocotb test scaffold automatically |

```
┌─────────────────────────────────────────────────────────────┐
│  AI Coding Assistant (Claude Code / Kimi Code)               │
│                                                              │
│  1. Description  ── Python DSL ──▶ AST (Signals, Modules, Logic)   │
│       │                                                        │
│       ▼                                                        │
│  2. Simulation  ── AST Simulator ──▶ Pass / Fail + Waveform        │
│       │         │                                              │
│       │         ▼                                              │
│       │    3. 优化  ── PPA + ABC ──▶ Area / Delay / Gates     │
│       │                                                        │
│       ▼                                                        │
│  4. UVM   ── pyUVM ──▶ Coverage Report + Scoreboard           │
│       │                                                        │
│       ▼                                                        │
│  5. Evolve ── Reusable libs grow (APB, AXI, FIFO, FSM...)     │
│       │                                                        │
│       ▼                                                        │
│  6. Generation  ── Verilog / SV UVM / cocotb / Compiler IR          │
│                                                              │
│  Structured feedback (coverage / PPA / lint) feeds back       │
│  to the AI → diagnose → patch → re-verify → converge          │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 How AI Coding Assistants Drive the Flow

The AI coding assistant (Claude Code / Kimi Code) acts as the orchestrator:

1. **Receives a spec** in natural language
2. **Writes Python RTL code** using RTLCraft's DSL
3. **Runs tests** by executing the code and reading structured output
4. **Reads failure diagnostics** (which cycle, which signal, which value)
5. **Patches the code** — surgical edits, not full regeneration
6. **Re-runs tests** until coverage and PPA budgets are met
7. **Emits final Verilog** with UVM testbench and cocotb scaffold

Because RTLCraft's feedback is structured (Python exceptions, PPA reports, coverage percentages), the AI can reason about failures precisely — unlike a black-box Verilog generator where the only feedback is "it doesn't work."

---

## 2. Environment Setup

### 2.1 Installation

```bash
# Clone the repository
git clone <repo-url>
cd RTLCraft

# Install core dependencies
pip install pyverilog numpy

# Optional: logic synthesis
brew install abc    # macOS
apt-get install abc # Ubuntu
```

### 2.2 Verify Installation

```bash
cd RTLCraft
python3 -c "
from rtlgen import Module, Input, Output, Reg, VerilogEmitter, Simulator
print('RTLCraft is ready')
"
```

---

## 3. Step 1: Description — Python DSL for RTL

RTLCraft uses a Python DSL where hardware is described as objects, not text. Every signal is a typed node with width, every module is a Python class, and logic blocks are decorated functions.

### 3.1 Example: 8-Bit Counter

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

Key design decisions:
- `<<=` operator: unified assignment — auto-selects blocking (`=`) vs non-blocking (`<=`) based on context
- `@self.comb` / `@self.seq`: decorators capture control-flow as AST at construction time
- `with If(...)`: context managers make conditional branches read like Python, generate standard Verilog

### 3.2 More Complex: 4-Operation ALU

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

### 3.3 Standard Component Library

RTLCraft ships with a library of verified components that the AI can reuse instead of generating from scratch:

```python
from rtlgen import SyncFIFO, BarrelShifter, LFSR, CRC, Divider

fifo = SyncFIFO(width=32, depth=16)
shifter = BarrelShifter(width=8, direction="left_rotate")
lfsr = LFSR(width=16, taps=[16, 14, 13, 11], seed=0xACE1)
crc = CRC(data_width=8, poly_width=8, polynomial=0x07)
div = Divider(dividend_width=8, divisor_width=8)
```

---

## 4. Step 2: Simulation & Debug — AST Simulator

### 4.1 Basic Simulation

RTLCraft's simulator interprets the AST directly in Python — no Verilog compilation, no VPI overhead:

```python
from rtlgen import Simulator

dut = Counter(width=8)
sim = Simulator(dut)

sim.reset()             # auto-detect rst/rst_n
sim.poke("en", 1)       # drive input

for i in range(10):
    sim.step()          # advance one clock cycle
    print(f"  cycle {i}: count = {sim.peek('count')}")

# Expected: count = 1, 2, 3, ..., 10
```

### 4.2 AI-Driven Debug: Find and Fix a Bug

Suppose the AI generates a counter but forgets the `en` guard:

```python
@self.seq(self.clk, self.rst)
def _logic():
    with If(self.rst == 1):
        self._cnt <<= 0
    with Else():
        # BUG: missing en guard
        self._cnt <<= self._cnt + 1
```

The AI writes a two-phase test and discovers the bug:

```python
sim = Counter(width=8)
sim = Simulator(dut)
sim.reset()

# Phase 1: en=0, count should stay 0
sim.poke("en", 0)
for _ in range(3):
    sim.step()
assert sim.peek("count") == 0, f"en=0 but count={sim.peek('count')}"

# Phase 2: en=1, count should increment
sim.poke("en", 1)
for _ in range(3):
    sim.step()
assert sim.peek("count") == 3, f"en=1 but count={sim.peek('count')}"
```

The structured assertion error tells the AI exactly what went wrong:
```
AssertionError: en=0 but count=3
```

The AI diagnoses the issue (missing `en` guard) and patches the code — one line change, not full regeneration.

### 4.3 Simulation Speed

| Design | Cycles | RTLCraft | cocotb + Icarus |
|--------|--------|----------|-----------------|
| Counter | 100 | ~0.8 ms | ~3,500 ms |
| Pipeline Adder | 100 | ~1.2 ms | ~5,000 ms |

The native interpreter is **~70x faster** for small designs because it eliminates Verilog compilation (~2-3s) and VPI communication overhead.

---

## 5. Step 3: Optimization — PPA Analysis

### 5.1 Static PPA (milliseconds)

```python
from rtlgen import PPAAnalyzer

dut = Counter(width=8)
ppa = PPAAnalyzer(dut)
report = ppa.analyze_static()

print(f"Gate count: {report['gate_count']}")
print(f"Logic depth: {report['logic_depth']}")
# Counter: gates=38, depth={'count': 7, 'cnt': 7}
```

### 5.2 AI-Driven Optimization Loop

The AI uses PPA as a cheap surrogate objective:

```python
# AI reads PPA report, identifies critical path
# If depth > budget: insert pipeline stage
# If gates > budget: simplify logic or swap arithmetic style

from rtlgen.blifgen import AdderStyle, MultiplierStyle, SynthConfig

# Example: swap multiplier style without rewriting RTL
config = design.get_config()
config.multiplier = MultiplierStyle.WALLACE  # was ARRAY
```

Static analysis completes in **<1 ms**, making it suitable for rapid iteration. The AI can evaluate hundreds of candidates before invoking the slower ABC synthesis backend.

---

## 6. Step 4: UVM Coverage — pyUVM Framework

### 6.1 Native Python UVM

RTLCraft implements a full UVM-like framework in Python:

```python
from rtlgen.pyuvm import UVMTest, delay
from rtlgen.pyuvm_sim import run_test


class CounterTest(UVMTest):
    def __init__(self, name, parent=None):
        super().__init__(name, parent)
        self.vif = None  # virtual interface (bound by framework)

    async def run_phase(self, phase):
        phase.raise_objection(self)

        # Reset
        self.vif.cb.rst <= 1
        self.vif.cb.en <= 0
        await delay(2)
        self.vif.cb.rst <= 0
        await delay(1)

        # Test 1: en=0, count should stay 0
        for _ in range(5):
            self.vif.cb.en <= 0
            await delay(1)
            assert self.vif._read("count") == 0

        # Test 2: en=1, count should increment
        expected = 0
        for _ in range(20):
            self.vif.cb.en <= 1
            await delay(1)
            expected = (expected + 1) & 0xFF
            assert self.vif._read("count") == expected

        # Test 3: en=0 again, count should hold
        for _ in range(5):
            self.vif.cb.en <= 0
            await delay(1)
            assert self.vif._read("count") == expected

        phase.drop_objection(self)


# Run the test
dut = Counter(width=8)
sim = Simulator(dut)
test = CounterTest("counter_test")
run_test(test, sim, max_cycles=200)
# [CHECKER] total=0 passed=0 failed=0
# UVM test completed in ~1.2ms
```

### 6.2 Coverage-Driven Bug Discovery

For the ALU example, the AI creates a scoreboard comparing DUT output against a Python reference model:

```python
def ref_model(a, b, op):
    if op == 0: return (a + b) & 0xFFFF
    elif op == 1: return (a - b) & 0xFFFF
    elif op == 2: return a & b
    else: return a | b

# 56 tests: 6 directed + 50 random
for i in range(50):
    a, b, op = random.randint(0, 0xFFFF), random.randint(0, 0xFFFF), random.randint(0, 3)
    # ... drive DUT and compare with ref_model ...
```

All 56 tests pass — the AI has achieved functional correctness.

### 6.3 Dual-Mode Execution

The same pyUVM testbench can be:
- **Run in Python** for rapid iteration (~1-20ms per test)
- **Exported to SystemVerilog** for sign-off with commercial simulators (VCS, Xcelium)

---

## 7. Step 5: Tool Evolution — Framework Grows with Designs

### 7.1 Protocol Bundles

RTLCraft includes pre-built protocol bundles that the AI can reuse:

```python
from rtlgen import APB, AXI4Lite, AXI4, AXI4Stream, Wishbone

apb = APB(addr_width=32, data_width=32)    # 12 signals
axi = AXI4Lite(addr_width=32, data_width=32)  # 19 signals
```

The AI doesn't need to write APB/AXI glue logic from scratch — it composes existing bundles into new designs.

### 7.2 Pipeline Engine

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

pipe.build()  # auto-generates inter-stage registers, ready back-pressure, handshake ports
# Generated: 58 lines of Verilog in 0.13ms
```

### 7.3 UVM Testbench Auto-Generation

For any DUT, the AI can generate a complete UVM testbench:

```python
from rtlgen import UVMEmitter

uvm = UVMEmitter()
files = uvm.emit_full_testbench(dut)
# Generates 12 files:
#   SimpleDUT_if.sv, SimpleDUT_pkg.sv, SimpleDUT_transaction.sv,
#   SimpleDUT_driver.sv, SimpleDUT_monitor.sv, SimpleDUT_agent.sv,
#   SimpleDUT_scoreboard.sv, SimpleDUT_env.sv, SimpleDUT_sequence.sv,
#   SimpleDUT_sequencer.sv, SimpleDUT_test.sv, tb_top.sv
```

### 7.4 Co-Evolution: Design-Driven Library Growth

As the AI solves more problems, the framework grows:

```
New design → Verified → Added to skills/ → Becomes reusable reference
                                                     ↓
                                   AI reuses verified modules instead of generating from scratch
```

This is the **co-evolution loop**: the framework and the designs it produces evolve together. Each solved problem becomes a building block for the next, making the AI more productive over time.

---

## 8. Step 6: Code Generation — Verilog / UVM / cocotb

### 8.1 Verilog-2001 / SystemVerilog

```python
from rtlgen import VerilogEmitter
from rtlgen.lint import VerilogLinter

dut = Counter(width=8)
sv = VerilogEmitter().emit(dut)

# Auto-lint
lint = VerilogLinter()
result = lint.lint(sv)
if result.fixed_text:
    sv = result.fixed_text
```

### 8.2 cocotb Test Scaffold

```python
from rtlgen import CocotbEmitter

cocotb = CocotbEmitter()
test_code = cocotb.emit_test(dut)
# Generates random-stimulus cocotb test with clock driver and reset sequence
```

### 8.3 Protocol VIP Generation

```python
from rtlgen import UVMEmitter

# Generate APB UVM VIP
apb_dut = ...  # any APB slave
files = UVMEmitter().emit_full_testbench(apb_dut)
# Generates complete APB agent, driver, monitor, scoreboard
```

---

## 9. Advanced: Processor/NPU Compiler Auto-Generation

### 9.1 NPU Compiler

RTLCraft's NPU (`skills/cpu/npu/`) includes a systolic array, vector ALU, SFU, pooling unit, and scratchpad memory. The AI can auto-generate a compiler:

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

### 9.2 BOOM-Style OoO Core

```python
from skills.cpu.boom.core import BOOMCore

core = BOOMCore()
core.branch_predictor.bht_entries = 128  # AI modifies parameters
core.rob_size = 64
```

---

## 10. Automated RTL Design with Claude Code

This section shows **exactly how** to use Claude Code (or Kimi Code) to automate the full RTL design flow — from initial generation through debugging, PPA optimization, UVM coverage improvement, and final code generation.

### 10.1 The Multi-Round Automation Loop

The core pattern is a **closed-loop conversation** between the user and the AI assistant:

```
Round 1: Spec → Generate RTL → Basic sim test
Round 2: Sim failure → Diagnose → Patch → Re-test
Round 3: PPA report → Optimize → Re-synthesize
Round 4: Low coverage → Add tests → Re-verify
Round 5: Converged → Generate Verilog + UVM + cocotb
```

Each round feeds **structured feedback** (assertion errors, PPA metrics, coverage reports) back to the AI, which diagnoses the issue and makes a surgical patch.

### 10.2 Round 1: Initial Generation

**User prompt:**

```
Using RTLCraft, implement an 8-bit up/down counter with the following spec:

Module name: UpDownCounter
Ports:
  - clk (input, 1-bit): clock
  - rst (input, 1-bit): synchronous reset, active high
  - load (input, 1-bit): load enable
  - up_down (input, 1-bit): 1=count up, 0=count down
  - load_val (input, 8-bit): value to load when load=1
  - count (output, 8-bit): current count value

Behavior:
  - On reset, count = 0
  - When load=1, count = load_val
  - When load=0 and up_down=1, count increments by 1 each cycle
  - When load=0 and up_down=0, count decrements by 1 each cycle
  - Count wraps around on overflow/underflow

Requirements:
1. Write the module to counter.py
2. Run a basic simulation test: reset, load value 5, count up 3 cycles,
   count down 2 cycles, verify results
3. Report any errors
```

**What the AI does:**
1. Writes `counter.py` with the `UpDownCounter` class using RTLCraft DSL
2. Appends a `__main__` block that creates the module, runs `Simulator`, and checks results
3. Executes the code and reads the output

**Expected output (if correct):**
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

**Common AI mistakes in Round 1:**
- Forgetting to gate an update signal (e.g., missing `load` check)
- Wrong operator precedence in conditional logic
- Width mismatch between signals

The AI self-corrects within 1-2 rounds when given the structured error output.

### 10.3 Round 2: Automatic Debug Loop

When the simulation fails, the AI sees a structured error like:

```
AssertionError at cycle 3: expected count=6, got count=5
  Signal trace: cycle 0: count=0, cycle 1: count=5, cycle 2: count=5, cycle 3: count=5
```

**Follow-up prompt (auto-generated by AI or user):**

```
The simulation failed at cycle 3: expected count=6, got count=5.
The counter was loaded with value 5, then up_down=1 for 3 cycles.
Expected sequence: 5→6→7→8, but actual: 5→5→5→5.

The count value is not incrementing. Check the @self.seq logic block
for the up/count path. Fix the bug and re-run the test.
```

**What the AI does:**
1. Reads the error — identifies the count isn't changing
2. Reads the source code — finds the bug (e.g., `self._cnt <<= self._cnt` instead of `self._cnt <<= self._cnt + 1`)
3. Makes a surgical edit — one line change
4. Re-runs the simulation — verifies pass

**Key insight:** The AI doesn't regenerate the entire file. It reads the error, diagnoses the root cause in the AST source, and applies a minimal patch — exactly how a human engineer debugs.

### 10.4 Round 3: Automatic PPA Optimization

Once functional, the user asks the AI to optimize for area/timing:

**User prompt:**

```
The UpDownCounter is functional. Now run PPA analysis and optimize
for area. If the gate count is above 100, try to simplify the logic.
Report the before/after metrics.
```

**What the AI does:**

```python
from rtlgen.ppa import PPAAnalyzer
from rtlgen.synth import ABCSynthesizer

# Step 1: Static PPA analysis
dut = UpDownCounter()
ppa = PPAAnalyzer(dut)
report = ppa.analyze_static()
print(f"Gate count: {report['gate_count']}")
print(f"Logic depth: {report['logic_depth']}")

# Step 2: If area is too high, optimize
# For example, if the AI used a complex MUX chain,
# it might simplify to a single adder/subtractor:
#
# Before (verbose):
#   with If(self.up_down == 1):
#       self._cnt <<= self._cnt + 1
#   with Else():
#       self._cnt <<= self._cnt - 1
#
# After (compact — single +/- operation):
#   direction = Wire(9, "dir")
#   direction <<= Concat(self.up_down, 0)  # 0b01 or 0b00
#   self._cnt <<= self._cnt + direction - 1

# Step 3: Re-analyze
report2 = ppa.analyze_static()
print(f"Optimized gate count: {report2['gate_count']}")
```

**Expected output:**
```
[BEFORE] Gate count: 52, Logic depth: {'count': 5}
[AFTER]  Gate count: 44, Logic depth: {'count': 4}
Area reduced by 15%
```

**PPA optimization patterns the AI can apply:**

| Pattern | Before | After | Savings |
|---------|--------|-------|---------|
| Redundant MUX | Two nested `If` → two MUX cascades | Single `If` with combined condition | 10-20% |
| Adder style | Ripple-carry (default) | Kogge-Stone (via config) | 30-50% delay |
| Multiplier style | Array | Wallace tree | 20-40% area |
| Dead code | Unused signal assignments | Removed by linter | 5-10% |

### 10.5 Round 4: Automatic UVM Coverage Improvement

**User prompt:**

```
Create a pyUVM testbench for the UpDownCounter. Target 100% functional
coverage on these bins:
- reset behavior (reset at different count values)
- load behavior (load different values, including 0 and 255)
- count up (from 0, from mid-range, from 254 with wrap)
- count down (from 255, from mid-range, from 0 with wrap)
- load+up/down combinations
- hold (load=0, up_down unchanged for multiple cycles)

Start with directed tests, then add random tests for any uncovered bins.
Run the tests and report coverage. If any bin is missed, add a directed
test for it and re-run.
```

**What the AI does:**

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

        # Reset tests
        self.vif.cb.rst <= 1; self.vif.cb.load <= 0; await delay(2)
        self.vif.cb.rst <= 0; await delay(1)
        assert self.vif._read("count") == 0
        self._record("reset_from_zero")

        # Load tests
        self.vif.cb.load <= 1; self.vif.cb.load_val <= 255; await delay(1)
        self.vif.cb.load <= 0; await delay(1)
        assert self.vif._read("count") == 255
        self._record("load_max")

        # ... more directed tests ...

        # Random test: cover edge cases
        import random
        for _ in range(20):
            val = random.choice([0, 1, 127, 128, 254, 255])
            self.vif.cb.load <= 1; self.vif.cb.load_val <= val; await delay(1)
            self.vif.cb.load <= 0
            for _ in range(5):
                self.vif.cb.up_down <= random.choice([0, 1])
                await delay(1)

        print(f"Coverage: {self.cov.report()}")
        phase.drop_objection(self)


dut = UpDownCounter()
sim = Simulator(dut)
test = CounterTest("counter_test")
run_test(test, sim, max_cycles=500)
```

**Coverage improvement loop:**

If the coverage report shows missed bins:

```
Coverage report:
  reset_from_zero: HIT (1 samples)
  reset_from_mid:  MISS
  load_zero:       HIT (1 samples)
  load_max:        HIT (1 samples)
  load_mid:        MISS
  ...
```

**User prompt (or AI auto-prompt):**

```
Coverage report shows 2 missed bins: reset_from_mid and load_mid.
Add directed tests for these two bins and re-run.
```

The AI adds two specific test cases and re-runs until all bins are covered.

### 10.6 Round 5: Final Code Generation

**User prompt:**

```
All tests pass and coverage is 100%. Generate:
1. Clean Verilog output
2. Complete UVM testbench in SystemVerilog
3. cocotb test scaffold
4. Save all files to output/counter/
```

**What the AI does:**

```python
import os
from rtlgen import VerilogEmitter, UVMEmitter, CocotbEmitter
from rtlgen.lint import VerilogLinter
from rtlgen.synth import ABCSynthesizer

os.makedirs("output/counter", exist_ok=True)

# 1. Verilog with linting
dut = UpDownCounter()
sv = VerilogEmitter().emit(dut)
lint = VerilogLinter()
result = lint.lint(sv)
if result.fixed_text:
    sv = result.fixed_text
with open("output/counter/counter.v", "w") as f:
    f.write(sv)

# 2. Synthesis check
synth = ABCSynthesizer()
synth.run(input_blif="/tmp/counter.blif", output_verilog="output/counter/counter_syn.v")

# 3. UVM testbench
uvm = UVMEmitter()
files = uvm.emit_full_testbench(dut, output_dir="output/counter/uvm")
print(f"Generated {len(files)} UVM files")

# 4. cocotb test
cocotb = CocotbEmitter()
test_code = cocotb.emit_test(dut)
with open("output/counter/test_counter.py", "w") as f:
    f.write(test_code)
```

### 10.7 Universal Prompt Templates

#### Template A: New Design (one-shot)

```
Using RTLCraft, implement the following module:

Module: {name}
Spec:
  Ports: {port list with widths and directions}
  Behavior: {functional description}

Steps:
1. Write the module class to {filepath}.py
2. In __main__, create a Simulator test with directed vectors covering:
   - Reset behavior
   - All major operation modes
   - Boundary cases (zero, max, wrap)
3. Run and verify all assertions pass
4. If any assertion fails, diagnose and fix before proceeding
5. Run PPAAnalyzer and report gate count + logic depth
6. Generate Verilog with VerilogEmitter
```

#### Template B: Bug Fix

```
The simulation for {module} failed:

Error: {exact error message}
Signal trace at failure: {relevant signal values}
Expected: {expected values}
Got: {actual values}

Read the source at {filepath}.py, identify the root cause in the
@self.seq or @self.comb logic block, and apply a minimal fix.
Re-run the simulation to verify.
```

#### Template C: PPA Optimization

```
{module} is functional but needs area/timing optimization.

Current metrics:
  Gate count: {N}
  Logic depth: {D}
  Target: gate_count < {target_gates}, depth < {target_depth}

Read the source at {filepath}.py and identify optimization opportunities:
- Redundant MUX cascades that can be simplified
- Operators that can use a more efficient implementation
- Dead code or unused signals

Apply the optimization, re-run PPA analysis, and report before/after.
```

#### Template D: Coverage Improvement

```
The pyUVM testbench for {module} has incomplete coverage:

Missed bins:
{list of missed coverage bins}

For each missed bin, write a directed test case that specifically
exercises that scenario. Add them to the CounterTest.run_phase method.
Re-run the test and report updated coverage.

If a bin cannot be covered, explain why (unreachable state, mutually
exclusive conditions, etc.).
```

#### Template E: Complete Flow (end-to-end)

```
Design and verify the following module using RTLCraft:

Module: {name}
Spec: {full specification}

Execute the complete flow:
1. Write RTL in Python DSL → {filepath}.py
2. Simulate with directed tests → fix any bugs
3. Run PPA static analysis → optimize if needed
4. Create pyUVM testbench with coverage → achieve all bins
5. Generate Verilog, lint, and synthesis-check with ABC
6. Generate SV UVM testbench and cocotb test
7. Save all outputs to {output_dir}/

Report: final gate count, logic depth, coverage %, test count,
all file paths generated.
```

### 10.8 Advanced: Automated Coverage-Driven Debugging

For complex designs, the AI can use coverage gaps to **discover bugs** that directed tests miss:

```python
# AI generates random tests and watches for coverage holes
for seed in range(100):
    random.seed(seed)
    # drive random inputs ...
    if dut fails:
        print(f"BUG FOUND at seed={seed}")
        print(f"  a={a}, b={b}, op={op}")
        print(f"  expected={ref_model(a,b,op)}, got={result}")
        # AI reads this, diagnoses, patches
```

This is how RTLCraft discovered the ALU subtraction bug: the random test found that `a - b` produced wrong results when `a < b` because the AI had used unsigned subtraction without handling the borrow correctly. The coverage gap (the "subtraction with borrow" bin was never hit by directed tests) was exposed by the random seed sweep.

### 10.9 AI Coding Assistant Best Practices

| Practice | Why |
|----------|-----|
| **Run code after every edit** | Catch bugs immediately instead of batch-regenerating |
| **Use assertions, not print statements** | Assertions give structured errors the AI can diagnose |
| **One fix per round** | Avoid cascading changes that create new bugs |
| **Read the source before editing** | AI should read the file it's about to modify, not guess |
| **Preserve working tests** | When adding new tests, don't break existing ones |
| **Use the standard library** | `SyncFIFO`, `BarrelShifter`, `CRC` etc. are verified — reuse them |
| **Keep prompts specific** | "Fix the enable guard on line 20" beats "make it work" |

---

## 11. FAQ

### Q: What if the AI-generated code doesn't run?

RTLCraft's API has type checking and runtime validation. If the AI generates incorrect code (e.g., width mismatch), Python raises an exception immediately. Feed the exception back to the AI — it typically self-corrects within 1-2 rounds.

### Q: How does simulation speed compare to external tools?

The Python AST interpreter is ~70x faster than cocotb+Icarus for small designs (<1000 cycles). For large designs, use `cocotbgen` to generate cocotb tests and run them with an external simulator.

### Q: How do I ensure the generated Verilog is synthesizable?

RTLCraft's DSL is designed for synthesizability from the start:
- `@self.comb` generates `always @(*)`
- `@self.seq` generates `always @(posedge clk)`
- `<<=` auto-selects blocking/non-blocking based on context
- `VerilogLinter` catches and auto-fixes common issues

### Q: Can I use other AI tools?

Yes. Any AI assistant that can execute Python code (Claude Code, Kimi Code, Cursor, etc.) works with RTLCraft. The key capabilities needed are:
1. Read code
2. Execute code
3. View execution results
4. Modify code

---

## 12. Related Resources

- [README.md](README.md) — Project overview
- [skills/skills.md](skills/skills.md) — Skills directory
- [paper/main.pdf](paper/main.pdf) — Research paper
