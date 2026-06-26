# Ethernet — PTP Timestamp Extract

## Overview

PTP (Precision Time Protocol) timestamp extraction from AXI-Stream tuser field. Used in ethernet/PTP-aware designs to recover hardware timestamps from packet metadata.

## Architecture

```
PTP_TS_EXTRACT
  s_axis_tuser → [slice ts_offset+:ts_width] → m_axis_ts
  frame_reg → [~tlast on tvalid] → valid on first beat
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| ptp_ts_extract | ethernet/rtl/ptp_ts_extract.v | Extract timestamp, valid on first beat |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| TS_WIDTH | int | 96 | Timestamp width (bits) |
| TS_OFFSET | int | 1 | Bit offset in tuser |

## Key Design Patterns

- **Frame tracking**: `frame_reg = ~tlast` when `tvalid` — tracks mid-frame state
- **First-beat valid**: `ts_valid = tvalid & ~frame_reg` — only valid on first beat
