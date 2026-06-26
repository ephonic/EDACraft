# ImplCraft

A Python-driven IC backend design automation framework. ImplCraft wraps commercial EDA tools (Design Compiler, ICC2, Calibre) behind a unified Python API, generates Tcl scripts from declarative YAML configs, parses tool reports into structured metrics, and orchestrates the full synthesis → physical implementation → sign-off pipeline — enabling AI agents to reason over QoR data instead of hand-crafting scripts.

## Overview

ImplCraft provides:

- **Tool Adapter Layer**: Python wrappers for Design Compiler, ICC2, and Calibre that encapsulate environment setup, Tcl script generation, tool invocation, and report parsing.
- **Unified Design State**: A single `DesignState` data model that flows through every stage — timing, area, power, routing, DRC/LVS metrics are all first-class fields, serializable to JSON for persistence and agent consumption.
- **Flow Orchestrator**: Dependency-aware stage execution with dry-run mode, stop-at / resume-from support, automatic metric logging, and flow-level summary reporting.
- **Report Parsers**: Deep extraction from DC QoR, ICC2 timing/congestion/utilization, and Calibre DRC/LVS reports into structured dataclasses.
- **QoR Analyzer**: Cross-stage regression detection with automated diagnostic recommendations.
- **YAML-Driven Config**: One YAML file describes the design, PDK, libraries, RTL, and flow options — no scattered Tcl variables.
- **CLI Runner**: `python -m src.run_flow` with subcommands for full flow, single stage, partial runs, analysis-only, and template generation.

## Architecture

```text
┌──────────────────────────────────────────────────┐
│  CLI  (run_flow.py)                              │
│  --config / --dry-run / --stage / --resume-from  │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  FlowOrchestrator                                │
│  dependency mgmt · state tracking · metrics log  │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  Tool Adapters                                   │
│  DCAdapter · ICC2Adapter · CalibreAdapter        │
│  script gen → subprocess → report parse          │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  DesignState                                     │
│  config · stage_results · artifacts · history    │
│  TimingMetrics · AreaMetrics · PowerMetrics      │
│  RouteMetrics · DRCMetrics · LVSMetrics          │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  Parsers              QoR Analyzer               │
│  DCReportParser       cross-stage delta          │
│  ICC2ReportParser     regression detection       │
│  CalibreReportParser  fix recommendations        │
└──────────────────────────────────────────────────┘
```

## Supported Tools

| Tool | Version Tested | Purpose | Environment |
|------|---------------|---------|-------------|
| Design Compiler | U-2022.12-SP7-3 | Logic synthesis | `source /share/apps/EDAs/syn22.bash` |
| ICC2 | U-2022.12-SP6 | Physical implementation | `source /share/apps/EDAs/syn22.bash` |
| Calibre | 2024.2_36 | DRC / LVS sign-off | `source /share/apps/EDAs/mg.bash` |

## Flow Stages

The default minimal flow closure covers 9 stages:

| # | Stage | Tool | Description |
|---|-------|------|-------------|
| 1 | `synthesis` | DC | RTL → gate-level netlist, SDC, QoR |
| 2 | `create_lib` | ICC2 | Create NDM library, read netlist |
| 3 | `floorplan` | ICC2 | Die/core definition, boundary/tap cells |
| 4 | `placement` | ICC2 | Standard cell placement with timing-driven optimization |
| 5 | `cts` | ICC2 | Clock tree synthesis + clock optimization |
| 6 | `routing` | ICC2 | Global / track / detail routing + redundant vias |
| 7 | `route_opt` | ICC2 | Post-route optimization + SPEF extraction |
| 8 | `drc` | Calibre | Design rule check sign-off |
| 9 | `lvs` | Calibre | Layout vs schematic verification |

## Installation

```bash
# Clone the EDACraft repo
git clone https://github.com/ephonic/EDACraft.git
cd EDACraft/ImplCraft

# Install in development mode
pip install -e .

# Verify installation
python -m src.run_flow --help
```

