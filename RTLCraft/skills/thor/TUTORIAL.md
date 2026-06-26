# Thor GPU — Three-Layer Design Tutorial

## 1. Overview

Thor GPU design follows a **three-layer metamodel** that progressively refines from abstract specification to synthesizable RTL:

```
Layer 1 — Functional (functional.py)
    │ Pure Python functions, no timing. Verify algorithm correctness.
    ▼
Layer 2 — Cycle-Accurate (cycle_level.py)
    │ CycleContext closures, register-accurate timing. Verify pipeline.
    ▼
Layer 3 — RTL DSL (layer3_dsl/*.py)
    │ Module subclasses, synthesizable Verilog. Bit/cycle exact.
    ▼
Verilog (rtlgen.codegen.VerilogEmitter)
```

**Cross-layer consistency** is mandatory: the same test program must produce identical results at all three layers. Enforced by `test_consistency.py`.

## 2. L1: Functional Model

### Specification

```
Signature: module_functional(**kwargs) -> Callable
Inner fn:  func(**inputs) -> Dict[str, int]
```

| Property | Requirement |
|----------|-------------|
| Timing | **None**. Pure combinational, no clock, no cycle concept |
| State | **None**. Stateless; caller manages state explicitly |
| Inputs | Named Python keyword args with defaults and type hints |
| Outputs | `Dict[str, int]`, keys matching L3 port names |
| Config | Via factory `**kwargs` (e.g., `width=16`) |

### Example

```python
# skills/thor/functional.py

def vector_alu_functional(**kwargs) -> Callable:
    n_lane = kwargs.get('n_lane', 16)
    xlen = kwargs.get('xlen', 32)
    mask = (1 << xlen) - 1

    def func(opcode: int = 0, op1: int = 0, op2: int = 0,
             pred_mask: int = 0xFFFF) -> Dict:
        result = 0
        for lane in range(n_lane):
            if not ((pred_mask >> lane) & 1):
                continue
            a = (op1 >> (lane * xlen)) & mask
            b = (op2 >> (lane * xlen)) & mask
            r = (a + b) & mask if opcode == OP_VADD else (a * b) & mask
            result |= r << (lane * xlen)
        return {"result": result, "valid": 1}
    return func
```

### Usage

```python
alu_fn = vector_alu_functional(n_lane=16, xlen=32)
r = alu_fn(opcode=OP_VADD, op1=broadcast(5), op2=broadcast(3),
           pred_mask=0xFFFF)
assert r["result"] == broadcast(8)
```

### Registration

All L1 models are registered in `FUNCTIONAL_MODELS` dict for name-based lookup:

```python
FUNCTIONAL_MODELS = {
    "vector_alu": vector_alu_functional,
    "warp_scheduler": warp_scheduler_functional,
    # ... 18 modules total
}
```

## 3. L2: Cycle-Accurate Model

### Specification

```
Signature: module_cycle(**kwargs) -> Callable[[CycleContext], None]
Inner fn:  behavior(ctx: CycleContext) -> None
```

| Property | Requirement |
|----------|-------------|
| Timing | **Cycle-accurate**. One `ArchSimulator.step()` = one clock cycle |
| State | `ctx.state[]` persists across cycles; `ctx.set_state()` writes `next_state` |
| Reset | **Mandatory**. Every behavior must check `rst` first |
| Inputs | `ctx.get_input('name', default)` |
| Outputs | `ctx.set_output('name', value)` |
| Registration | `TemplateRegistry.register('name', behavior_fn)` |

### CycleContext API

```python
class CycleContext:
    cycle: int                      # current cycle number
    inputs: Dict[str, Any]          # current input values
    outputs: Dict[str, Any]         # current output values (write-only)
    state: Dict[str, Any]           # current state (read-only)
    next_state: Dict[str, Any]      # next state (written by set_state)

    def get_input(self, name, default=0) -> Any
    def set_output(self, name, value)
    def get_state(self, name, default=None) -> Any
    def set_state(self, name, value)  # → next_state, visible next cycle
```

### Example

