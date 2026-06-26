# rtlgen

`rtlgen` is a Python toolkit for designing, simulating, verifying, and emitting
RTL from a white-box hardware DSL.

This release is published under the package name `rtlgen`. The historical
`skills/` and `tools/` trees are not part of the release package. The release
focuses on a small, inspectable, engineer-controlled flow rather than a large
prompt or workflow framework.

## Design Philosophy

### White-Box RTL, Not Black-Box HLS

`rtlgen` is not a C-to-gates compiler and not an opaque HLS engine. A design is
authored as a Python object graph:

1. ports are explicit `Input` / `Output` objects
2. state is explicit `Reg`, `Array`, or `Memory`
3. control flow is explicit `If`, `Else`, `Switch`, and sequential blocks
4. hierarchy is explicit submodule instantiation and port mapping
5. emitted RTL is derived from the same structure used for simulation,
   diagnostics, verification, and PPA analysis

The central idea is simple: hardware should be executable early and inspectable
at every step. When something fails, users should be able to see the authored
DSL, the lowered executable model, the generated RTL, and the diagnostic source
location without guessing what a hidden compiler decided.

### Semantics First

The recommended flow is semantics-first:

```text
DSL Module
  -> authoring-intent validation
  -> lowering / flattening
  -> Python simulator
  -> compiled C++ simulator
  -> emitted SystemVerilog
  -> local RTL simulator smoke / closure
  -> PPA and verification reports
```

This flow makes it cheap to catch design errors before spending time in a full
RTL toolchain. The Python simulator is used for fast debug, the compiled
simulator is used for higher-throughput parity, and emitted RTL is checked with
local tools such as `iverilog`, `verilator`, or a locally installed `vcs`.

### Agent-Friendly, Engineer-Controlled

`rtlgen` is designed to work well with coding agents, but the contract is still
engineering-first:

1. design-visible objects must be registered on the module
2. signedness must be explicit when it matters
3. unsupported storage or backend contracts fail fast
4. diagnostics include stable rule names and source locations where possible
5. generated collateral is reviewable text, not a hidden side effect

The agent can write, inspect, and revise the design, but the user keeps the
same code and reports that a human RTL engineer would expect.

## What Is In This Release

The release package is centered on `rtlgen`, the clean-core RTL toolkit.

```text
rtlgen/
  archsim/   early architecture models, workloads, sweeps, bottleneck reports
  dsl/       hardware DSL, lowering, Verilog emitter, lint/readability helpers
  sim/       Python runtime, compiled C++ backend, trace, parity, cosim
  verify/    directed tests, streaming checks, Python-UVM, SV/UVM collateral
  ppa/       structural/runtime PPA analysis, calibration, recommendations
  tests/     regression coverage for the clean-core stack

jpeg_decoder/
  dsl_modules.py
  README.md
  tests/
```

The release intentionally excludes:

1. `skills/`
2. `tools/`
3. legacy prompt/workflow experiments
4. temporary generated probes and simulator build directories
5. network-login simulator helpers and environment-specific farm scripts

VCS usage in the release documentation assumes a local VCS installation. Users
without VCS can still use Python simulation, the compiled C++ backend,
`iverilog` compile smoke checks, and `verilator` where available.

## DSL Overview

### Minimal Module

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

### Core Authoring Features

`rtlgen.dsl` supports the current stable authoring subset:

1. modules, ports, wires, registers, arrays, and memories
2. combinational, sequential, latch, and initialization blocks
3. `If` / `Else` / `Elif`, `Switch`, `Mux`, concatenation, slices, and part
   selects
4. explicit signed and unsigned intent through `.as_sint()` and `.as_uint()`
5. arithmetic shift helpers such as `SRA(...)` and fixed-point
   `RoundShiftRight(...)`
6. module-owned ROM/LUT initialization through `init_data` and `init_file`
7. explicit submodule instantiation and parent-owned stage handoff wires
8. clock/reset domain declarations and multi-clock executable stepping
9. CDC-oriented primitives and report-oriented CDC checks
10. SystemVerilog emission for the supported subset

### Authoring Rules That Matter

These rules are deliberately enforced because they prevent silent mismatches
between Python, C++, emitted RTL, and external tools:

1. Do not write `if signal:` in Python. Use `with If(signal):`.
2. Do not use Python `and` / `or` / `not` on DSL values. Use bitwise `&`, `|`,
   `~`, or `Mux`.
3. Register design-visible objects on `self`, for example
   `self.tmp = Wire(...)`, `self.buf = Array(...)`, and
   `self.mem = Memory(...)`.
