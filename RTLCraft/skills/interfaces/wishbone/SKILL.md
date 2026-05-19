# Wishbone — Bus Interface Components

## Overview

Wishbone bus components: register slice for pipeline isolation and 2-to-1 address-decode multiplexer for bus fan-out.

## Architecture

```
WB_REG (register slice)
  Master Side ←→ Registers ←→ Slave Side
  - 2-state: Idle (pass-through) / Cycle (hold)
  - 1-cycle latency per transaction

WB_MUX_2 (2-to-1 MUX)
  Master → Address Decode → Slave0 / Slave1
  - Pure combinational
  - Priority: slave0 > slave1
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| wb_reg | wishbone/rtl/wb_reg.v | Register slice, 1-cycle latency |
| wb_mux_2 | wishbone/rtl/wb_mux_2.v | 2-to-1 address-decode MUX |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| DATA_WIDTH | int | 32 | Data bus width (8/16/32/64) |
| ADDR_WIDTH | int | 32 | Address bus width |
| SELECT_WIDTH | int | DATA_WIDTH/8 | Byte select width |

## Key Design Patterns

- **Cycle-hold register**: `wbs_cyc_o_reg & wbs_stb_o_reg` detects active cycle
- **Response gate**: `ack | err | rty` ends the cycle
- **Address decode**: `~|((adr ^ addr) & addr_msk)` matches address prefix
- **Priority MUX**: `wbs1_sel = wbs1_match & ~wbs0_match`
