# AXI — Dual-Port RAM

## Overview

Simplified AXI dual-port RAM with word-level access. Two independent AXI-Lite interfaces share the same memory array.

## Architecture

```
AXI_DP_RAM_SIMPLE
  Port A → [AW/W/B + AR/R] → Shared Memory
  Port B → [AW/W/B + AR/R] ↗
  - Word-level (no byte enables)
  - Zero-initialized memory
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| axi_dp_ram_simple | axi/rtl/axi_dp_ram.v | Dual-port RAM with AXI-Lite interfaces |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| DATA_WIDTH | int | 32 | Word width |
| ADDR_WIDTH | int | 16 | Address width (depth = 2^16) |

## Protocol Behavior

- **Write**: AW+W ready same cycle → B response valid next cycle
- **Read**: AR ready same cycle → R valid with data next cycle
- **Response clear**: bready & bvalid, rready & rvalid