4. Keep submodule `port_map` keys identical to the child module's declared
   port names.
5. Use `.as_sint()` before signed multiply, compare, or clip operations.
6. Use `RoundShiftRight(...)` for signed fixed-point round-then-shift logic.
7. Treat ROM `init_data` and `init_file` as part of the design semantics.

## Tool Capabilities

### Simulation

`rtlgen` provides two primary executable paths:

1. `PythonSimulator` for fast debug and source-level observability
2. the compiled C++ backend for higher-throughput parity and regression runs

The usual pattern is:

```python
from rtlgen.dsl import lower_dsl_module_to_sim, build_compiled_simulator_from_dsl
from rtlgen.sim import PythonSimulator

module = Accumulator()
py_sim = PythonSimulator(lower_dsl_module_to_sim(module).module)
cpp_sim = build_compiled_simulator_from_dsl(module)
```

### Verilog / SystemVerilog Emission

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(Accumulator())
```

The emitter performs boundary checks and fails fast for unsupported contracts.
Current local backend guidance:

1. use Python/C++ simulation first for semantic debug
2. use `iverilog -g2012` as a lightweight compile smoke check
3. use `verilator` for stronger local emitted-RTL closure
4. use local `vcs` when your environment provides it and you need project-style
   simulator behavior

Network-login simulator flows are not part of the release documentation.

### Verification

The verification package is DSL-facing. It includes:

1. directed step-vector tests
2. streaming checks
3. Python-UVM style sequence execution
4. SV/UVM collateral generation
5. generated reference model smoke checks
6. CDC and reset-release reports

The intent is to reuse the same executable DSL semantics across local testing,
generated reference models, and exported verification collateral.

### PPA And Architecture Exploration

`rtlgen.archsim` helps explore bandwidth, latency, capacity, queue-depth, and
workload bottlenecks before detailed RTL is final.

`rtlgen.ppa` analyzes detailed modules and reports structural pressure such as
register bits, combinational expression pressure, storage use, and rewrite
opportunities. It is a first-pass engineering aid, not a replacement for final
synthesis signoff.

## Recommended RTL Design Method

Use `rtlgen` as an executable RTL design loop:

1. Write a small behavior/reference model for expected transactions.
2. Author a DSL module with explicit ports, state, storage, and hierarchy.
3. Run Python simulation with focused tests.
4. Run compiled simulation for parity and speed.
5. Emit RTL and run local compile smoke.
6. Add verification collateral only after the executable path is stable.
7. Run PPA analysis to identify structural hotspots.
8. Refactor the DSL, rerun the same tests, and keep the loop short.

For a concrete JPEG-style datapath example, see:

1. [jpeg_decoder/README.md](./jpeg_decoder/README.md)
2. [rtlgen/JPEG_DATAPATH_COOKBOOK.md](./rtlgen/JPEG_DATAPATH_COOKBOOK.md)

The JPEG example demonstrates signed fixed-point IDCT, LUT-backed MACs,
transpose/reorder buffers, parent-owned stage handoff wires, Python/C++
simulation parity, and emitted RTL smoke checks.

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

Still deliberate fail-fast or limited:

1. broad arbitrary multi-port memory contracts
2. arbitrary non-zero read latency storage in emitted RTL
3. unconstrained macro mapping
4. proving arbitrary CDC protocols from generic logic
5. treating `iverilog` as final correctness signoff for all SystemVerilog

## Documentation

Release entry points:

1. [README_CN.md](./README_CN.md) - Chinese README
2. [Tutorial.md](./Tutorial.md) - English best-practice tutorial
3. [Tutorial_CN.md](./Tutorial_CN.md) - Chinese best-practice tutorial
4. [rtlgen/DSL_SEMANTICS.md](./rtlgen/DSL_SEMANTICS.md)
5. [rtlgen/DSL_SUPPORT_MATRIX.md](./rtlgen/DSL_SUPPORT_MATRIX.md)
6. [rtlgen/STDLIB_SUPPORT_MATRIX.md](./rtlgen/STDLIB_SUPPORT_MATRIX.md)
7. [rtlgen/JPEG_DATAPATH_COOKBOOK.md](./rtlgen/JPEG_DATAPATH_COOKBOOK.md)
8. [rtlgen/MIXED_DESIGN_COSIM_GUIDE.md](./rtlgen/MIXED_DESIGN_COSIM_GUIDE.md)

All user-facing examples use the release package name `rtlgen`.

## License

The framework code is released under the repository license. This release does
not include the historical `skills/` reference-design library.
