# fundamentals — Standard Library & Basic Tutorials

## Overview

This directory contains the **rtlgen standard component library** and **introductory tutorials**. It is the recommended starting point for anyone new to rtlgen.

## Sub-directories

### `lib/` — Standard Component Library

A copy of `rtlgen/lib.py` for reference. Runtime version is imported via:

```python
from rtlgen import FSM, SyncFIFO, BarrelShifter, LFSR, CRC, Divider
```

| Component | Class | Description |
|-----------|-------|-------------|
| FSM | `FSM` | Declarative state-machine generator with `@fsm.state` decorator |
| Sync FIFO | `SyncFIFO` | Single-clock FIFO (pointer + count based) |
| Async FIFO | `AsyncFIFO` | Cross-clock-domain FIFO (interface placeholder) |
| Round-Robin Arbiter | `RoundRobinArbiter` | Request arbitration |
| Decoder | `Decoder` | n-to-2ⁿ combinational decoder |
| Priority Encoder | `PriorityEncoder` | Lowest-set-bit to binary index |
| Barrel Shifter | `BarrelShifter` | Left/right/rotate shift |
| LFSR | `LFSR` | Galois LFSR with configurable taps |
| CRC | `CRC` | Parallel CRC combinational generator |
| Divider | `Divider` | Unsigned restoring-remainder divider |

### `tutorials/` — Step-by-Step Examples

| File | Topic |
|------|-------|
| `api_demo.py` | Core API walkthrough (Module, Input, Output, Wire, Reg) |
| `lib_demo.py` | How to instantiate FSM, FIFO, Shifter from `rtlgen.lib` |
| `full_adder.py` | Combinational full adder |
| `pipeline_adder.py` | Multi-stage pipelined adder |
| `ram_demo.py` | SRAM / memory instantiation |
| `counter.py` | Synchronous counter with enable/load |
| `sim_counter_demo.py` | Cycle-accurate simulation basics |
| `sim_memory_demo.py` | Memory read/write in simulation |
| `sim_multiclock_demo.py` | Multiple clock domains in simulation |
| `sim_xz_demo.py` | X/Z value handling in simulation |

## Key Patterns

### Async Active-Low Reset

All rtlgen modules use the convention:

```python
@self.seq(self.clk, self.rst_n, reset_async=True, reset_active_low=True)
def _seq():
    with If(self.rst_n == 0):
        self.state <<= 0
    with Else():
        ...
```

### Handshake Interface

```python
self.valid_in  = Input(1, "valid_in")
self.ready_out = Output(1, "ready_out")
self.valid_out = Output(1, "valid_out")
self.ready_in  = Input(1, "ready_in")
```

## See Also

- `../arithmetic/SKILL.md` — Datapath-heavy designs (multipliers, hash functions)
- `../control/SKILL.md` — FSM-centric control logic
