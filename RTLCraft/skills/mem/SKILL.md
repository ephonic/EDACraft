# mem — Memory Controller Design Skill

## Overview

Memory subsystem designs: DDR3/DDR4/LPDDR5 controllers, SRAM interfaces,
CAM (Content Addressable Memory), and PHY sequencers. Uses the Spec2RTL
flow with `MemoryModel` and `MemoryControllerSpec`.

## Subdirectories

| Directory | Description |
|-----------|-------------|
| `ddr3/` | DDR3 controller full Spec2RTL flow (Phase 0-5) |
| `cam/` | CAM behavioral models, DSL skeletons, and skill templates |

## Core Modules

| File | Description |
|------|-------------|
| `behaviors.py` | Cycle-accurate templates: memory_controller (FSM: INIT→IDLE→ACT→READ/WRITE→PRE→REF), dfi_sequencer (DFI timing + data serialization) |
| `skeleton_templates.py` | PE type → implementation steps (memory_controller, dfi_sequencer) |

## Quick Start

```python
from skills.mem.behaviors import memory_controller_template, dfi_sequencer_template
from skills.mem.skeleton_templates import register_memory_skeleton_steps
from rtlgen.behaviors import TemplateRegistry

# Register skeleton steps
from rtlgen import arch_skel
register_memory_skeleton_steps(arch_skel._TEMPLATE_STEPS)

# Use templates
beh = memory_controller_template(mem_type="DDR3", bank_count=8)
```

## Controller Architecture

```
DDR3Controller (top wrapper: mem port → core mapping)
  └── DDR3Core (core FSM: INIT/IDLE/ACT/READ/WRITE/PRE/REF)
        ├── DDR3DFISeq (DFI sequencer: timing + serialization)
        └── DDR3FIFO (ID tracking + write data buffer)
```

## Design Guidelines

1. Use `MemoryControllerSpec` for JEDEC-compliant parameterization
2. Use `MemoryModel` as the `ModelProvider` for row buffer tracking
3. DDR3Timing provides ns→cycles conversion for all timing parameters
4. DFI sequencer handles command timing delays and data serialization
5. Verify all state transitions against behavioral model before RTL

## Adding a New Memory Controller Type

1. Add behavior template to `behaviors.py`
2. Register into `TemplateRegistry`
3. Add implementation steps to `skeleton_templates.py`
4. Create a new design flow script in `skills/mem/ddr3/` or a new skill folder
