\# EDACraft



A comprehensive EDA (Electronic Design Automation) toolkit collection for digital and analog IC design.



\## Overview



EDACraft is a monorepo hosting multiple EDA sub-projects, each focusing on different aspects of the chip design flow. The goal is to provide an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimization.



\## Sub-projects



\### RTLCraft (`RTLCraft/`)



A Python-to-Verilog RTL generation and verification framework. RTLCraft provides:



\- **Python API for RTL Generation**: Object-oriented, decorator-driven Python DSL for describing synthesizable Verilog / SystemVerilog digital logic.

\- **AST-based Design**: Transparent Abstract Syntax Tree (AST) representation where every `Signal`, `Module`, and `Assign` is an explicit node that can be traversed, modified, and printed.

\- **Built-in Simulation**: Cycle-accurate Python AST interpreter with hierarchical design support, X/Z 4-state logic, multi-clock, and JIT acceleration.

\- **UVM Verification**: Native Python UVM DSL with support for directed/random sequences, coverage collection, and scoreboard-based checking.

\- **Verilog Generation**: Single-module or full-design Verilog / SystemVerilog emission with optional assertions.

\- **Lint & Analysis**: AST-level lint rules (e.g., `seq_output_assign`, `comb_reg_assign`, `unregistered_output`) and Verilog text-level linting.

\- **Synthesis & PPA**: Integration with ABC for synthesis and PPA (Power, Performance, Area) analysis.

A comprehensive EDA (Electronic Design Automation) toolkit collection for digitaKey directories under `RTLCraft/`:

\- `rtlgen/` — Core framework (AST, codegen, simulation, UVM)

\- `examples/` — Design examples (counter, decoder_8b10b, FP8 ALU, etc.)

\- `tests/` — Pytest-based functional and pyUVM test suites

\- `skills/` — Reusable design skills (arithmetic, cryptography, memory, etc.)ffe- `generated_*` — Auto-generated Verilog and UVM testbenches an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimiz### DeviceCraft (`DeviceCraft/`)



A 3D quantum-corrected semiconductor device simulator with an evolutionary design-space exploration engine. DeviceCraft covers:



\- **Multi-Physics Solver**: Gummel-style coupled Poisson–drift-diffusion solver (C++ backend + Python/Cython frontend) with density-gradient quantum correction, thermal coupling, and optical generation.

\- **Tunneling & Ferroelectric Models**: Kane band-to-band tunneling (BTBT) generation for TFETs; Landau–Khalatnikov ferroelectric model with negative-capacitance (NC) gate stacks.

\- **Device Templates**: Parametric generators for MOSFET, FinFET, GAA nanowire, p–n junction, TFET, CFET, and ferroelectric-FET structures.- **Design-Space Evolution**: Analytical TFET evaluator + (μ+λ) NSGA-II style multi-objective optimizer for exploring I_on, I_off, and subthreshold-swing trade-offs; hybrid concept generator (NC-TFET, C-TFET, Fe-CFET).

\- **TCAD Validation Pipeline**: 1-D diode E-field calibration, 3-D transfer-characteristic sweeps, and BTBT self-consistent loops.

\- **Python API for RTL Generation**: Object-oriented, decorator-driven Python DSKey directories under `DeviceCraft/`:g / SystemVerilog digital logic.

\- `tcad/core/` — C++ solver backend and Cython bindingse (AST) representation wh- `tcad/simulator/` — Python API, analyses, and backend wrappershat can be trave- `tcad/geometry/` — Device template factory and mesh generation

\- `tcad/physics/` — BTBT, ferroelectric, and material models

\- `tcad/discovery/` — Evolutionary optimizer and analytical evaluators

\- `tcad/gui_qt/` — Qt-based schematic/layout viewer (optional)



\## License



MIT License — see [LICENSE](LICENSE) for details.
