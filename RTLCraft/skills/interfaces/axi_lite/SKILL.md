# AXI-Lite RAM — AXI-Lite Slave Memory

## Overview

AXI-Lite RAM is a simplified AXI-Lite slave interface providing word-level read/write access to an internal memory array. Supports configurable data width and address width. Memory is zero-initialized.

## Architecture

```
AXIL_RAM
├── Write Address Channel (AW) — awaddr/awvalid/awready
├── Write Data Channel (W) — wdata/wvalid/wready
├── Write Response Channel (B) — bresp/bvalid/bready
├── Read Address Channel (AR) — araddr/arvalid/arready
└── Read Data Channel (R) — rdata/rresp/rvalid/rready
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| axil_ram | axi/rtl/axil_ram.v | AXI-Lite RAM with word-level read/write |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| DATA_WIDTH | int | 32 | Data bus width |
| ADDR_WIDTH | int | 16 | Address bus width (memory depth = 2^ADDR_WIDTH) |

## Protocol Behavior

### Write Channel (AW/W/B)

When `s_axil_awvalid & s_axil_wvalid & !bvalid_reg`:
- `s_axil_awready = 1`, `s_axil_wready = 1`, `s_axil_bvalid = 1`
- Latch `s_axil_awaddr` into `awaddr_reg`
- Write `s_axil_wdata` to `mem[awaddr]`

B response is cleared when `s_axil_bready & bvalid_reg`.

### Read Channel (AR/R)

When `s_axil_arvalid & (!rvalid_reg | s_axil_rready)`:
- `s_axil_arready = 1`, `s_axil_rvalid = 1`
- Latch `s_axil_araddr` into `araddr_reg`
- Read `mem[araddr]` into `rdata_reg`

R response is cleared when `s_axil_rready & rvalid_reg`.

### Response Codes

Both `bresp` and `rresp` are always `OK` (0).

## Key Design Patterns

- **Combinatorial ready generation**: `awready` and `wready` asserted when a write transaction completes in one cycle
- **Response-based back-pressure**: New writes blocked while `bvalid` is pending (prevents response overwrite)
- **Read overlap prevention**: New reads blocked while `rvalid` is pending and not consumed
- **Memory abstraction**: Word-addressable dictionary-backed memory (zero-initialized)

## Internal Registers

| Register | Width | Description |
|----------|-------|-------------|
| awready_reg | 1 | Write address ready |
| wready_reg | 1 | Write data ready |
| bvalid_reg | 1 | Write response valid |
| arready_reg | 1 | Read address ready |
| rvalid_reg | 1 | Read response valid |
| rdata_reg | DATA_WIDTH | Read data output register |
| awaddr_reg | ADDR_WIDTH | Latched write address |
| araddr_reg | ADDR_WIDTH | Latched read address |

## Import Path

```python
from skills.interfaces.axi_lite import (
    AXIL_RAM_Model,
    build_axil_ram_arch,
    axil_ram_template,
)
```
