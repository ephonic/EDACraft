# rtlgen

English | [中文](README_CN.md)

`rtlgen` is a Python toolkit for RTL design, simulation, verification, and
SystemVerilog generation. It is the clean-core RTLCraft release package in this
repository.

This release uses `rtlgen` as the public package name. The previous
`rtlgen_x` name is retired from user-facing documentation. Historical
`skills/`, `tools/`, remote-login simulator helpers, generated probes, and
project-specific experiments are not part of the release surface.

## Design Philosophy

### White-box RTL instead of black-box HLS

`rtlgen` is not a C-to-gates compiler and not an opaque HLS system. Designs are
authored as explicit Python object graphs:

1. ports are explicit `Input` and `Output` objects
2. state is explicit `Reg`, `Array`, or `Memory`
3. control flow is explicit `If`, `Else`, `Switch`, and sequential blocks
4. hierarchy is explicit submodule instantiation and port mapping
5. generated RTL comes from the same structure used for simulation,
   diagnostics, verification, and PPA analysis

The goal is to keep hardware executable early and inspectable at every step.
When a design fails, users should be able to inspect the authored DSL, the
lowered executable model, the generated RTL, and the diagnostic source location
without guessing what a hidden compiler did.

### Semantics first

The recommended loop is:

```text
DSL module
  -> authoring-intent checks
  -> lowering and inspection
  -> Python simulation
  -> compiled C++ simulation
  -> SystemVerilog emission
  -> local RTL simulator smoke checks
  -> verification and PPA reports
  -> DSL refinement
```

Python simulation gives fast source-level debug. The compiled C++ backend gives
higher-throughput parity and regression. Generated RTL is then checked with
local tools such as `iverilog`, `verilator`, or a locally installed `vcs`.

### Agent-friendly, engineer-controlled

`rtlgen` is designed to work well with coding agents, but the contract remains
engineering-first:

1. design-visible objects are registered on the module
2. signedness is explicit when it matters
3. unsupported storage or backend contracts fail fast
4. diagnostics use stable rule names and source locations where possible
5. generated collateral is reviewable text

An agent can write, inspect, and revise the DSL, while the user keeps ordinary
RTL engineering artifacts: code, tests, generated RTL, verification collateral,
and reports.

## Repository Layout

The RTLCraft release directory is intentionally small:

```text
RTLCraft/
  README.md
  README_CN.md
  rtlgen/
    archsim/   early architecture models, workloads, sweeps, bottleneck reports
    dsl/       hardware DSL, lowering, Verilog emitter, lint/readability helpers
    sim/       Python runtime, compiled C++ backend, trace, parity, cosim
    verify/    directed checks, streaming checks, Python-UVM, SV/UVM collateral
    ppa/       structural/runtime PPA analysis, calibration, recommendations
    tests/     clean-core regression coverage
```

`RTLCraft/rtlgen/README.md` is intentionally not used. The GitHub-facing
README lives here at `RTLCraft/README.md`, and the package itself lives under
`RTLCraft/rtlgen/`.

## Quick Start

From the repository root:

```bash
PYTHONPATH=RTLCraft python - <<'PY'
import rtlgen
print("rtlgen import ok")
PY
```

From the `RTLCraft/` directory:

```bash
PYTHONPATH=. python - <<'PY'
import rtlgen
print("rtlgen import ok")
PY
```

The release is source-checkout friendly. A local simulator is optional for many
flows: Python simulation, compiled C++ simulation, DSL linting, verification
helpers, and PPA reports can be used before running external RTL tools.

## DSL Overview

### Minimal module

```python
from rtlgen.dsl import Else, If, Input, Module, Output, Reg


class Accumulator(Module):
    def __init__(self, width=16):
        super().__init__("Accumulator")
        self.clk = Input(1, "clk")
        self.rst = Input(1, "rst")
        self.en = Input(1, "en")
        self.x = Input(width, "x")
        self.y = Output(width, "y")

        self.acc = Reg(width, "acc")

        with self.seq(self.clk, self.rst):
            with If(self.rst == 1):
                self.acc <<= 0
            with Else():
                with If(self.en == 1):
                    self.acc <<= self.acc + self.x

        with self.comb:
            self.y <<= self.acc
```

### Stable authoring features

Current DSL coverage includes:

1. modules, ports, wires, registers, arrays, and memories
2. combinational, sequential, latch, and initialization blocks
3. `If` / `Else` / `Elif`, `Switch`, `Mux`, concatenation, slices, and part
   selects
4. explicit signed and unsigned intent through `.as_sint()` and `.as_uint()`
5. arithmetic shift and fixed-point helpers such as `SRA(...)` and
   `RoundShiftRight(...)`