```python
# skills/thor/cycle_level.py

def warp_scheduler_cycle(**kwargs) -> Callable[[CycleContext], None]:
    n_warps = kwargs.get('n_warps', 4)

    def behavior(ctx: CycleContext) -> None:
        # Step 1: Reset
        rst = ctx.get_input('rst', 0)
        if rst == 1:
            ctx.state['last_warp'] = 0
            return

        # Step 2: Read inputs
        warp_ready = ctx.get_input('warp_ready_mask', 0)
        warp_stall = ctx.get_input('warp_stall_mask', 0)

        # Step 3: Computation
        avail = warp_ready & ~warp_stall
        last = ctx.state.get('last_warp', 0)
        sel, valid = last, 0
        if avail:
            for i in range(n_warps):
                idx = (last + 1 + i) % n_warps
                if (avail >> idx) & 1:
                    sel, valid = idx, 1; break

        # Step 4: Update state (→ next cycle)
        ctx.state['last_warp'] = sel

        # Step 5: Write outputs (this cycle)
        ctx.set_output('selected_warp', sel)
        ctx.set_output('select_valid', valid)
    return behavior
```

### Execution Model

```
ArchSimulator.step()
  │
  ├─ 1. Model callback (arch.model.on_cycle)
  ├─ 2. Interconnect delay countdown
  ├─ 3. FIFO data transfer
  ├─ 4. PE delay countdown
  ├─ 5. Topo-sorted PE execution
  │      └─ Each PE: CycleContext → behavior(ctx) → collect outputs
  ├─ 6. Signal interconnect (src output → dst input)
  └─ 7. State commit (next_state → state), cycle++
```

## 4. L3: RTL DSL Model

### Specification

```
Inherit:  class MyModule(rtlgen.core.Module)
Signals:  Input(width, name) / Output(width, name)
          Wire(width, name) / Reg(width, name)
Combinational:  with self.comb:
Sequential:     with self.seq(clk, rst):
Assignment:     signal <<= expr
```

### Example

```python
# skills/thor/layer3_dsl/warp_scheduler.py
from rtlgen.core import Module, Input, Output, Wire, Reg
from rtlgen.logic import If, Else, ForGen

class WarpScheduler(Module):
    def __init__(self, name="warp_scheduler"):
        super().__init__(name)
        self.clk = Input(1, "clk"); self.rst = Input(1, "rst")
        self.warp_ready = Input(4, "warp_ready")
        self.warp_stall = Input(4, "warp_stall")
        self.selected_warp = Output(2, "selected_warp")
        self.select_valid = Output(1, "select_valid")

        self._last = Reg(2, "last_warp")

        with self.comb:
            avail = self.warp_ready & ~self.warp_stall
            self.select_valid <<= (avail != 0)
            for i in range(4):
                idx = (self._last + i + 1) & 3
                with If((avail >> self._last) & 1):
                    self.selected_warp <<= self._last

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self._last <<= 0
            with Else():
                with If(self.select_valid):
                    self._last <<= self.selected_warp
```

### Pipeline Module Pattern

```python
class VectorALU(Module):
    def __init__(self, name="vector_alu", latency=3):
        # ... ports ...
        self._pv = [Reg(1, f"pv_{i}") for i in range(latency)]
        self._pd = [Reg(512, f"pd_{i}") for i in range(latency)]

        with self.comb:
            self.in_ready <<= (self._pv[latency-1] == 0) | self.out_ready

        with self.seq(self.clk, self.rst):
            # Reverse-order shift for correct pipeline drain
            with If(self._pv[latency-1] & self.out_ready):
                self._pv[latency-1] <<= 0
            for s in range(latency-2, -1, -1):
                nxt_free = (self._pv[s+1] == 0)
                with If(self._pv[s] & (nxt_free | self.out_ready)):
                    self._pd[s+1] <<= self._pd[s]
                    self._pv[s+1] <<= 1; self._pv[s] <<= 0
            with If(self.in_valid & self.in_ready):
                self._pd[0] <<= self.op1 + self.op2
                self._pv[0] <<= 1
```

