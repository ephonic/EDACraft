# memory-storage — SRAM, Cache & Storage Controllers

## Overview

Memory subsystem designs including SRAM controllers, cache hierarchies, DMA engines, and storage interface controllers (NVMe, UFS, SD/eMMC).

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `SimpleSRAM` | Single-port SRAM wrapper with read/write arbitration |
| `DualPortSRAM` | True dual-port SRAM with collision handling |
| `SimpleCache` | Direct-mapped cache with write-back policy |
| `DMAEngine` | Scatter-gather DMA with descriptor rings |
| `AXI4SRAMBridge` | AXI4-to-SRAM protocol adapter |

## Design Guidelines

- Use `rtlgen.ram` for memory primitive instantiation
- Maintain byte-enable granularity for sub-word writes
- Consider read-latency vs combinational output trade-offs

## See Also

- `../fundamentals/SKILL.md` — `ram_demo.py` basic usage
