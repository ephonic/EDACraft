# gpgpu — General Purpose GPU Cores

## Overview

GPU-like programmable accelerators: shader cores, warp schedulers, register files, and memory coalescing units.

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `SIMDCore` | Single-instruction multiple-data execution unit |
| `WarpScheduler` | Thread block / warp scheduling and scoreboarding |
| `RegisterFile` | Multi-bank vector register file with hazard detection |
| `MemoryCoalescer` | Load/store address coalescing for global memory |

## Design Guidelines

- **SIMD width** is typically 16, 32, or 64 lanes
- **Register file** dominates area; use multi-bank architecture to avoid port contention
- **Branch divergence** requires per-lane predicate masks

## See Also

- `../npu/SKILL.md` — Tensor-oriented array processors
- `../accelerators/SKILL.md` — Domain-specific compute engines
