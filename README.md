# EDACraft

A comprehensive EDA (Electronic Design Automation) toolkit collection for digital and analog IC design.

## Overview

EDACraft is a monorepo hosting multiple EDA sub-projects, each focusing on different aspects of the chip design flow. The goal is to provide an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimization.

## Sub-projects

### RTLCraft / rtlgen (`RTLCraft/`)

RTLCraft now publishes its clean-core RTL toolkit as `rtlgen`. The release
replaces the historical `rtlgen_x` naming in the public package and removes the
old `skills/` and `tools/` trees from the release surface.

`rtlgen` is a Python toolkit for designing, simulating, verifying, and emitting
RTL from a white-box hardware DSL. It is not an opaque HLS compiler: ports,
wires, registers, memories, control flow, hierarchy, reset behavior, and
signedness are all explicit in user code. The same design structure is reused
for semantic checks, Python simulation, compiled C++ simulation,
SystemVerilog generation, verification collateral, and PPA analysis.

Recommended RTL design loop:

```text
DSL module
  -> authoring-intent checks
  -> Python simulation
  -> compiled C++ simulation
  -> SystemVerilog emission
  -> local RTL simulator smoke checks
  -> verification and PPA reports
```

RTLCraft provides:

- **White-box Python DSL**: Explicit modules, ports, wires, registers,
  arrays, memories, combinational blocks, sequential blocks, hierarchy,
  signed/unsigned intent, fixed-point helpers, ROM/LUT initialization, CDC
  primitives, and SystemVerilog emission for the supported subset.
- **Executable semantics**: Fast Python simulation for debug and compiled C++
  simulation for higher-throughput parity and regression.
- **Local RTL closure**: Generated RTL can be checked with local tools such as
  `iverilog`, `verilator`, or a locally installed `vcs`; remote-login VCS
  helper scripts are not part of the release documentation.
- **Verification support**: Directed tests, streaming checks, Python-UVM style
  execution, SV/UVM collateral generation, reference-model smoke checks, and
  CDC/reset-release reports.
- **PPA and architecture exploration**: Early architecture sweeps plus
  structural/runtime PPA reports to guide rewrite opportunities before final
  signoff.

Key RTLCraft documentation:

- [DSL semantics](RTLCraft/rtlgen/DSL_SEMANTICS.md)
- [DSL support matrix](RTLCraft/rtlgen/DSL_SUPPORT_MATRIX.md)
- [Standard-library support matrix](RTLCraft/rtlgen/STDLIB_SUPPORT_MATRIX.md)
- [Architecture and PPA tutorial](RTLCraft/rtlgen/TUTORIAL_ARCH_PPA.md)
- [UVM tutorial](RTLCraft/rtlgen/TUTORIAL_UVM.md)

Key directories under `RTLCraft/`:

- `rtlgen/` — DSL, code generation, simulation, verification, PPA, and
  architecture exploration.

Quick start:

```bash
PYTHONPATH=RTLCraft python - <<'PY'
import rtlgen
print("rtlgen import ok")
PY
```


### EDACode (`EDACode/`)

An AI-powered EDA code platform for analog/mixed-signal IC design. EDACode provides:

- **Natural Language Design**: Interactive chat interface for describing and modifying circuit designs using plain English.
- **LLM Agent Framework**: Tool-augmented AI agent that can read/write schematics, run simulations, manage designs, and execute bash commands.
- **VSCode Integration**: Full-featured sidebar extension with chat panel, tool visualization, file edit integration, and terminal control.
- **Multi-Provider LLM Support**: OpenAI, Anthropic, and any OpenAI-compatible proxy (Ollama, vLLM, etc.).
- **Context Management**: Automatic context compaction, budget tracking, and design state persistence.
- **Circuit Harness**: One-click validation workflows including netlist check, DRC, LVS, and simulation.

Key directories under `EDACode/`:

- `src/eda_agent/` — Python agent core, tools, providers, and server
- `vscode-extension/` — TypeScript VSCode extension (chat UI, process management)
- `tests/` — Unit tests for agent components and server integration


### TCADCraft (`TCADCraft/`)

A Python-driven 3D quantum-corrected semiconductor device simulator for nanoscale TCAD analysis. TCADCraft provides:

- **Device Templates**: MOSFET, FinFET, GAA nanosheet, TFET, heterojunction TFET, FeFET/NC-FET, tunnel diode (NDR), Dirac-source FET, PN junction, and BSPDN GAA.
- **Multi-Physics Solver**: 3D finite-difference Poisson, drift–diffusion with Scharfetter–Gummel, adaptive Gummel and Newton–Raphson solvers, density-gradient quantum correction, band-to-band tunneling (local Kane + non-local WKB), ferroelectric Landau–Khalatnikov model, and self-heating.
- **Cryo & Heterogeneous Models**: Temperature-dependent mobility, Fermi–Dirac statistics, freeze-out, and spatially varying effective DOS / bandgap.
- **Mesh & Visualization**: Structured Cartesian grids, Gmsh unstructured tetrahedral meshes, adaptive refinement, and matplotlib / PyVista visualization.
- **Post-Processing**: Terminal-current extraction, band-diagram cutlines, TFET / NDR metrics, mechanism attribution, trust gates, and discovery metrics (`Ion`, `Ioff`, `SS`, `Vth`, `DIBL`).
- **Device Discovery**: Evolvable device grammar, mutation operators, and NSGA-II-style search loop.
- **Solver Backends**: Dense direct LU for small grids and optional PETSc direct LU for larger grids.