## 5. Template Library

RTLCraft ships 22 parameterized micro-architecture templates in `rtlgen/lib.py`:

### Pipeline & FIFO

```python
from rtlgen.lib import PipelineShift, SyncFIFO, AsyncFIFO

# 3-stage pipeline with valid/ready handshake
p = PipelineShift(width=32, depth=3)

# Synchronous FIFO
f = SyncFIFO(width=32, depth=8)

# Async FIFO with Gray-code CDC pointers
af = AsyncFIFO(width=32, depth=8)
```

### Cross-Domain Clocking (CDC)

```python
from rtlgen.lib import SyncCell, PulseSynchronizer, AsyncResetRel, GrayCounter

# 2-flop synchronizer
s = SyncCell(width=32)  # data_in → clk_dst domain

# Pulse synchronizer (toggle + edge detect)
ps = PulseSynchronizer()  # pulse_in → pulse_out across domains

# Async reset synchronizer
ar = AsyncResetRel()  # async rst → sync rst release
```

### Cache Hierarchy

```python
from rtlgen.lib import DirectMappedCache, SetAssocCache, CAM

# Direct-mapped cache (4KB, 64B lines)
d = DirectMappedCache(size=4096, line_size=64)

# 4-way set-associative cache with LRU (16KB)
s = SetAssocCache(n_ways=4, size=16384)

# Fully-associative CAM (8 entries, 32-bit)
c = CAM(width=32, depth=8)
```

### Compute

```python
from rtlgen.lib import MAC, SignedMultiplier, MultiCyclePath

# Pipelined multiply-accumulate
m = MAC(width=16)  # acc = acc + a*b, 2-stage pipe

# Pipelined signed multiplier (3-stage, valid/ready)
sm = SignedMultiplier(width=16, latency=3)

# Multi-cycle path (hold data for N cycles)
mcp = MultiCyclePath(width=32, n_cycles=2)
```

### All 22 Templates

| Template | Description | Line Count |
|----------|-------------|-----------|
| `PipelineShift` | Configurable pipeline + valid/ready | 60 |
| `SyncFIFO` | Synchronous FIFO | 85 |
| `AsyncFIFO` | Async FIFO + Gray-code CDC | 88 |
| `RoundRobinArbiter` | Round-robin arbiter | 90 |
| `Counter` | Loadable up-counter | 38 |
| `MultiCycleFSM` | IDLE→REQ→WAIT→DONE FSM | 51 |
| `RegisterFile` | Multi-port reg file | 190 |
| `DualPortRAM` | Dual-port RAM | 27 |
| `CAM` | Fully-associative CAM | 109 |
| `LUT` | Lookup table ROM | 81 |
| `MAC` | Pipelined multiply-accumulate | 43 |
| `SignedMultiplier` | Signed multiplier, valid/ready | 70 |
| `DirectMappedCache` | Direct-mapped cache | 61 |
| `SetAssocCache` | N-way set-assoc + LRU | 116 |
| `SyncCell` | 2-flop CDC synchronizer | 29 |
| `PulseSynchronizer` | Pulse CDC | 43 |
| `EdgeDetector` | Rising/falling edge | 28 |
| `ClockGate` | Latch-based clock gate | 25 |
| `AsyncResetRel` | Async reset release | 23 |
| `OneHotMux` | One-hot mux | 27 |
| `PipelineInterlock` | Pipeline stall/hold | 35 |
| `BypassNetwork` | Forwarding network | 45 |
| `GrayCounter` | Gray code counter | 28 |
| `MultiCyclePath` | Multi-cycle path | 32 |

## 6. PPA-Driven Optimization

The `PPAAnalyzer` performs static and dynamic analysis on any Module AST:

```python
from rtlgen.ppa import PPAAnalyzer
from rtlgen.lib import MAC

mac = MAC(width=16)
pa = PPAAnalyzer(mac)

# Static analysis (no simulation needed)
static = pa.analyze_static()
print(f"Gate count: {static['gate_count']:.0f}")
print(f"Reg bits:   {static['reg_bits']}")
print(f"Logic depth: {static['logic_depth']}")
print(f"Fanout:     {static['fanout_report']}")

# Optimization suggestions
for s in pa.suggest_optimizations():
    print(s)

# Full report
print(pa.report())
```

