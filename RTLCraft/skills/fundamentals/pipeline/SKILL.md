# pipeline — Pipeline Primitives & Delay-Matching

## Overview

This directory contains **reusable pipeline primitives** for rtlgen designs: shift registers, valid-gated pipelines, and hierarchical debug probes. It also documents the **cross-module boundary delay** phenomenon that was critical to fixing the `MontgomeryMult384` back-to-back alignment bug.

## Files

| File | Description |
|------|-------------|
| `pipeline.py` | Reference copy of `rtlgen/pipeline.py` (ShiftReg, ValidPipe, DebugProbe, Pipeline engine) |

## Primitives

### `ShiftReg(width, depth, name)`

A simple shift register with async active-low reset. Every cycle the data shifts one stage forward.

```python
from rtlgen.pipeline import ShiftReg

self.delay = ShiftReg(128, 16, "delay_u")
self.instantiate(self.delay, "u_delay",
    port_map={
        "clk": self.clk, "rst_n": self.rst_n,
        "din": self.data_in, "dout": self.data_out
    })
```

- `depth=1`: single register (`din` → `r0` → `dout`, 1-cycle delay)
- `depth=0`: wire-through (`dout <<= din`, 0-cycle delay)

**⚠️ Boundary Delay Warning:**
> When `ShiftReg` is instantiated as a **child submodule**, the rtlgen AST simulator adds **+1 cycle** of boundary delay between parent and child `@seq` blocks. A chain of two `ShiftReg(…, depth=16)` submodules gives **32 cycles** of delay in simulation, not 30.

| Scenario | Delay in Simulation | Delay in Verilog |
|----------|---------------------|------------------|
| Hand-written regs inside same module | `N` cycles | `N` cycles |
| `ShiftReg(width, N)` as submodule | `N` cycles | `N` cycles |
| Two `ShiftReg(width, N)` chained as submodules | `2N` cycles | `2N` cycles |
| `N` hand-written regs + 1 child `@seq` | `N+1` cycles | `N` cycles |

**Design Rule:**
- For **simulation-correct designs**, keep delay lines inside the **same module** as the consumer, or account for +1 per submodule boundary.
- `ShiftReg` is safe to use as a submodule **when it is the only pipeline stage** between source and sink (no additional boundary effects).

---

### `ValidPipe(width, name)`

Single pipeline stage with **valid gating**. Captures `din` only when `valid_in` is high. Output holds the last captured value.

```python
from rtlgen.pipeline import ValidPipe

stage = ValidPipe(128, "stage_u")
self.instantiate(stage, "u_stage",
    port_map={
        "clk": self.clk, "rst_n": self.rst_n,
        "din": self.in_data, "valid_in": self.in_valid,
        "dout": self.out_data, "valid_out": self.out_valid
    })
```

Use cases:
- Feed-forward pipelines where each stage must only advance on valid data
- Avoiding bubble corruption when `ready` is tied high (no back-pressure)

---

### `DebugProbe(sim)`

Hierarchical signal probe for `rtlgen.Simulator`. Eliminates the need to manually navigate `_subsim_info` tuples.

```python
from rtlgen.pipeline import DebugProbe

probe = DebugProbe(sim)

# Read top-level signal
probe.get("o_valid")

# Read submodule signal by fuzzy name
path, subsim = probe.find_subsim("u_r0")
probe.get("qm2", path=path)

# Bulk print from all matching submodules
probe.print_all(signals=["valid_in", "out_valid"], path_prefix="u_r0")
```

---

## Case Study: MontgomeryMult384 Delay Alignment

### The Bug

`RedUnit128` (SOS reduction unit) has an internal latency of ~13 cycles. Its output `out_Z0..Z3` must align with the delayed `M` (modulus) at the final conditional-subtraction stage.

**Original design:**
- `M` was stored in a single register `s8_M_r` at the KO-3 capture stage
- 15 cycles later, `r0_valid` went high, but `s8_M_r` already held the **next input's M**
- Random-vector tests failed because each reduction used the wrong modulus

**Root cause:**
- `M` is consumed 3 times (r0, r1, r2 reduction + final subtraction)
- Each consumption point is separated by **15 cycles** from the previous stage
- A single register cannot serve back-to-back transactions

**Fix:**
```
s7_M ──► s8_M_shift[0..15] ──► r0_M_shift[0..15] ──► r1_M_shift[0..15] ──► r2_M_r
          (16 stages)            (16 stages)           (16 stages)
```

- `s8_M_shift`: matches `s8_valid → r0_valid` delay (15 internal + 1 boundary)
- `r0_M_shift`: matches `r0_valid_r → r1_valid` delay
- `r1_M_shift`: matches `r1_valid_r → r2_valid` delay
- `r2_M_r`: captures `r1_M_shift[15]` when `r2_valid` fires

**Key insight:**
> In a pipelined design with **N-cycle internal latency** and a **child `@seq` consumer**, the parent needs a **(N+1)-stage delay line** to align data with the child's output valid window. The `+1` comes from the AST simulator's cross-module boundary delay.

### Alignment Checklist

When designing a pipeline with submodule multipliers or reduction units:

1. **Measure the submodule latency** with a single input (from `valid_in` to `valid_out`)
2. **Account for boundary delay**: if the consumer is a child `@seq`, add +1 cycle
3. **Delay all sideband data** (M, Mp, control signals) by the same number of stages
4. **Use `DebugProbe`** to verify alignment with back-to-back inputs:
   - Input 0's `M` should arrive at the consumer exactly when input 0's `valid_out` fires
   - Input 1's `M` should not leak into input 0's computation window
5. **Test random vectors** with **different moduli per input** — this catches M misalignment that constant-M tests miss

---

## See Also

- `../lib/SKILL.md` — Standard component library (FSM, FIFO)
- `../../arithmetic/SKILL.md` — MontgomeryMult384 detailed architecture
- `rtlgen/pipeline.py` — Runtime source (Pipeline engine, Handshake)
