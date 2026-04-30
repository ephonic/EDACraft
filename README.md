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

Key directories under `RTLCraft/`:

- `rtlgen/` — Core framework (AST, codegen, simulation, UVM)
- `examples/` — Design examples (counter, decoder_8b10b, FP8 ALU, etc.)
- `tests/` — Pytest-based functional and pyUVM test suites
- `skills/` — Reusable design skills (arithmetic, cryptography, memory, etc.)


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

## License

MIT License — see [LICENSE](LICENSE) for details.
