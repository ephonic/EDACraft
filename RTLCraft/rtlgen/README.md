# rtlgen

This directory is the clean-core RTL toolkit published as `rtlgen`.

## What `rtlgen` Provides

`rtlgen` is a compact set of engineering capabilities:

1. `archsim/` for early architecture exploration
2. `dsl/` for executable RTL authoring
3. `sim/` for Python runtime, compiled C++ simulation, trace, parity, and cosim
4. `verify/` for directed tests, streaming checks, Python-UVM, SV/UVM collateral,
   CDC and reset-release reports
5. `ppa/` for structural/runtime PPA analysis and recommendations

The package is intentionally capability-first. It does not require a heavy
document workflow or a skills library. The user or coding agent orchestrates the
loop, while `rtlgen` provides the engines.

The repository also carries a narrow `rtlgen_x` compatibility package for older
seed code. It forwards legacy `rtlgen_x.dsl`, `rtlgen_x.sim`,
`rtlgen_x.archsim`, `rtlgen_x.ppa`, and `rtlgen_x.verify` imports to `rtlgen`.
Prefer `rtlgen` for all new code.

## Design Loop

The detailed-design flow is:

```text
DSL Module
  -> authoring-intent validation
  -> lowering / flattening
  -> LoweredDslModule / SimModule
  -> PythonSimulator
  -> compiled C++ simulator
  -> verification / PPA / emitted RTL / cosim
```

The recommended usage pattern:

1. write a small DSL module with explicit ports and state
2. run Python simulation first
3. add compiled simulation parity
4. emit SystemVerilog with `VerilogEmitter`
5. run local compile smoke or local RTL closure
6. add verification collateral after the executable path is stable
7. use PPA reports to guide structural rewrites

## Foundation Contract Gate

Before promoting a DSL module into stdlib, a worked example, or release-facing
documentation, run the foundation contract gate:

```python
from rtlgen.verify import analyze_foundation_contract, emit_foundation_contract_markdown

report = analyze_foundation_contract(module)
print(emit_foundation_contract_markdown(report))
```

The gate combines review-profile readability, unified diagnostics, CDC/reset
preflight, and storage/lowering/emitted-RTL fail-fast checks. A clean foundation
report means the module passes this engineering preflight; it does not replace
simulation, protocol verification, or external RTL simulator closure.

## Current Package Layout

```text
rtlgen/
  archsim/   architecture simulators, workloads, sweeps, reports
  dsl/       DSL authoring surface, lowering, emitter, lint/readability
  sim/       Python runtime, C++ backend, trace, parity, cosim
  verify/    directed/Python-UVM/SV-UVM/CDC verification helpers
  ppa/       PPA statistics, calibration, report parsing, recommendations
  tests/     regression coverage
```

## DSL Authoring Guidance

The public authoring surface is `rtlgen.dsl.Module`.

Important rules:

1. use `with If(...)`, `with Else():`, `Switch`, and `Mux`; do not use Python
   `if signal:` or Python `and` / `or` / `not` on DSL values
2. register design-visible objects on `self`, for example `self.tmp = Wire(...)`,
   `self.buf = Array(...)`, and `self.mem = Memory(...)`
3. keep explicit submodule `port_map` keys identical to the child module's
   declared port names
4. use `.as_sint()` / `.as_uint()` to make signedness explicit at arithmetic
   boundaries
5. use `SRA(...)` for arithmetic right shift intent and `RoundShiftRight(...)`
   for signed fixed-point round-then-shift
6. treat `Memory(..., init_data=...)` and `Memory(..., init_file=...)` as design
   semantics, not optional simulation hints
7. for stage chaining, connect children through parent-owned wires such as
   `self.mid_data`, `self.mid_valid`, and `self.mid_ready`
8. for multi-clock designs, declare clock/reset domains and use explicit
   domain-aware stepping
9. use CDC helpers such as `SyncCell`, `PulseSynchronizer`, `AsyncResetRel`,
   `AsyncFIFO`, and `ReadyValidAsyncBridge` instead of ad hoc crossings when
   possible

See [DSL_SEMANTICS.md](./DSL_SEMANTICS.md) for the full semantic contract and
[DSL_SUPPORT_MATRIX.md](./DSL_SUPPORT_MATRIX.md) for support boundaries. The
review RTL rules are described in
[RTL_READABILITY_CONTRACT.md](./RTL_READABILITY_CONTRACT.md).