Key directories under `TCADCraft/`:

- `src/` — Extended-precision C++ solver core
- `tcad/` — Python package (geometry, materials, mesh, solver bindings, post-processing, search, knowledge, visualization)
- `examples/` — Runnable device examples
- `setup.py` / `pyproject.toml` / `CMakeLists.txt` — Build configuration

See [TCADCraft/README.md](TCADCraft/README.md) for installation and usage details.


### CktCraft (`CktCraft/`)

A compact SPICE-style RF / analog circuit simulator with large-signal MOSFET periodic steady-state (Shooting-Newton + FFT harmonic extraction) and OSDI compact-model integration. CktCraft provides:

- **Multi-Analysis Solver**: DC operating point (Newton + gmin homotopy + source-stepping + mid-rail seeding), DC sweep, small-signal AC, Harmonic Balance (linear analytic + nonlinear HB-NL with GMRES), and Periodic Steady State (Shooting-Newton with DFT harmonic extraction).
- **Sparse Direct Solver**: SuiteSparse-KLU (BTF + AMD + partial pivoting) for DC / transient / shooting Newton steps; complex KLU for AC.
- **OSDI Compact Models**: OpenVAF/OSDI 0.3 & 0.4 dual-ABI support for BSIM4, BSIM-SOI, BSIM-CMG, EKV, diode, and Shichman-Hodges MOSFET, with internal-node collapse and cross-CRT heap alignment.
- **S-Parameter Devices**: N-port Touchstone `.sNp` parsing, S→Y conversion, Vector Fitting (Gustavsen two-stage pole relocation) for Backward-Euler transient companion models.
- **DC Convergence Homotopy**: Log-spaced gmin scheduling, source-stepping, resistor-graph BFS mid-rail seed propagation, and gmin floor-accept for hostile operating points.
- **SPICE Parser**: Token + AST + flattening with `.param`, `.subckt`, `.model`, `.options`, SPICE unit suffixes, and error-recovery diagnostics.

Key directories under `CktCraft/`:

- `src/` — Core library (parser, circuit, model, assembly, solver, sparam, output)
- `tests/` — GoogleTest unit tests (22 suites, 111 tests)
- `models/` — Precompiled OSDI models (`.dll` + `.va` sources)
- `tools/` — OpenVAF compiler + waveform viewer + bench summarizer
- `netlists/` — Example SPICE netlists (DC, AC, PSS, S-parameter, RF circuits)

See [CktCraft/README.md](CktCraft/README.md) for usage and [CktCraft/Development_guide.md](CktCraft/Development_guide.md) for architecture and development (including OpenVAF Linux build instructions).


### ImplCraft (`ImplCraft/`)

A Python-driven IC backend design automation framework. ImplCraft wraps commercial EDA tools (Design Compiler, ICC2, PrimeTime, Calibre) behind a unified Python API, orchestrates the full synthesis → physical implementation → sign-off pipeline, and enables AI agents to reason over structured QoR data. ImplCraft provides:

- **Tool Adapter Layer**: Python wrappers for Design Compiler (synthesis), ICC2 (floorplan / placement / CTS / routing), PrimeTime (STA), and Calibre (DRC / LVS) with automatic Tcl script generation and report parsing.
- **Unified Design State**: A single data model carrying timing, area, power, routing, DRC, and LVS metrics through every pipeline stage — serializable to JSON for persistence and agent consumption.
- **Flow Orchestrator**: Dependency-aware stage execution with dry-run mode, stop-at / resume-from, automatic metric logging, and flow summary reporting.
- **Report Parsers**: Deep extraction from DC QoR, ICC2 timing/congestion/utilization, PrimeTime STA, and Calibre DRC/LVS reports into structured dataclasses.
- **QoR Analyzer**: Cross-stage regression detection (WNS / TNS / utilization) with automated diagnostic recommendations.
- **Design Partition System**: Hierarchical analysis for designs exceeding tool capacity (>4M gates), with intelligent harden/flatten/split decisions and sub-partition advisor.
- **PG Network Advisor**: Power/Ground pad count calculation, placement strategy (uniform/clustered/peripheral/corner), I/O and bond pad placement, IR-drop estimation, and EM checking.
- **Error Checker & RTL Advisor**: Cross-tool error/warning detection, RTL modification suggestions based on timing analysis, and design rule validation.
- **YAML-Driven Config**: One YAML file describes the design, PDK, libraries, RTL, and flow options — no scattered Tcl variables.

Key directories under `ImplCraft/`:

- `src/tools/` — Tool adapters (DC, ICC2, PT, Calibre) with Tcl script generation
- `src/parsers/` — Report parsers for each tool's output format
- `src/flow/` — Orchestrator and stage definitions
- `src/analysis/` — QoR analyzer, error checker, RTL advisor, partition system, PG network advisor
- `src/db/` — Design state data model and persistence
- `config/` — Project YAML configuration templates
- `tests/` — 69 pytest tests covering all modules

See [ImplCraft/README.md](ImplCraft/README.md) for installation, usage, and roadmap.


## License

MIT License — see [LICENSE](LICENSE) for details.
