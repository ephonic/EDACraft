# GPGPU Streaming Processor

A complete SIMT (Single Instruction, Multiple Thread) streaming processor core built with **rtlgen**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         GPGPUCore                            │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │  WarpSched  │───>│   Frontend  │───>│   Scoreboard    │  │
│  │  (4 warps)  │    │ (Fetch/Dec) │    │ (Hazard track)  │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │ RegisterFile│<───│    ALU      │    │    TensorCore   │  │
│  │ (32×32-bank)│    │  (32 lanes) │    │   (4×4×4 MMA)   │  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│         ▲                  │                                 │
│         │                  ▼                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │    SFU      │    │  Coalescer  │───>│    L1 Cache     │  │
│  │ (32 lanes)  │    │  (128-bit)  │    │  (16-set, 4-way)│  │
│  └─────────────┘    └─────────────┘    └─────────────────┘  │
│                                               │              │
│  ┌─────────────┐                              ▼              │
│  │ SharedMemory│                         Global Memory      │
│  │  (16 KB)    │                                              │
│  └─────────────┘                                             │
└─────────────────────────────────────────────────────────────┘
```

## Modules

| Module | Description | Status |
|--------|-------------|--------|
| `RegisterFile` | 32-lane multi-bank register file (2R1W) | ✅ |
| `ALULane` | Single-lane integer/FP ALU | ✅ |
| `ALUArray` | 32-lane SIMD ALU array | ✅ |
| `SFULane` | Special function unit lane (LUT-based) | ✅ |
| `SFUArray` | 32-lane SFU array | ✅ |
| `TensorCore` | 4×4×4 matrix multiply-accumulate unit | ✅ |
| `WarpScheduler` | Round-robin scheduler with divergence stack | ✅ |
| `Scoreboard` | In-flight register dependency tracker | ✅ |
| `Frontend` | Instruction fetch/decode with I-cache | ✅ |
| `MemoryCoalescer` | Warp-level address coalescing | ✅ |
| `L1Cache` | Set-associative data cache | ✅ |
| `SharedMemory` | Banked scratchpad memory | ✅ |
| `GPGPUCore` | Top-level integration | ✅ |

## Parameters

Configurable via `GPGPUParams`:

- `warp_size`: 32 threads/warp
- `num_warps`: 4 warps/core
- `num_regs`: 32 registers/thread
- `data_width`: 32-bit
- `tensor_dim`: 4×4×4 MMA
- `icache_sets`: 16 sets
- `l1_sets/l1_ways`: 16 sets, 4 ways
- `shared_mem_size`: 16 KB

## Usage

```python
from rtlgen import VerilogEmitter
from skills.gpgpu.core import GPGPUCore
from skills.gpgpu.common import GPGPUParams

params = GPGPUParams()
core = GPGPUCore(params)

verilog = VerilogEmitter().emit_design(core)
with open("gpgpu_core.v", "w") as f:
    f.write(verilog)
```

## Tests

```bash
pytest tests/test_gpgpu.py -v
```

## Examples

See `skills/gpgpu/examples/basic_usage.py` for a complete walkthrough:

```bash
python skills/gpgpu/examples/basic_usage.py
```

Covers:
- Verilog generation
- ALU lane simulation
- Register file read/write
- TensorCore MMA
- Custom parameter configurations

## ISA

See `skills/gpgpu/common/isa.py` for opcode definitions covering:
- ALU: ADD, SUB, MUL, MAD, AND, OR, XOR, SHL, SHR, MIN, MAX, ABS, NEG
- FP: FADD, FSUB, FMUL, FMAD, FMIN, FMAX, FABS, FNEG
- Compare: SETP_EQ, SETP_NE, SETP_LT, SETP_LE, SETP_GT, SETP_GE
- Move: MOV, SEL
- SFU: RECIP, RSQRT, SIN, COS, LOG2, EXP2
- Memory: LD, ST, LDS, STS
- Tensor: MMA
- Control: BRA, CALL, RET, EXIT, BAR, NOP
