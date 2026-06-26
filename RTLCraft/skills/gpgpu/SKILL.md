# gpgpu — GPGPU/SIMT Design Skill

## Overview

GPGPU (General-Purpose GPU) micro-architecture design using the Spec2RTL
flow with interactive markdown template reports. Covers SIMT execution
model, CU/SM pipeline, warp scheduling, workgroup dispatch, and memory
subsystem.

## Modules

| File | Description |
|------|-------------|
| `behaviors.py` | Cycle-accurate templates: CTA_Scheduler (workgroup dispatch), Warp_Scheduler (per-CU warp management) |
| `models.py` | GPGPUModel (SIMT execution), GPUWarp, GPUThread, GPUState |
| `arch_templates.py` | Extensible architecture templates (Basic, ComputeCluster, StreamProcessor, MultiCu) with GpgpuPeBuilder/GpgpuPeCatalog pattern |
| `skeleton_templates.py` | PE type → implementation steps (8 GPGPU PE types) |
| `design_flow.py` | Full Spec2RTL flow script — low-level programmatic API |
| `design_wizard.py` | Interactive design wizard with markdown template reports |
| `templates/` | Markdown templates: `spec_template.md`, `arch_template.md`, `final_report_template.md` |

## Quick Start

### Interactive Wizard (recommended)

```python
from skills.gpgpu.design_wizard import run_gpgpu_design_wizard

result = run_gpgpu_design_wizard(
    num_cus=8,
    warps_per_cu=16,
    target_mhz=1000,
    area_budget=200000,
)
```

### Low-level Flow (full control)

```python
from skills.gpgpu.design_flow import run_gpgpu_design_flow, GPGPUConfig

cfg = GPGPUConfig(
    num_cus=8, warps_per_cu=16,
    vgpr_per_cu=256, lds_size_kb=64,
)
result = run_gpgpu_design_flow(cfg)
```

### Custom Architecture

```python
from skills.gpgpu.arch_templates import (
    CustomGpuArchTemplate, GpgpuArchParams,
    GpgpuPeCatalog, register_template,
)

class MyGPU(GpgpuArchTemplate):
    @property
    def family_name(self):
        return "My Custom GPU"

    def build_pes(self, params):
        catalog = GpgpuPeCatalog()
        return [
            catalog.warp_scheduler(params),
            catalog.sm_pipe(params),
            catalog.shared_mem(params),
        ]

    def build_interconnects(self, params):
        return [
            ("Warp_Scheduler", "SM_Pipe", ["dispatch_valid", "dispatch_warp_id"]),
            ("SM_Pipe", "SharedMem", ["req_valid", "req_addr"]),
        ]

register_template("my_gpu", MyGPU)
```

## Design Wizard Workflow

The wizard produces **4 artifacts** at `output_dir/`:

| File | Phase | Content |
|------|-------|---------|
| `01_spec.md` | Spec | Filled spec template with GPU parameters, ISA, PPA targets |
| `02_arch_report.md` | Arch + Sim | PE list, interconnect topology, simulation results |
| `03_final_report.md` | Final | RTL modules, lint results, PPA analysis, verification status |
| `design_summary.txt` | Summary | Plain-text summary of key metrics |

### Interactive Mode

```bash
python -m skills.gpgpu.design_wizard --interactive
```

In interactive mode:
1. Fills `01_spec.md` from user requirements → shows preview → waits for confirmation
2. Builds architecture + runs simulation → fills `02_arch_report.md` → waits for confirmation
3. Generates RTL + lint + PPA → fills `03_final_report.md`
4. Auto-iterates if PPA targets not met

### Missing Components

If parameters are missing, the wizard:
- Uses defaults from the selected architecture template
- Logs which components used defaults
- User can provide custom spec to override

## Architecture Templates

| Template | PEs | Description |
|----------|-----|-------------|
| `basic` | Warp_Scheduler, SM_Pipe, SharedMem | Single CU, minimal GPU |
| `compute_cluster` | CTA_Scheduler, Warp_Scheduler, SM_Pipe, SharedMem, WarpArbiter, VGPR_Bank, [L2_Cache] | Multi-CU with L2 |
| `stream_processor` | SM_Pipe, VGPR_Bank, PopCnt | SIMD-wide vector processor |
| `multi_cu` | All PEs + L2_Cache | Full GPGPU with CTA dispatch, arbitration |

Auto-classification maps requirements to the best template:
- `num_cus >= 8` → `multi_cu`
- `num_cus >= 4` + LDS > 0 → `compute_cluster`
- `num_cus <= 1` + `alu_pipes <= 2` → `basic`
- Default → `compute_cluster`

## Adding a New GPGPU PE Type

1. Add behavior template to `behaviors.py`
2. Register into `TemplateRegistry`
3. Add implementation steps to `skeleton_templates.py`
4. Add builder to `GpgpuPeCatalog` in `arch_templates.py`
