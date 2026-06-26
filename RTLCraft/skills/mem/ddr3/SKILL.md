# ddr3 — DDR3 Controller Spec2RTL Design Skill

## Overview

DDR3 memory controller design using the full Spec2RTL 6-phase flow.
Produces 4 RTL modules: DDR3Controller, DDR3Core, DDR3DFISeq, DDR3FIFO.

## Modules

| File | Description |
|------|-------------|
| `ddr3_controller.py` | Full Spec2RTL flow (Phase 0-5) for DDR3 controller |
| `generated/` | Generated Verilog output |

## Architecture

```
DDR3Controller (top wrapper: mem port → core mapping)
  └── DDR3Core (core FSM: INIT/IDLE/ACT/READ/WRITE/PRE/REF)
        ├── DDR3DFISeq (DFI sequencer: timing + serialization)
        └── DDR3FIFO (ID tracking + write data buffer)
```

## Quick Start

```python
from skills.mem.ddr3.ddr3_controller import main
main()
```

## Dependencies

- `skills/mem/behaviors.py` — memory_controller_template, dfi_sequencer_template
- `skills/mem/skeleton_templates.py` — PE type implementation steps
- `rtlgen/` — Spec2RTL framework (all phases)
