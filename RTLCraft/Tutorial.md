# rtlgen Tutorial

This tutorial describes the recommended way to use `rtlgen` for RTL design in
the release package. It focuses on best practices: how to author a small module,
simulate it, emit RTL, debug failures, and grow toward larger datapaths without
losing semantic clarity.

The release package name is `rtlgen`; all examples use that name.

## 1. Mental Model

Think of `rtlgen` as an executable RTL workbench:

```text
reference behavior
  -> DSL module
  -> Python simulation
  -> compiled C++ simulation
  -> emitted SystemVerilog
  -> local RTL simulator smoke / closure
  -> verification and PPA reports
```

Best practice is to keep this loop short. Do not start by generating a large
amount of RTL. Start with one module, one behavior expectation, and one focused
test.

## 2. Write The Smallest Useful Module

Use explicit ports and state. Register every design-visible signal on `self`.

```python
from rtlgen.dsl import Else, If, Input, Module, Output, Reg


class Counter(Module):
    def __init__(self, width=8):
        super().__init__("Counter")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.value = Output(width, "value")

        self.count = Reg(width, "count")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.count <<= 0
            with Else():
                with If(self.en == 1):
                    self.count <<= self.count + 1

        with self.comb:
            self.value <<= self.count
```

Key rules:

1. Use `with If(...)`, not Python `if`.
2. Use `self.count = Reg(...)`, not a host-local `count = Reg(...)`.
3. Put output wiring in a visible comb block.
4. Keep reset behavior obvious.

## 3. Run Python Simulation First

```python
from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

dut = Counter()
sim = PythonSimulator(lower_dsl_module_to_sim(dut).module)

print(sim.step({"clk": 0, "rst": 1, "en": 0}))
print(sim.step({"clk": 0, "rst": 0, "en": 1}))
print(sim.step({"clk": 0, "rst": 0, "en": 1}))
```

Use Python simulation for:

1. reset/debug visibility
2. fast iteration on control logic
3. checking whether DSL authoring intent is accepted by lowering
4. exploring state and output traces before involving external tools

If lowering fails, fix that first. Lowering diagnostics are intentionally part
of the authoring loop.

## 4. Add A Compiled Simulation Parity Check

Once Python simulation is stable, add compiled simulation.

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl

cpp_sim = build_compiled_simulator_from_dsl(Counter())
print(cpp_sim.step({"clk": 0, "rst": 1, "en": 0}))
print(cpp_sim.step({"clk": 0, "rst": 0, "en": 1}))
```

Best practice:

1. keep Python and compiled simulator test vectors identical
2. treat Python-vs-C++ mismatch as a framework/backend bug or signed-width bug
   until proven otherwise
3. use compiled simulation for bigger regressions after Python has made the
   issue easy to localize

## 5. Emit SystemVerilog

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Counter())
print(rtl)
```

Recommended backend order:

1. Python simulation for DSL semantics
2. compiled C++ simulation for parity and speed
3. `iverilog -g2012` for lightweight compile smoke
4. `verilator` for stronger local emitted-RTL closure
5. local `vcs` if your environment provides it and you need project-style
   simulator behavior

The release documentation does not depend on network-login simulator flows. Use
local VCS directly when available.

## 6. Best Practices For Signed Datapaths

Signed fixed-point logic is where hidden assumptions become expensive. Be
explicit.

```python
from rtlgen.dsl import Const, Mux, RoundShiftRight, Wire

self.prod = Wire(32, "prod", signed=True)
self.sum_next = Wire(32, "sum_next", signed=True)
self.scaled = Wire(32, "scaled", signed=True)
self.final = Wire(33, "final", signed=True)
self.clipped = Wire(33, "clipped", signed=True)

with self.comb:
    self.prod <<= self.sample.as_sint() * self.coeff.as_sint()
    self.sum_next <<= self.acc + self.prod
    self.scaled <<= RoundShiftRight(self.sum_next, 14)
    self.final <<= self.scaled.as_sint() + Const(128, 33)
    self.clipped <<= Mux(
        self.final.as_sint() < Const(0, 33).as_sint(),
        Const(0, 33),
        Mux(
            self.final.as_sint() > Const(255, 33).as_sint(),
            Const(255, 33),
            self.final,
        ),
    )
```

