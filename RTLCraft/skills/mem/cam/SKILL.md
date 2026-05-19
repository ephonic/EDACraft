# CAM — Content Addressable Memory Skill

Parameterizable CAM with two backends: SRL-based (shift-register LUT) and
BRAM-based (dual-port RAM per slice). Based on Alex Forencich's verilog-cam.

## Architecture

```
CAM #(CAM_STYLE)
  ├── CamSRL (CAM_STYLE=0) — SRL-based
  │     ├── PriorityEncoder (recursive tree)
  │     └── SRL array (Memory(1, depth) per row×slice)
  └── CamBRAM (CAM_STYLE=1) — BRAM-based
        ├── PriorityEncoder (recursive tree)
        ├── RamDP × SLICE_COUNT (dual-port RAM per slice)
        └── erase_ram (tracks stored data for delete)
```

## Module PE Mapping

| PE Type | Submodule | Key Algorithm |
|---------|-----------|---------------|
| `priority_encoder` | PriorityEncoder | Recursive tree, LSB/MSB priority |
| `ram_dp` | RamDP | Dual-port RAM, read-first behavior |
| `cam_srl` | CamSRL | 4-state FSM (INIT→IDLE→WRITE→DELETE), SRL shift register array |
| `cam_bram` | CamBRAM | 6-state FSM (INIT→IDLE→DEL_1→DEL_2→WR_1→WR_2), BRAM slices + erase tracking |
| `cam_top` | CAM | Generate-if style selection (SRL vs BRAM) |

## Key Design Patterns

1. **SRL shift-register storage**: Each (row, slice) pair has a SRL16/SRL32.
   Write = shift in data bit-by-bit over SLICE_WIDTH cycles. Delete = shift in zeros.
2. **BRAM slice partitioning**: Data bus split into SLICE_WIDTH chunks, each stored
   in a RamDP. Match = AND of all slice read outputs.
3. **Erase RAM tracking** (BRAM only): Stores last written data per address for
   correct read-modify-write delete operation.
4. **Recursive priority encoder**: Generate-if tree splitting at power-of-two
   boundaries. LSB_PRIORITY="HIGH" → lowest set bit wins.
5. **Padded data bus**: SLICE_COUNT × SLICE_WIDTH may exceed DATA_WIDTH;
   high-order bits zero-padded.

## Parameters

| Parameter | SRL Default | BRAM Default | Description |
|-----------|-------------|--------------|-------------|
| DATA_WIDTH | 64 | 64 | Search data bus width |
| ADDR_WIDTH | 5 | 5 | Memory size in log2(words) |
| SLICE_WIDTH | 4 | 9 | Data bus slice width (4=SRL16, 9=BRAM) |
| SLICE_COUNT | 16 | 8 | (DATA_WIDTH+SLICE_WIDTH-1)/SLICE_WIDTH |
| RAM_DEPTH | 32 | 32 | 2^ADDR_WIDTH |

## Usage

```python
from skills.mem.cam.behaviors import (
    priority_encoder_template, ram_dp_template,
    cam_srl_template, cam_bram_template, cam_top_template,
)
from skills.mem.cam.models import CAMModel
from skills.mem.cam.arch_templates import build_cam_arch
```
