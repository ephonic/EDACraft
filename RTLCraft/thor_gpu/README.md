# Thor-Class GPGPU SM Compute Cluster — RTLCraft Spec2RTL Design

This directory contains a complete, end-to-end Spec2RTL design for a **Thor-class GPGPU
streaming-multiprocessor (SM) compute cluster**. It is built with RTLCraft's 6-layer IR
flow and produces synthesizable Verilog together with cross-layer verification evidence.

**Key reference**: [`design_spec.md`](design_spec.md) has the full requirements,
architecture, ISA, PPA targets, and roadmap.

---

## Directory Layout

```
thor_gpu/
├── design_spec.md              # Full design specification
├── README.md                   # This file
├── constraints.py              # Cross-layer constraint definitions and transforms
├── docgen.py                   # Document generator (per-layer specs/plans/reports)
├── specs/                      # SoC-level specs and review bundle
│   └── 00_top_level_spec.md
├── modules/                    # Per-module 6-layer IR decomposition
│   ├── common/                 # Shared bit/integer helpers
│   ├── warp_scheduler/
│   ├── vector_alu/
│   ├── vector_fpu/
│   ├── tensor_core/
│   ├── lsu/
│   ├── simt_stack/
│   ├── shared_memory/
│   ├── gpu_sm/
│   └── gpu_cluster/
├── top/                        # SoC/cluster top-level integration
└── verilog/                    # Generated Verilog output
```

Every module directory follows the convention:

```
modules/<M>/
├── layer_L1_behavior/   {src/behavior.py, specs/01_*, tests/test_behavior.py}
├── layer_L2_cycle/      {src/cycle.py, specs/02_*, tests/test_cycle.py}
├── layer_L3_architecture/{src/arch.py, specs/03_*, tests/test_arch.py}
├── layer_L4_structure/  {src/structure.py, specs/04_*, tests/test_structure.py}
├── layer_L5_dsl/        {src/dsl.py, specs/05_*, tests/test_dsl.py}
├── layer_L6_verilog/    {src/emitter.py, specs/06_*, tests/test_verilog.py}
└── specs/               {00_module_spec.md, 07_module_test_plan.md, 08_module_test_report.md}
```

---

## Architecture

2 SMs × 4 warps × 8 INT32 lanes, custom 4-bit-opcode ISA, sticky round-robin warp
scheduling, INT8 8×8×8 tensor core, FP32 vector FPU, and a round-robin L2 arbiter.

See [`design_spec.md`](design_spec.md) §3 (System Architecture) and §6 (ISA) for details.

---

## How to Run

**Prerequisites**: Python 3.12+, `pytest` 7.4+, RTLCraft `rtlgen` on `PYTHONPATH`.

**1. Module-level pytest suite**

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft pytest thor_gpu/modules -q
```

**2. Generate Verilog for all modules + cluster top**

```bash
PYTHONPATH=/Users/yangfan/release/EDACraft-main/RTLCraft python thor_gpu/docgen.py
```

---

## See Also

- [`design_spec.md`](design_spec.md) — requirements, architecture, ISA, and roadmap.
- [`../README.md`](../README.md) / [`../Tutorial.md`](../Tutorial.md) — RTLCraft methodology.
