# arithmetic — Arithmetic Units & Datapath Designs

## Overview

This directory collects high-performance arithmetic datapath designs, including large integer multipliers, hash functions, and floating-point units. These designs demonstrate advanced pipeline techniques such as Karatsuba-Ofman decomposition, shift-register delay matching, and feed-forward handshaking.

## Sub-directories

### `multipliers/` — Large Integer Multipliers

| File | Description | Latency | Throughput |
|------|-------------|---------|------------|
| `montgomery_mult_384.py` | 384-bit Montgomery modular multiplier with KO-3 tree | ~60 cycles | 1/cycle |
| `mul128_ko3.py` | 128-bit KO-3 multiplier (building block) | — | — |

**Key Techniques (MontgomeryMult384):**
- **KO-3 tree**: 384→128→64→32→16 recursive decomposition
- **SOS reduction**: 3 iterations of `RedUnit128` word-level reduction
- **Pipeline alignment**: Hand-written 16-stage shift registers for `M/Mp` to match `RedUnit128` latency
- **Conditional subtraction**: Final `Z >= M ? Z-M : Z`

**Design Rule:**
> In the rtlgen AST simulator, a child `@seq` sees parent register updates **1 cycle later** than intra-module `@seq`. When chaining submodules, add +1 cycle to the delay line per module boundary, or keep delay registers inside the same module.

### `sha3/` — SHA3-256 / Keccak

| File | Description |
|------|-------------|
| `sha3_256_pipe.py` | Pipelined SHA3-256 with Keccak-f[1600] |
| `sha3_256_round_comb.py` | Single-round combinational Keccak (θ/ρ/π/χ/ι) |

### `fp8/` — Floating Point

| File | Description |
|------|-------------|
| `fp8e5m2_alu_pipe.py` | FP8 (E5M2) pipelined ALU |

## Quick Reference

### Montgomery Multiplier Interface

```python
from arithmetic.multipliers.montgomery_mult_384 import MontgomeryMult384

dut = MontgomeryMult384()
# Inputs:  X[384], Y[384], M[384], M_prime[128]
# Outputs: Z[384], o_valid
```

### DebugProbe for Pipeline Tracing

```python
from rtlgen.pipeline import DebugProbe
probe = DebugProbe(sim)
probe.find_subsim("u_r0")   # locate RedUnit128 submodule
```

## See Also

- `../cryptography/` — ChaCha20 stream cipher
- `../fundamentals/SKILL.md` — Standard library components
