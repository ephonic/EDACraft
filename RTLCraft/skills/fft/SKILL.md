# fft — Fast Fourier Transform Skill

## Overview

Radix-2^2 Single-Path Delay Feedback (R2^2SDF) FFT accelerator suite.
Parameterizable FFT sizes (64/128/1024), 16-bit default data width.

Reference RTL: `ref_rtl/fft/verilog/` (Butterfly, DelayBuffer, Multiply, Twiddle, SdfUnit, SdfUnit2).

## Modules

| File | Description |
|------|-------------|
| `behaviors.py` | 7 behavior templates (fft_butterfly, fft_delay_buffer, fft_multiply, fft_twiddle, fft_sdf_unit, fft_sdf_unit2, fft_controller) |
| `models.py` | Golden reference models for all 7 FFT modules |
| `arch_templates.py` | build_fft_arch(), FFTSuiteModel |
| `skeleton_templates.py` | PE type → implementation steps (7 PE types) |

## Quick Start

### Build Architecture

```python
from skills.fft.arch_templates import build_fft_arch

arch = build_fft_arch(
    N=64,       # FFT size
    width=16,   # Data width in bits
)
```

### Golden Reference Verification

```python
from skills.fft.models import (
    FFTButterflyModel, FFTMultiplyModel,
    FFTSdfUnitModel, FFTControllerModel,
)

# Butterfly
bf = FFTButterflyModel(width=16, rh=0)
y0_re, y0_im, y1_re, y1_im = bf.step(
    x0_re=100, x0_im=0, x1_re=50, x1_im=0,
)

# SDF Unit (Radix-2^2)
sdf = FFTSdfUnitModel(N=64, M=64, width=16)
for i in range(64):
    do_en, do_re, do_im = sdf.step(di_en=1, di_re=i, di_im=0)

# Full FFT Controller (N=64)
fft = FFTControllerModel(N=64, width=16)
for i in range(64):
    do_en, do_re, do_im = fft.step(di_en=1, di_re=i, di_im=0)
```

## FFT Pipeline Stages

| Stage | pe_type | Description | Latency |
|-------|---------|-------------|---------|
| FFT_BUTTERFLY | fft_butterfly | Complex radix-2 butterfly (add/sub + scale) | 1 cycle |
| FFT_DELAY_BUFFER | fft_delay_buffer | Shift-register delay line (depth = 2^k) | depth cycles |
| FFT_MULTIPLY | fft_multiply | Complex multiplier (4 real multiplies + scale) | 1 cycle |
| FFT_TWIDDLE | fft_twiddle | ROM-based twiddle factor lookup | 1 cycle (ROM) |
| FFT_SDF_UNIT | fft_sdf_unit | Radix-2^2 SDF unit (BF1+DB1+BF2+DB2+MULT) | Variable |
| FFT_SDF_UNIT2 | fft_sdf_unit2 | Radix-2 SDF unit for M=2 (no twiddle) | Variable |
| FFT_CONTROLLER | fft_controller | Top-level: chains SDF stages based on N | Variable |

## Key Algorithms

### Complex Butterfly (FFTButterfly)

```
y0 = (x0 + x1 + RH) >>> 1   # Sum path with optional rounding
y1 = (x0 - x1 + RH) >>> 1   # Difference path with optional rounding
```

RH (rounding half): BF1 uses RH=0 (truncation), BF2 uses RH=1 (rounding).
Arithmetic right shift preserves sign bit.

### Complex Multiplication (FFTMultiply)

```
real_part = a_re * b_re - a_im * b_im
imag_part = a_re * b_im + a_im * b_re
```

4 real multiplications, each scaled by >>>(width-1) to return to Q1.(w-1) format.
Saturation protection prevents overflow on the final add/sub.

### Twiddle Factor ROM (FFTTwiddle)

```
W_N^k = cos(-2*pi*k/N) + j*sin(-2*pi*k/N)
```

Quantized to signed width-bit integers: `int(round(cos_val * 2^(width-1)))`.

### Radix-2^2 SDF Pipeline (FFTSdfUnit)

```
Input → DB1 ─┬→ BF1 → DB2 ─┬→ BF2 → Multiply → Output
             │               │
             └───────────────┴── feedback paths
```

Two butterfly stages (BF1, BF2) with two delay feedback buffers (DB1, DB2).
Control logic manages single-path output timing via counters.
Twiddle multiplication is bypassed when the twiddle factor is 1+0j (addr=0).

### Parameterized FFT Architecture (FFTController)

For N-point FFT:
- `num_su = log2(N) // 2` SDF units (Radix-2^2)
- If `log2(N)` is odd, append one SdfUnit2 (Radix-2) stage

Each successive SDF unit has a smaller M value: M = N / 4^i for stage i.
The output of one stage feeds the input of the next.

## FFT Module Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| N | 64 | FFT size (power of 2) |
| width | 16 | Data path width in bits |
| rh | 0/1 | Rounding half for butterfly (0=truncate, 1=round) |