### Optimization Loop

```
1. Write/Modify DSL module
2. PPAAnalyzer.analyze_static() → get gate_count, logic_depth, fanout
3. If logic_depth > 6: insert PipelineShift stages
4. If fanout > 8: replicate high-fanout signals
5. If dead_signals present: remove unused logic
6. Re-emit Verilog, re-verify
```

## 7. UVM Verification

### Generate UVM Testbench

```python
from rtlgen.uvmgen import UVMEmitter
from rtlgen.lib import MAC

mac = MAC(width=16)
uvm = UVMEmitter()
files = uvm.emit_full_testbench(mac)
# files = {"MAC_if.sv": ..., "MAC_pkg.sv": ..., "MAC_driver.sv": ..., ...}
```

### Golden Trace Bridge

```python
from rtlgen.uvm_scoreboard import generate_golden_trace
from rtlgen.lib import MAC

mac = MAC(width=16)
stimuli = [
    {"a": 5, "b": 3},
    {"a": 7, "b": 2},
]
outputs = ["acc_out", "valid"]

sv_code, golden_data = generate_golden_trace(mac, stimuli, outputs)
# sv_code: UVM scoreboard SV code
# golden_data: per-cycle expected values
```

## 8. Three-Layer Comparison

| Dimension | L1 Functional | L2 Cycle-Level | L3 DSL |
|-----------|---------------|----------------|--------|
| **File** | `functional.py` | `cycle_level.py` | `layer3_dsl/*.py` |
| **Declaration** | `def fn(**kw) → Dict` | `def fn(ctx) → None` | `class M(Module)` |
| **State** | Caller-managed | `ctx.state[]` auto-persist | `Reg` signals |
| **Timing** | None | Cycle-level (step) | Clock-edge (posedge) |
| **Reset** | None | Manual `if rst:` | `with self.seq(clk, rst):` |
| **Inputs** | Function args | `ctx.get_input()` | `Input(width, name)` |
| **Outputs** | `return Dict` | `ctx.set_output()` | `Output <<=` |
| **Combinational** | All of it | `ctx.state` comb use | `with self.comb:` |
| **Sequential** | ❌ | `ctx.state` cross-cycle | `with self.seq():` |
| **Submodules** | Function composition | PE hierarchy | `self.instantiate()` |
| **Control flow** | Python `if/for` | Python `if/for` | `If/Switch/ForGen` |
| **Simulator** | None (direct call) | `ArchSimulator` | `Simulator` |
| **Speed** | ~1μs/call | ~100μs/cycle | ~45μs/step (JIT) |
| **Verilog** | ❌ | ❌ | ✅ `VerilogEmitter` |
| **Best for** | Algorithm verify | Architecture explore | RTL generation |

## 9. Cross-Layer Consistency

### Verification Method

The same program executed through all three layers must produce identical results:

```
Program (instruction sequence)
  ├──→ L1 functional.py    → Dict[str, int]
  ├──→ L2 cycle_level.py   → ArchSimulator signals
  └──→ L3 layer3_dsl/*.py  → Simulator signals
                              ↓ compare
                         Must be identical
```

### Implementation

```python
def test_cross_layer_consistency():
    """Same program on L1 and Golden model must match."""

    # L1 functional
    from skills.thor.functional import sm_wrapper_functional
    l1_fn = sm_wrapper_functional()
    rf = [0] * 16
    for pc, code in enumerate(program):
        r = l1_fn(inst=code, pc=pc, rf=rf, pred_mask=0xFFFF)
        if r["wb_valid"]:
            rf[r["wb_dest"]] = r["wb_data"]
    l1_result = rf[2]

    # Golden model (equivalent to L2 + L3)
    from skills.thor.models import ThorSM_Model
    sm = ThorSM_Model(nwarp=1, vregs=8)
    for addr, data in enumerate(program):
        sm.load_imem(addr, data)
    for _ in range(100):
        result = sm.step(start=start)
        if result["sm_done"]: break
    golden_result = sm.vrf[0 * 8 + 2]

    assert l1_result == golden_result  # must match bit-for-bit
```