**Requirements**: Python ≥ 3.10, PyYAML ≥ 6.0, access to Synopsys / Mentor EDA tools.

## Quick Start

### 1. Generate a project config template

```bash
python -m src.run_flow --init my_project.yaml
```

Edit `my_project.yaml` to set your design name, clock, die size, PDK paths, library paths, and RTL files.

### 2. Dry run (generate Tcl scripts only, no tool execution)

```bash
python -m src.run_flow --config my_project.yaml --dry-run
```

This creates a `work/` directory with one subfolder per stage, each containing the generated `run.tcl` script. Inspect them before running real tools.

### 3. Run the full flow

```bash
python -m src.run_flow --config my_project.yaml
```

The orchestrator executes stages in dependency order, logs metrics after each stage, and produces a `design_state.json` snapshot + `qor_report.txt` in the work directory.

### 4. Run a single stage

```bash
python -m src.run_flow --config my_project.yaml --stage synthesis
```

### 5. Resume from a specific stage

```bash
# Skip everything before placement, then run placement → end
python -m src.run_flow --config my_project.yaml --resume-from placement
```

### 6. Stop at a specific stage

```bash
# Run synthesis through CTS only
python -m src.run_flow --config my_project.yaml --stop-at cts
```

### 7. Analyze existing results (no tool re-run)

```bash
python -m src.run_flow --config my_project.yaml --analyze-only
```

## Configuration

The project YAML config has five sections:

```yaml
design:
  name: FullSystem            # Design name
  top_module: FullSystem      # Top-level module
  clock_period_ns: 10.0       # Target clock period
  clock_name: clk             # Clock port name
  die_width_um: 2900.0        # Die width in micrometers
  die_height_um: 1900.0       # Die height in micrometers
  core_offset_um: [180, 180, 180, 180]  # Core-to-die offsets
  target_utilization: 0.70    # Target placement utilization
  scenario: func.tt0p9v.wc.cmax_25c.setup  # Timing scenario

pdk:
  name: tsmc28hpcp            # PDK name
  tech_file: /path/to/tech.tf # Technology file
  min_routing_layer: M2       # Minimum routing layer
  max_routing_layer: M9       # Maximum routing layer

libraries:
  std_cell_libs:              # Synthesis .db libraries
    - /path/to/stdcell.db
  ndm_libs:                   # ICC2 NDM reference libraries
    - /path/to/stdcell.ndm
    - /path/to/ram.ndm
  dont_use_cells: []          # Cells to exclude from synthesis

rtl:
  files:                      # RTL source files
    - /path/to/rtl/top.v
  sdc_file: ""                # SDC constraint file (empty = auto-generate)

flow:
  work_root: ./work           # Working directory for all stages
  dry_run: false              # Generate scripts without running tools
```

## Project Structure