6. ROM/LUT initialization through `init_data` and `init_file`
7. explicit submodule instantiation and parent-owned stage handoff wires
8. clock/reset domain declarations and multi-clock executable stepping
9. CDC-oriented primitives and report-oriented CDC checks
10. SystemVerilog emission for the supported subset

### Authoring rules that matter

These rules are enforced because they prevent silent mismatches between Python,
C++, emitted RTL, and external tools:

1. Do not write Python `if signal:` on DSL values. Use `with If(signal):`.
2. Do not use Python `and`, `or`, or `not` on DSL values. Use `&`, `|`, `~`,
   or `Mux`.
3. Register design-visible objects on `self`, for example
   `self.tmp = Wire(...)`, `self.buf = Array(...)`, and
   `self.mem = Memory(...)`.
4. Keep submodule `port_map` keys identical to the child module port names.
5. Use `.as_sint()` before signed multiply, compare, clip, or fixed-point
   operations where signed intent matters.
6. Treat ROM `init_data` and `init_file` as design semantics.

## Tool Capabilities

### Simulation

`rtlgen` provides two executable paths:

1. `PythonSimulator` for fast debug and source-level observability
2. compiled C++ simulation for higher-throughput parity and regression

Typical setup:

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl, lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

module = Accumulator()
py_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
cpp_sim = build_compiled_simulator_from_dsl(module)
```

### SystemVerilog generation

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Accumulator())
```

Use emitted RTL with local tools:

1. `iverilog -g2012` for lightweight compile smoke checks
2. `verilator` for stronger local RTL closure
3. local `vcs` when your site provides it and project-style simulation is
   needed

Remote-login VCS workflows are intentionally excluded from this release.

### Verification

The verification package is DSL-facing and includes:

1. directed step-vector tests
2. streaming checks
3. Python-UVM style sequence execution
4. SV/UVM collateral generation
5. generated reference-model smoke checks
6. CDC and reset-release reports

The intent is to reuse the same executable DSL semantics across local testing,
reference models, and exported verification collateral.

### PPA and architecture exploration

`rtlgen.archsim` helps explore bandwidth, latency, capacity, queue depth, and
workload bottlenecks before detailed RTL is final.

`rtlgen.ppa` analyzes detailed modules and reports structural pressure such as
register bits, combinational expression pressure, storage use, and rewrite
opportunities. It is an early engineering aid, not a replacement for final
synthesis signoff.

## Recommended RTL Design Method

Use `rtlgen` as a short executable design loop:

1. Write a small behavior or reference model for expected transactions.
2. Author a DSL module with explicit ports, state, storage, and hierarchy.
3. Run Python simulation with focused tests.
4. Run compiled simulation for parity and speed.
5. Emit SystemVerilog and run local compile smoke.
6. Add verification collateral after the executable path is stable.
7. Run PPA analysis to identify structural hot spots.
8. Refactor the DSL and rerun the same tests.

For deeper flows, start with:

1. [Architecture exploration to PPA tutorial](rtlgen/TUTORIAL_ARCH_PPA.md)
2. [DSL to local UVM tutorial](rtlgen/TUTORIAL_UVM.md)
3. [JPEG datapath cookbook](rtlgen/JPEG_DATAPATH_COOKBOOK.md)
4. [Mixed design cosimulation guide](rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

## Current Capability Boundaries

Stable and recommended today:

1. single-clock synchronous control and datapath modules
2. explicit multi-clock execution with declared domains
3. module-owned arrays and memories in the supported storage subset
4. ROM/LUT `init_data` and `init_file` semantics
5. signed fixed-point arithmetic with explicit signed intent
6. hierarchical composition through explicit parent-owned interconnect
7. local Python/C++ simulation and local RTL backend smoke/closure
8. report-oriented CDC, verification, and PPA flows

Limited or deliberate fail-fast areas:

1. broad arbitrary multi-port memory contracts
2. arbitrary non-zero read-latency storage in emitted RTL
3. unconstrained macro mapping
4. proving arbitrary CDC protocols from generic logic
5. treating `iverilog` as final correctness signoff for all SystemVerilog

## Documentation

Core documentation:

1. [中文 README](README_CN.md)
2. [DSL semantic contract](rtlgen/DSL_SEMANTICS.md)
3. [DSL support matrix](rtlgen/DSL_SUPPORT_MATRIX.md)
4. [Standard-library support matrix](rtlgen/STDLIB_SUPPORT_MATRIX.md)
5. [Architecture exploration to PPA tutorial](rtlgen/TUTORIAL_ARCH_PPA.md)
6. [DSL to local UVM tutorial](rtlgen/TUTORIAL_UVM.md)
7. [JPEG datapath cookbook](rtlgen/JPEG_DATAPATH_COOKBOOK.md)
8. [Mixed design cosimulation guide](rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

## License

The framework code follows the repository license. This release does not
include the historical `skills/` reference-design library.