### Test Coverage (`test_consistency.py`)

| Test | Description |
|------|-------------|
| L1 SLOAD broadcast | All 16 lanes receive same immediate |
| L1 SIMD VADD/VMUL | Per-32-bit-lane correct |
| L2 SM behavior | ArchSimulator runs full program |
| L3 Pipeline valid | Multi-cycle pipeline handshake works |
| Golden compute | `5*3 + 7*2 = 29` |
| Golden multi-warp | 4 warps, independent VRF |
| Golden full GPU | 2 SMs + round-robin arbiter |
| Cross-layer | L1 == Golden (bit-identical) |

## 10. API Reference

### CycleContext

```python
ctx.get_input(name, default=0)        # Read input
ctx.set_output(name, value)            # Write output
ctx.get_state(name, default=None)      # Read state
ctx.set_state(name, value)             # Write next-state
ctx.retire(n=1)                        # Retire count
ctx.record_metric(key, value)          # Performance metric
ctx.memory_read(addr, size=4)          # Memory read
ctx.memory_write(addr, value, size=4)  # Memory write
ctx.register_read(rf_name, idx)        # Register read
ctx.register_write(rf_name, idx, v)    # Register write
ctx.cache_access(cache, addr)          # Cache access
```

### Module Signal API

```python
# Declaration
Input(width, name); Output(width, name)
Wire(width, name);  Reg(width, name, init_value=0)
Memory(width, depth, name, init_data=None)
Array(width, depth, name)

# Assignment
signal <<= expr         # Reg: non-blocking; Wire/Output: continuous

# Expressions
a + b, a - b, a * b    # Arithmetic
a & b, a | b, a ^ b    # Bitwise
~a                      # Bitwise NOT
a << n, a >> n          # Shift
a == b, a != b, <, >    # Comparison
a[hi:lo]                # Bit-slice
a[idx]                  # Bit-select
Cat(a, b, ...)          # Concatenation
Rep(sig, n)             # Replication
Mux(cond, t, f)         # 2:1 mux
Const(val, width=n)     # Constant
REDUCE_AND(a)           # &a (reduction AND)
LOGIC_AND(a, b)         # a && b
clog2(x)                # $clog2(x)

# Control flow
with If(cond): ...; with Elif(cond): ...; with Else(): ...
with Switch(expr, kind="case") as sw: sw.case(v): ...; sw.default(): ...
with Switch(kind="casez"): ...   # casez statement
with ForGen("i", start, end): ... # generate-for
```

### Simulator API

```python
Simulator(module, use_xz=False, clock_period_ns=10.0)

sim.set(name, value)            # Set input signal
sim.get_int(name) → int         # Read signal value
sim.step()                      # Advance one clock cycle
sim.reset(rst, cycles=2)        # Reset sequence
sim.assert_eq(name, expected)   # Assert signal value
sim.peek_memory(name, addr)     # Read memory
sim.poke_memory(name, addr, v)  # Write memory
```

### ArchSimulator API

```python
ArchSimulator(arch_definition)

sim.run(num_cycles, init_inputs={})  # Run N cycles
sim.step()                            # Single step
sim._signals["pe.signal"]            # Read signal
sim._build_report()                   # Build report
```

### PPAAnalyzer API

```python
PPAAnalyzer(module, tech_node="7nm")

pa.analyze_static()
  → {"logic_depth": {...}, "gate_count": 394.0,
     "reg_bits": 96, "fanout_report": {...}, ...}
pa.analyze_dynamic(sim, n_cycles=100)
  → {"toggle_rates": {...}, "power_hotspots": [...]}
pa.suggest_optimizations()
  → ["[时序] ...", "[面积] ..."]
pa.report(sim=sim)  → str
```