## Simulation

Python simulation:

```python
from rtlgen.dsl import lower_dsl_module_to_sim
from rtlgen.sim import PythonSimulator

lowered = lower_dsl_module_to_sim(module)
sim = PythonSimulator(lowered.module)
```

Compiled simulation:

```python
from rtlgen.dsl import build_compiled_simulator_from_dsl

sim = build_compiled_simulator_from_dsl(module)
```

Use the same vectors on both paths whenever possible.

For old seed code that imports `rtlgen.Simulator`, the top-level package keeps
a narrow `reset/poke/peek/step` compatibility wrapper. New code should prefer
`lower_dsl_module_to_sim(...)` plus `PythonSimulator` or the compiled simulator
path above; the removed AST/JIT simulator and DSL validator surfaces are not
restored.

## RTL Emission And Local Backends

```python
from rtlgen.dsl import EmitProfile, VerilogEmitter

rtl = VerilogEmitter(profile=EmitProfile.review()).emit_design(module)
```

Backend guidance:

1. Python/C++ simulation is the primary semantic closure path
2. `iverilog -g2012` is useful for lightweight compile smoke
3. `verilator` is the preferred open local emitted-RTL closure backend
4. local `vcs` can be used when available and stronger project-style simulator
   behavior is needed

Network-login simulator flows are not part of the release documentation.

## Verification

The verification helpers are DSL-facing. They can consume the original
`Module` or a `LoweredDslModule` and generate:

1. directed step-vector tests
2. streaming tests
3. Python-UVM style sequences
4. generated SV/UVM collateral
5. reference-model smoke checks
6. CDC and reset-release markdown reports

The recommended order is:

1. directed Python simulator checks
2. compiled simulator parity
3. Python-UVM or streaming checks
4. emitted RTL smoke
5. generated SV/UVM collateral

## PPA And Architecture Exploration

`archsim` helps answer early questions about bandwidth, capacity, latency,
queue depth, and bottleneck ranking.

`ppa` analyzes detailed modules and reports structural pressure such as
register bits, memory/storage use, expression pressure, and rewrite
opportunities. It is early engineering feedback, not final synthesis signoff.

## Worked Example: JPEG Datapath

The release includes `jpeg_decoder/` as a worked example.

Start with:

1. [../jpeg_decoder/README.md](../jpeg_decoder/README.md)
2. [JPEG_DATAPATH_COOKBOOK.md](./JPEG_DATAPATH_COOKBOOK.md)

The JPEG example covers:

1. signed fixed-point IDCT
2. LUT-backed MACs
3. transpose and zig-zag reorder buffers
4. parent-owned stage handoff wires
5. Python and compiled simulation parity
6. emitted RTL compile smoke

Recommended rerun:

```bash
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_idct_basic.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_dequant_idct.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_cpp_entropy_dequant.py
PYTHONPATH=. pytest -q jpeg_decoder/tests/test_verilog.py
```

## Mixed DSL + External Verilog

Use [MIXED_DESIGN_COSIM_GUIDE.md](./MIXED_DESIGN_COSIM_GUIDE.md) for local
mixed-design packaging and cosim.

The release policy:

1. package external Verilog sources, include directories, defines, and ROM
   init files together with emitted DUT RTL
2. use local `verilator` as the preferred emitted-RTL closure backend when
   available
3. use local `vcs` only when the user's environment provides it
4. keep `iverilog` as compile smoke / compatibility
5. keep release docs focused on local simulator flows

## Current Boundaries

Stable and recommended:

1. explicit DSL modules and hierarchy
2. module-owned arrays and memories in the supported storage subset
3. ROM/LUT `init_data` and `init_file`
4. signed fixed-point intent with `.as_sint()` and `RoundShiftRight(...)`
5. Python/C++ simulation parity
6. local emitted-RTL smoke / closure
7. report-oriented CDC and PPA

Still limited or fail-fast:

1. arbitrary multi-port memory contracts
2. arbitrary non-zero read-latency emitted RTL
3. broad macro mapping
4. proving arbitrary CDC protocols
5. using `iverilog` as universal final SystemVerilog signoff

## Release Note

The published package name is `rtlgen`; all user-facing examples and imports
should use `rtlgen`.
