# rtlgen Skills — Hardware Design Reference Library

## Overview

This directory collects reusable hardware design modules, tutorials, and domain-specific reference designs built on the **rtlgen** framework. Each sub-directory is a self-contained skill area with its own `SKILL.md`, Python source files, and design documentation.

All modules are parameterizable Python generators that produce synthesizable Verilog / SystemVerilog via `rtlgen.VerilogEmitter`, and can be cycle-accurately simulated with `rtlgen.Simulator`.

## Directory Index

| # | Category | Path | Description |
|---|----------|------|-------------|
| 1 | **Fundamentals** | [`fundamentals/`](fundamentals/SKILL.md) | Standard library (FSM, FIFO, Arbiter), basic tutorials, API demos |
| 2 | **Arithmetic** | [`arithmetic/`](arithmetic/SKILL.md) | Multipliers (KO tree), SHA3, FP8 ALU — datapath intensive designs |
| 3 | **Cryptography** | [`cryptography/`](cryptography/SKILL.md) | Stream ciphers, block ciphers, post-quantum crypto primitives |
| 4 | **Codec** | [`codec/`](codec/SKILL.md) | Line codes, entropy coding, compression/decompression |
| 5 | **Control** | [`control/`](control/SKILL.md) | FSM, counters, scheduling, pipeline control logic |
| 6 | **Memory & Storage** | [`memory-storage/`](memory-storage/SKILL.md) | SRAM controllers, caches, DMA, storage interfaces |
| 7 | **Video** | [`video/`](video/SKILL.md) | Video codecs, display pipelines, HDMI/DP controllers |
| 8 | **Image** | [`image/`](image/SKILL.md) | ISP, image filtering, resize/rotate, DCT |
| 9 | **GPGPU** | [`gpgpu/`](gpgpu/SKILL.md) | Shader cores, warp schedulers, memory coalescing |
| 10 | **CPU** | [`cpu/`](cpu/SKILL.md) | RISC-V cores, ALUs, branch predictors, caches |
| 11 | **NPU** | [`npu/`](npu/SKILL.md) | Systolic arrays, tensor cores, quantization engines |
| 12 | **Accelerators** | [`accelerators/`](accelerators/SKILL.md) | Domain-specific accelerators (ML inference, signal processing, etc.) |
| 13 | **Verification** | [`verification/`](verification/SKILL.md) | Debug tools, testbench patterns, formal verification helpers |
| 14 | **Synthesis** | [`synthesis/`](synthesis/SKILL.md) | ABC integration, timing analysis, area estimation flows |
| 15 | **Physical Design** | [`physical-design/`](physical-design/SKILL.md) | Floorplanning, placement, routing, DFT, signoff |

## Quick Start

### 1. Generate Verilog from a reference design

```python
import sys
sys.path.insert(0, "/path/to/rtlgen")

from rtlgen import VerilogEmitter
from arithmetic.multipliers.montgomery_mult_384 import MontgomeryMult384

top = MontgomeryMult384()
sv = VerilogEmitter().emit_design(top)
print(sv)
```

### 2. Simulate a design

```python
from rtlgen import Simulator
from arithmetic.multipliers.montgomery_mult_384 import MontgomeryMult384

dut = MontgomeryMult384()
sim = Simulator(dut)
sim.reset('rst_n')
# ... drive inputs and step()
```

### 3. Use a standard library component

```python
from rtlgen import FSM, SyncFIFO, BarrelShifter

# See fundamentals/SKILL.md for full API
```

## Design Conventions

- All designs use **async active-low reset** (`rst_n`) unless otherwise noted.
- Handshake signals follow the `valid/ready` convention.
- Pipeline stages are numbered `S0, S1, S2, ...` from input to output.
- Karatsuba-Ofman multipliers use the notation `MulNxNPipe` for pipelined versions and `MulNxN` for combinational versions.

## Adding a New Skill

1. Create a new directory under `skills/<category>/`
2. Add a `SKILL.md` explaining the design domain, key modules, and usage.
3. Place Python source files alongside the `SKILL.md`.
4. Update this `skills.md` index table.

## Related Documentation

- `README.md` — Project overview
- `pyRTL.md` — RTL generation DSL specification
- `rtlgen/pipeline.py` — Pipeline primitives (`ShiftReg`, `ValidPipe`, `DebugProbe`)