Checklist:

1. storage reads that represent signed values should use `.as_sint()` at the
   arithmetic boundary
2. use `RoundShiftRight(...)` instead of relying on plain shift semantics
3. compare signed values as signed values
4. clip before narrowing to the output width
5. keep intermediate signals module-owned so traces and emitted RTL are easy to
   inspect

The JPEG IDCT example in `jpeg_decoder/` is the main release example for this
pattern.

## 7. Best Practices For Storage

Use module-owned `Array` and `Memory` objects.

```python
from rtlgen.dsl import Array, Memory, Wire

self.buf = Array(16, 64, "buf")
self.rom = Memory(16, 64, "rom", init_data=my_table)
self.addr = Wire(6, "addr")
self.data = Wire(16, "data")

with self.comb:
    self.data <<= self.rom[self.addr]
```

Rules:

1. `init_data` and `init_file` are design semantics
2. do not hide tables in host-side Python control flow when emitted RTL needs
   the same content
3. keep address construction visible in wires or registers
4. unsupported storage contracts fail fast; do not treat them as silent
   synthesis hints

Current stable storage is intentionally narrower than a full memory compiler
interface. See `rtlgen/DSL_SUPPORT_MATRIX.md` and `rtlgen/DSL_SEMANTICS.md`.

## 8. Best Practices For Hierarchy

Use explicit parent-owned wires between child stages.

```python
self.mid_data = Wire(16, "mid_data")
self.mid_valid = Wire(1, "mid_valid")
self.mid_ready = Wire(1, "mid_ready")

self.instantiate(stage0, "u_stage0", port_map={
    "out_data": self.mid_data,
    "out_valid": self.mid_valid,
    "out_ready": self.mid_ready,
})

self.instantiate(stage1, "u_stage1", port_map={
    "in_data": self.mid_data,
    "in_valid": self.mid_valid,
    "in_ready": self.mid_ready,
})
```

Do not write temporary local handoff wires inside the constructor and forget to
attach them to `self`. The authoring-intent checker will reject that pattern
because it makes ownership ambiguous during lowering and emission.

## 9. Best Practices For Verification

Start with the smallest deterministic tests:

1. reset behavior
2. one normal transaction
3. one boundary transaction
4. one backpressure or stall transaction if the module has ready/valid
5. one signed or overflow case if the datapath is numeric

Then grow:

1. Python simulator directed tests
2. compiled simulator parity
3. streaming or Python-UVM style checks
4. emitted RTL smoke
5. generated SV/UVM collateral when the executable path is already stable

Keep the same transaction set across layers whenever possible.

## 10. Best Practices For PPA Feedback

Use PPA analysis as an early design review aid:

1. look for wide combinational expressions
2. inspect register/storage growth
3. identify repeated arithmetic or mux structures
4. consider pipeline staging when critical expressions become too deep
5. rerun functional tests after every rewrite

Do not use the PPA report as final signoff. Final timing/area/power still
belongs to your synthesis and implementation flow.

## 11. Worked Example: JPEG Datapath

The release includes a JPEG-style datapath example:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

It demonstrates:

1. signed fixed-point IDCT
2. LUT-backed MACs
3. transpose and zig-zag reorder buffers
4. parent-owned stage handoff wires
5. Python/compiled simulator parity
6. emitted RTL compile smoke

Use `jpeg_decoder/README.md` for rerun order and
`rtlgen/JPEG_DATAPATH_COOKBOOK.md` for reusable datapath patterns.

## 12. Release Checklist For A New Design

Before treating a module as release-ready:

1. Python simulator tests pass
2. compiled simulator parity passes
3. emitted RTL is generated with the review profile
4. local RTL compile smoke passes for the supported subset
5. signed/storage/hierarchy diagnostics are clean
6. relevant support-matrix boundaries are documented
7. README or module notes explain how to rerun the focused tests

That is the practical `rtlgen` loop: keep the design executable, keep the
semantics explicit, and let every tool consume the same authored structure.
