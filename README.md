# EDACraft



A comprehensive EDA (Electronic Design Automation) toolkit collection for digital and analog IC design.



## Overview



EDACraft is a monorepo hosting multiple EDA sub-projects, each focusing on different aspects of the chip design flow. The goal is to provide an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimization.



## Sub-projects



### RTLCraft (`RTLCraft/`)



A Python-to-Verilog RTL generation and verification framework. RTLCraft provides:



- **Python API for RTL Generation**: Object-oriented, decorator-driven Python DSL for describing synthesizable Verilog / SystemVerilog digital logic.

- **AST-based Design**: Transparent Abstract Syntax Tree (AST) representation where every `Signal`, `Module`, and `Assign` is an explicit node that can be traversed, modified, and printed.

- **Built-in Simulation**: Cycle-accurate Python AST interpreter with hierarchical design support, X/Z 4-state logic, multi-clock, and JIT acceleration.

- **UVM Verification**: Native Python UVM DSL with support for directed/random sequences, coverage collection, and scoreboard-based checking.

- **Verilog Generation**: Single-module or full-design Verilog / SystemVerilog emission with optional assertions.

- **Lint & Analysis**: AST-level lint rules (e.g., `seq_output_assign`, `comb_reg_assign`, `unregistered_output`) and Verilog text-level linting.

- **Synthesis & PPA**: Integration with ABC for synthesis and PPA (Power, Performance, Area) analysis.

A comprehensive EDA (Electronic Design Automation) toolkit collection for digitaKey directories under `RTLCraft/`:

- `rtlgen/` — Core framework (AST, codegen, simulation, UVM)

- `skills/` — Reusable design skills (arithmetic, cryptography, memory, etc.)ffe- `generated_*` — Auto-generated Verilog and UVM testbenches an integrated, extensible, and AI-friendly toolchain for hardware design, verification, and optimiz### DeviceCraft (`DeviceCraft/`)



## License



See [LICENSE](LICENSE) for details. Commercial use of this Software requires a separate written license agreement
with the author and Fudan University.
