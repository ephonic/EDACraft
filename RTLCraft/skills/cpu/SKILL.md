# cpu — Processor Design Skill

## Overview

CPU micro-architecture design using the Spec2RTL flow with interactive
markdown template reports. Covers superscalar out-of-order processors,
in-order pipelines, and embedded cores.

## Modules

| File | Description |
|------|-------------|
| `behaviors.py` | 8 cycle-accurate behavior templates: IFU, IDU, ALU, LSU, ROB, RegFile, BPU, IssueQueue |
| `models.py` | RV32ISS (RISC-V RV32I simulator), RV32State, CPUModel |
| `arch_templates.py` | Extensible architecture templates (Embedded, InOrder, OutOfOrder, MultiCore) with PeBuilder/PeCatalog pattern |
| `skeleton_templates.py` | PE type → implementation step mappings (9 CPU PE types) |
| `design_flow.py` | Full Spec2RTL flow script — low-level programmatic API |
| `design_wizard.py` | Interactive design wizard with markdown template reports |
| `templates/` | Markdown templates: `spec_template.md`, `arch_template.md`, `final_report_template.md` |

## Quick Start

### Interactive Wizard (recommended)

```python
from skills.cpu.design_wizard import run_cpu_design_wizard

# High-level requirements → auto-classify + generate RTL
result = run_cpu_design_wizard(
    target_mhz=500,
    area_budget=50000,
    isa="riscv",
    pipeline_style="in_order",  # or "out_of_order", "embedded"
)
```

### Low-level Flow (full control)

```python
from skills.cpu.design_flow import run_cpu_design_flow, CPUConfig

cfg = CPUConfig(
    fetch_width=4, dispatch_width=6, rob_depth=128,
    alu_pipes=3, lq_size=64, sq_size=64,
)
result = run_cpu_design_flow(cfg)
```

### Custom Architecture

```python
from skills.cpu.arch_templates import CustomArchTemplate, CpuArchParams, PeCatalog, register_template

class MyCustomCPU(CpuArchTemplate):
    @property
    def family_name(self):
        return "My Custom CPU"

    def build_pes(self, params):
        catalog = PeCatalog()
        return [catalog.ifu(params), catalog.alu(params), catalog.lsu(params)]

    def build_interconnects(self, params):
        return [
            ("IFU", "ALU", ["inst_valid", "inst_count"]),
            ("ALU", "IFU", ["redirect_valid"]),
        ]

register_template("my_custom", MyCustomCPU)
```

## Design Wizard Workflow

The wizard produces **4 artifacts** at `output_dir/`:

| File | Phase | Content |
|------|-------|---------|
| `01_spec.md` | Spec | Filled spec template with all parameters, ISA, PPA targets |
| `02_arch_report.md` | Arch + Sim | PE list, interconnect topology, simulation results |
| `03_final_report.md` | Final | RTL modules, lint results, PPA analysis, verification status |
| `design_summary.txt` | Summary | Plain-text summary of key metrics |

### Interactive Mode

```bash
python -m skills.cpu.design_wizard --interactive
```

In interactive mode, the wizard:
1. Fills `01_spec.md` from user requirements → shows preview → waits for confirmation
2. Builds architecture + runs simulation → fills `02_arch_report.md` → waits for confirmation
3. Generates RTL + lint + PPA → fills `03_final_report.md`
4. Auto-iterates if PPA targets not met (within wizard logic)

### Missing Components

If the user's markdown spec is missing component parameters, the wizard:
- Uses default values from the selected architecture template
- Logs which components used defaults in the console output
- User can provide a custom spec markdown to override defaults

## Architecture Templates

| Template | PEs | Description |
|----------|-----|-------------|
| `embedded` | IFU, IDU, ALU, LSU | Single-issue, no BPU, no ROB |
| `in_order` | IFU, BPU, IDU, ALU, LSU | 5-stage with branch prediction |
| `out_of_order` | IFU, BPU, IDU, ALU, LSU, ROB, RegFile, IssueQueue | Superscalar OoO |
| `multi_core` | IFU, IDU, ALU, LSU, L2Cache | Multiple cores sharing L2 |

Auto-classification maps user requirements to the best template:
- `target_ipc <= 1.0` + `area < 20000` → `embedded`
- `target_ipc > 2.0` or `has_out_of_order` → `out_of_order`
- `num_cores > 1` → `multi_core`
- Default → `in_order`

## Adding a New CPU PE Type

1. Add behavior template to `behaviors.py`
2. Register into `TemplateRegistry`
3. Add implementation steps to `skeleton_templates.py`
4. Add builder to `PeCatalog` in `arch_templates.py`
