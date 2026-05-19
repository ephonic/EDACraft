# PCIe — Interface Components

## Overview

PCIe interface utilities: pulse merge for multi-input event counting and P-Tile flow control credit tracking.

## Architecture

```
PULSE_MERGE
  pulse_in[WIDTH] → [popcount] → [counter ±pulse] → count_out
  - Saturating: new pulses accumulate
  - pulse_out = (count > 0)

PCIE_PTILE_FC_COUNTER
  tx_cdts_limit → [TDM demux] → fc_cap/fc_inc
  fc_av → [clamp(fc_av - fc_dec + fc_inc, 0, fc_cap)]
```

## PE Types

| PE Type | Reference File | Description |
|---------|---------------|-------------|
| pulse_merge | pcie/rtl/pulse_merge.v | Multi-input pulse accumulator |
| pcie_ptile_fc | pcie/rtl/pcie_ptile_fc_counter.v | Flow control credit counter |

## Key Design Patterns

- **Population count**: `bin(pulse_in).count('1')` for input pulse sum
- **Saturating arithmetic**: `min(max(result, 0), fc_cap)`
- **TDM demux**: `tx_cdts_limit_tdm_idx == index` selects which counter to update
