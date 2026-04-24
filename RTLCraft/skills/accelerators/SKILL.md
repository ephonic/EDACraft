# accelerators — Domain-Specific Hardware Accelerators

## Overview

General-purpose accelerator templates and domain-specific engines beyond the GPGPU/CPU/NPU taxonomy: DSP, signal processing, genomics, graph analytics, etc.

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `FFTEngine` | Radix-2 / Radix-4 FFT butterfly pipeline |
| `FIRFilterBank` | Multi-channel FIR filter with shared coefficients |
| `SmithWaterman` | Genomic sequence alignment (local alignment) |
| `GraphAccelerator` | Sparse matrix-vector multiply for graph analytics |

## Design Guidelines

- Identify **memory-bound vs compute-bound** kernels before architecture selection
- Use **streaming dataflow** (no random access) whenever possible
- **Custom precision** (bfloat16, log-domain, stochastic) can dramatically reduce area

## See Also

- `../npu/SKILL.md` — Neural network accelerators
- `../gpgpu/SKILL.md` — Programmable SIMD engines