```text
ImplCraft/
├── pyproject.toml                    # Python package metadata
├── config/
│   └── project_default.yaml          # Default project config (TSMC 28nm HPC+)
├── src/
│   ├── __init__.py
│   ├── __main__.py                   # python -m entry point
│   ├── run_flow.py                   # CLI runner
│   ├── db/
│   │   └── design_state.py           # DesignState + all metric dataclasses
│   ├── tools/
│   │   ├── base.py                   # ToolAdapter ABC
│   │   ├── dc_adapter.py             # Design Compiler adapter
│   │   ├── icc2_adapter.py           # ICC2 adapter (6 sub-stages)
│   │   └── calibre_adapter.py        # Calibre DRC/LVS adapter
│   ├── parsers/
│   │   ├── dc_parser.py              # DC report parser
│   │   ├── icc2_parser.py            # ICC2 report parser
│   │   └── calibre_parser.py         # Calibre report parser
│   ├── flow/
│   │   ├── stages.py                 # Stage definitions + default flow
│   │   └── orchestrator.py           # Flow orchestrator
│   ├── analysis/
│   │   └── qor_analyzer.py           # QoR cross-stage analyzer
│   └── config/
│       └── loader.py                 # YAML config loader/saver
└── tests/
    ├── test_config.py                # Config loader tests
    ├── test_adapters.py              # Tcl script generation tests
    ├── test_parsers.py               # Report parser tests
    └── test_flow.py                  # Orchestrator + state + analyzer tests
```

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test suites
python -m pytest tests/test_adapters.py -v   # Script generation
python -m pytest tests/test_parsers.py -v    # Report parsing
python -m pytest tests/test_flow.py -v       # Flow orchestration
```

**30 tests** cover config round-trip, Tcl script generation for all stages (DC/ICC2/Calibre), report parsing (QoR/timing/area/power/DRC/LVS), design state serialization, dry-run orchestration, stop-at/resume-from, and QoR regression detection.

## Roadmap

The MVP (v0.1.0) covers the minimum flow closure: DC → ICC2 → Calibre. Future releases will incrementally expand toward the full backend copilot vision.

### Phase 2 — Sign-off & Extraction (v0.2)

- **PrimeTime adapter** — STA sign-off with multi-corner multi-mode (MCMM) support, SI analysis, CPPR
- **StarRC adapter** — Parasitic extraction, SPEF generation, back-annotation to PT/ICC2
- **PrimePower / PT-PX adapter** — Dynamic and leakage power analysis with VCD/FSDB waveform input
- **SPEF round-trip** — ICC2 → StarRC → PT → ICC2 ECO loop

### Phase 3 — ECO & Iteration (v0.3)

- **Functional ECO** — Spare cell insertion, metal-only ECO flow
- **Physical ECO** — ICC2 `create_eco_cells` + incremental P&R
- **ECO verifier** — Formal equivalence check (Formality / Conformal LEC) pre/post ECO
- **Iteration manager** — Automatic before/after QoR comparison, rollback support

### Phase 4 — Physical Verification Deep Dive (v0.4)

- **Calibre DRC auto-fix** — Programmatic fixing of common DRC violations (spacing, density, antenna)
- **Calibre LVS debug** — Structured error categorization, net tracing, device matching analysis
- **ERC analysis** — Electrical rule check with power-grid connectivity verification
- **Metal fill** — Timing-aware metal fill insertion with slack preservation

### Phase 5 — Analysis & Intelligence (v0.5)

- **Constraint analyzer** — SDC quality assessment, false path / multicycle path audit
- **Floorplan advisor** — Aspect ratio optimization, pin assignment heuristics, blockage placement
- **Timing root-cause engine** — Path-based root-cause classification (logic depth, fanout, clock skew, congestion)
- **Power analysis** — VT distribution optimization, clock-gating efficiency, multi-Vt cell swapping suggestions

### Phase 6 — Agent Layer (v0.6)

- **LLM-driven diagnosis** — Agent reads QoR data, forms hypotheses, proposes parameter changes
- **Autonomous iteration** — Agent executes fixes, compares results, decides next action
- **Knowledge base** — Design pattern library, troubleshooting recipes, silicon learning database
- **Multi-agent collaboration** — Specialized agents for timing / power / area / DRC, coordinated by orchestrator agent

### Phase 7 — Dashboard & Collaboration (v1.0)

- **Web dashboard** — Real-time QoR visualization, stage progress tracking, metric trending
- **Design version control** — Git-like commit/diff/tag for design states and flow scripts
- **Notification system** — Slack/email alerts on stage completion, regression, or failure
- **Multi-design management** — Run and compare multiple designs in parallel

## Design Philosophy

| Principle | Description |
|-----------|-------------|
| **Hard-core first** | Each module provides real analysis/solving capability, not just Tcl script generation |
| **Tool-agnostic abstraction** | Agent calls `timing.optimize()` without knowing if it's DC or Genus underneath |
| **Database-driven** | All decisions based on queryable design state, not scattered report files |
| **Explainable decisions** | Every recommendation comes with quantified evidence, spec references, and trade-off data |
| **Verifiable closed loop** | Every action has before/after QoR comparison with rollback support |
| **Safe boundaries** | LLM does not directly modify designs — controlled Python API + regression checker |

## License

MIT License — see [LICENSE](../LICENSE) for details.
