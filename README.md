# EDACraft

A comprehensive EDA (Electronic Design Automation) toolkit collection for digital and analog IC design.

## Overview

EDACraft is a monorepo hosting multiple EDA sub-projects, each focusing on different aspects of the chip design flow. The goal is to provide an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimization.

## Sub-projects

### [RTLCraft / rtlgen](RTLCraft/README.md) (`RTLCraft/`)

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

- [RTLCraft README](RTLCraft/README.md)
- [中文 README](RTLCraft/README_CN.md)
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

- **Device Templates**: MOSFET, FinFET, GAA nanosheet, TFET, heterojunction TFET, FeFET/NC-FET, tunnel diode (NDR), Dirac-source FET, PN junction, BSPDN GAA, and **AlScN+MoS₂ FeFET**.
- **Multi-Physics Solver**: 3D finite-difference Poisson, drift–diffusion with Scharfetter–Gummel, adaptive Gummel and Newton–Raphson solvers, density-gradient quantum correction, band-to-band tunneling (local Kane + non-local WKB), and self-heating.
- **Ferroelectric Models**: Three models for NC-FET/FeFET simulation:
  - **Landau-Khalatnikov** (vector 3-component P, per-component branch continuation + spinodal switching, [-Ps,+Ps] saturation clamp)
  - **Preisach** (classical scalar play-operator, parameterised directly by Ps/Ec)
  - **NLS** (Nucleation-Limited Switching, Merz-law τ(E)=τ₀·exp(E₀/|E|), finite-slope S-shaped loop for wurtzite ferroelectrics like AlScN)
  - **Material-driven FE detection** (fe_alpha≠0, not dielectric-constant window) — correctly identifies AlScN (ε_r≈15)
  - **Internal/imprint field** (E_bi offset for ±loop asymmetry)
  - **Depolarization field** (E_dep = -P/(ε_fe·ε₀) for correct thickness-window scaling)
- **Correct div(P) coupling**: Central-difference divergence stencil verified by physical-truth tests (prevents P pinning / divergence bugs).
- **Leakage & Trap Models**: Poole-Frenkel + Fowler-Nordheim leakage current, interface traps (Dit) and bulk oxide traps (Q_ot) with charge injection into Poisson equation.
- **Reliability Simulation**: Retention characteristics (polarization decay monitoring), endurance (field-dependent fatigue/breakdown model), pulse-width sweep (switching speed), and single-operation energy measurement.
- **Cryo & Heterogeneous Models**: Temperature-dependent mobility, Fermi–Dirac statistics, freeze-out, and spatially varying effective DOS / bandgap.
- **Mesh & Visualization**: Structured Cartesian grids, Gmsh unstructured tetrahedral meshes, adaptive refinement, and academic-style matplotlib / PyVista visualization with P-V/P-E loop, Id-Vg transfer, and PUND pulse plotters (with correct log-scale formatting).
- **Post-Processing**: Real terminal-current extraction via Scharfetter-Gummel edge flux, band-diagram cutlines, TFET / NDR metrics, mechanism attribution, trust gates, discovery metrics (`Ion`, `Ioff`, `SS`, `Vth`, `DIBL`), and P-V/P-E loop drivers.
- **Device Discovery**: Evolvable device grammar, mutation operators, and NSGA-II-style search loop.
- **Physics Invariant Checks**: Runtime checks (|P|≤Ps, n/p≥0, potential bounds, stencil correctness, material unit consistency) and physical-truth tests that encode inviolable physics laws.
- **Pre-commit Quality Gate**: Automated physics + regression test suite (59 tests, 21 s) runs before every git commit via pre-commit hook.
- **Validation Framework**: Systematic verification strategy set for new physics development including grid convergence, conservation laws, symmetry, limiting cases, boundedness, cross-validation, and sensitivity analysis.
- **Solver Backends**: Dense direct LU for small grids and optional PETSc direct LU for larger grids.

Key directories under `TCADCraft/`:

- `src/` — Extended-precision C++ solver core (Poisson, Gummel, Newton, ferroelectric, leakage, traps)
- `tcad/` — Python package (geometry, materials, mesh, solver bindings, post-processing, search, knowledge, visualization, validation, **physics invariants**)
- `examples/` — Runnable device examples (AlScN PUND, AlScN+MoS₂ FeFET, FinFET/GAA, MOSFET I-V)
- `tests/` — Comprehensive test suite (**59 tests** including 11 physical-truth, 32 FE regression, 16 FE validation)
- `scripts/` — Pre-commit physics check + git hook
- `setup.py` / `pyproject.toml` / `CMakeLists.txt` — Build configuration

See [TCADCraft/README.md](TCADCraft/README.md) for installation and usage details.


### MoMCraft (`MoMCraft/`)

A Method of Moments (MoM) electromagnetic solver for extracting S-parameters of
3D interconnect structures — microstrip lines, multilayer substrates, through-
silicon vias (TSVs), microbumps, and **UCIe (Universal Chiplet Interconnect
Express)** packages — across the 0–60 GHz band. MoMCraft provides:

- **Layered-medium dyadic Green's function**: spectral TM/TE reflection with
  S-matrix recursion, QWE Sommerfeld integration, two-level Aksun tail
  extraction, and surface-wave pole extraction (Chew search + Hankel domain).
- **RWG basis functions** on triangular meshes for arbitrary planar and 3D
  conductor surfaces, including **vertical-current support** for vias/TSVs.
- **Two solver backends**: dense direct LU for small problems and
  preconditioned FFT (pFFT) + GMRES for O(N log N) on large meshes.
- **Schur N-port reduction** and Z→S conversion for multi-port extraction.
- **High-level Python API**: `Microstrip`, `Structure`, `FreqSweep`, and
  Touchstone 2.0 `.sNp` read/write.
- **gmsh-based meshing**: rectangles, cylinder surfaces (TSV), vias with pads,
  traces, and a built-in 32-bit UCIe structure builder.
- **OpenMP parallelization** for matrix assembly and frequency sweeps.

Key directories under `MoMCraft/`:

- `core/` — C++17 solver core (Green's function, RWG assembly, solvers, sweep)
- `bindings/` — pybind11 Python bindings (`_mom` extension)
- `py/mom/` — Python package (high-level API + gmsh meshing + Touchstone I/O)
- `examples/` — Runnable end-user examples
- `tests/` — pytest smoke tests
- `docs/` — Design notes (UCIe, vertical current, multi-port plan)

Quick start:

```bash
cd MoMCraft
pip install -e .          # builds the C++ _mom extension (needs CMake + C++17)
python examples/run_touchstone_demo.py
```

See [MoMCraft/README.md](MoMCraft/README.md) for the full API and
[MoMCraft/使用说明.md](MoMCraft/使用说明.md) for the Chinese tutorial.


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
