# AXI-Stream — Streaming Interface Components

## Overview

AXI-Stream (AXIS) components for stream pipelining, width adaptation, and fanout.

## Architecture

```
AXIS_REGISTER — Skid buffer (REG_TYPE=2)
  Input → [output_reg] → Output
       ↘   [temp_reg]   ↗
  - 3-state: input→output, input→temp, temp→output
  - No bubble cycles

AXIS_ADAPTER — Width Up-size (8→32)
  Narrow Input → [seg_0..seg_N] → Wide Output
  - Collects N input beats per output word
  - Per-segment registers (no dynamic slices)

AXIS_BROADCAST — 1-to-M Fanout
  Input → [replicate] → M × Output
  - Per-output valid/ready
  - all_ready = Σ(m_ready & m_valid) == m_valid
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| axis_register | axis/rtl/axis_register.v | Skid buffer register (REG_TYPE=2) |
| axis_adapter | axis/rtl/axis_adapter.v | Width up-size adapter |
| axis_broadcast | axis/rtl/axis_broadcast.v | 1-to-M broadcaster |

## Key Design Patterns

- **Skid buffer**: `s_tready_early = m_ready | (~temp_valid & (~out_valid | ~in_valid))`
- **Per-segment registers**: Avoid `reg[expr+:width]` dynamic slices via individual segment regs
- **all_ready for broadcast**: `(m_ready & m_valid) == m_valid` per-bit check
