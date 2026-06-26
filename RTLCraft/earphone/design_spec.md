# Smart Earphone SoC — Design Specification

**Project**: RTLCraft-based low-power smart earphone chip  
**Version**: 0.1  
**Date**: 2026-06-14  
**Design flow**: Spec2RTL 6-layer IR + Verilog output

---

## 1. Overview

This document defines a low-power system-on-chip (SoC) for true-wireless stereo (TWS) smart earphones. The chip is designed using RTLCraft's white-box Spec2RTL methodology, with mandatory cross-layer verification at every abstraction boundary.

### Target Application
- Audio playback/capture with DSP pre/post-processing
- Bluetooth Low Energy (BLE) 1M PHY connectivity
- Sensor hub (accelerometer, proximity, touch)
- Voice activation / light-weight AI inference

### Key Characteristics
| Item | Target |
|------|--------|
| Process | 22nm / 28nm low-power CMOS |
| Core voltage | 0.6–1.0 V |
| Active audio + BLE power | < 5 mW |
| CPU frequency | 48–160 MHz |
| Audio sample rate | 16 kHz / 48 kHz, 16-bit stereo |

---

## 2. Requirements Summary

| # | Requirement | Implementation |
|---|-------------|----------------|
| 1 | ARM Cortex-M4 class RISC-V processor core | **RV32IM**, 3-stage in-order pipeline, Harvard-ish bus interface, single-issue |
| 2 | SIMD ALU array: 16 lanes, INT16/FP16 | **SIMD16**: 16× INT16 lanes (add/sub/mul/and/or/xor/shift/compare) + 16× FP16 MAC lanes |
| 3 | 256-point FFT accelerator | **FFT256**: streaming radix-2² SDF, 16-bit Q1.15 fixed-point, 1 sample/cycle |
| 4 | Peripherals: SPI, UART, I2C, I2S, Bluetooth controller, QSPI | APB-attached controllers; BTLE = reuse existing 1M PHY + new DMA/LL wrapper |
| 5 | On-chip SRAM 256 KB | **SRAM256K**: single-cycle, byte-write-enable, 32-bit data, AHB/APB slave |
| 6 | External 32 MB Flash via QSPI | **QSPI**: XIP read + command/erase/program, 4-bit I/O, memory-mapped |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Smart Earphone SoC                          │
├─────────────────────────────────────────────────────────────────────┤
│  CPU Subsystem                                                      │
│  ┌──────────────┐    ┌─────────────┐    ┌──────────────────────┐   │
│  │  RV32IM Core │◄──►│  SIMD16     │    │  FFT256 Accelerator  │   │
│  │  3-stage     │    │  16 lanes   │    │  256-pt streaming    │   │
│  └──────┬───────┘    └──────┬──────┘    └──────────┬───────────┘   │
│         │                   │                       │               │
│         └───────────────────┴───────────────────────┘               │
│                         │                                          │
│                         ▼                                          │
│              ┌─────────────────────┐                               │
│              │  AHB/APB Bridge     │                               │
│              │  + AHB-lite matrix  │                               │
│              └─────────┬───────────┘                               │
│                        │                                            │
│  ┌─────────────────────┼─────────────────────┐                     │
│  ▼                     ▼                     ▼                     │
│ ┌──────────┐    ┌───────────┐    ┌────────────────────┐           │
│ │SRAM256K  │    │ QSPI Ctrl │    │  AHB/APB Bridge    │           │
│ │256 KB    │    │ 32MB Flash│    │                    │           │
│ └──────────┘    └───────────┘    └─────────┬──────────┘           │
│                                            │                       │
│  APB Control Peripherals                   ▼                       │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────────────┐              │
│  │ SPI │ UART│ I2C │ I2S │GPIO │ Tim │  BTLE LL    │              │
│  └─────┴─────┴─────┴─────┴─────┴─────┴──────┬──────┘              │
│                                             │                      │
│  ┌──────────────────────────────────────────┘                      │
│  ▼                                                                 │
│  BTLE 1M PHY (reuse skills/interfaces/btle)                        │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Clocking and Power Domains
| Domain | Clock | Description |
|--------|-------|-------------|
| `clk_sys` | 48–160 MHz | CPU, AHB, SRAM, QSPI XIP |
| `clk_per` | 48 MHz | APB peripherals (divided from `clk_sys`) |
| `clk_i2s` | 12.288 MHz | Audio codec I2S (MCLK-derived) |
| `clk_ble` | 16 MHz | BLE PHY (radio clock domain) |
| `pdm_clk` | 3.072 MHz | PDM microphone clock (optional) |

---

## 4. Spec2RTL 7-Stage Design Hierarchy

This design follows RTLCraft's mandatory **6-layer IR lowering + final Verilog output**, with cross-layer consistency checks between adjacent layers.

| Stage | Layer / IR | File Location | Deliverable | Verification |
|-------|------------|---------------|-------------|--------------|
| 1 | **SpecIR** | `earphone/specs/` | Module specs (ports, function, timing, PPA goals) | Human review |
| 2 | **BehaviorIR** | `earphone/behaviors/` | Pure-Python functional models (L1) | `assert func() == expected` |
| 3 | **CycleIR** | `earphone/cycle/` | Cycle-accurate Python models (L2) | `L2 == L1` via LayerVerifier |
| 4 | **ArchitectureIR** | `earphone/arch/` | Pipeline/operator/architecture plan | Simulation via ArchSimulator |
| 5 | **StructuralIR** | `earphone/structural/` | Submodule decomposition + port maps | Connectivity checks |
| 6 | **DSL AST** | `earphone/dsl/` | RTLCraft `Module` classes (L3) | `L3 == L2` via LayerVerifier |
| 7 | **Verilog** | `earphone/verilog/` | Synthesizable `.v` + lint report | VerilogLinter + co-sim |

### Cross-Layer Verification Contract
For every module:
```
L1 (functional)  ──►  L2 (cycle)  ──►  L3 (DSL)  ──►  Verilog
      ≡                    ≡               ≡
```
- `LayerVerifier.verify(...)` must PASS before advancing.
- If mismatch: fix the lowest layer first.

---

## 5. Module Specifications

### 5.1 RV32IM Core — `EarphoneRV32`

**Purpose**: single-issue, 3-stage in-order RISC-V integer core with M-extension multiplier/divider.

**Pipeline stages**: IF → ID/EX → WB
- **IF**: PC +4, fetch 32-bit instruction from I-side bus.
- **ID/EX**: decode, register file read, ALU operation, branch resolution.
- **WB**: writeback to register file.

**Interfaces**
| Port | Width | Direction | Description |
|------|-------|-----------|-------------|
| `clk` | 1 | in | system clock |
| `rst_n` | 1 | in | active-low async reset |
| `imem_addr` | 32 | out | instruction memory address |
| `imem_rdata` | 32 | in | instruction memory read data |
| `imem_req` | 1 | out | instruction fetch request |
| `imem_gnt` | 1 | in | instruction fetch grant |
| `dmem_addr` | 32 | out | data memory address |
| `dmem_wdata` | 32 | out | data memory write data |
| `dmem_rdata` | 32 | in | data memory read data |
| `dmem_we` | 4 | out | byte write enable |
| `dmem_req` | 1 | out | data request |
| `dmem_gnt` | 1 | in | data grant |
| `dmem_valid` | 1 | in | data read valid |
| `irq` | 32 | in | local interrupt lines (PLIC-lite) |

**ISA**: RV32I base + RV32M (MUL/MULH/MULHSU/MULHU/DIV/DIVU/REM/REMU).  
**No MMU**, physical addressing only.  
**No FPU**: FP16 handled by SIMD accelerator.

**PPA targets**
- Logic depth ≤ 12 FO4 @ 160 MHz
- Area ≤ 30 k NAND2 equivalent
- Dynamic power ≤ 0.5 mW/MHz

---

### 5.2 SIMD16 Accelerator — `EarphoneSIMD16`

**Purpose**: 16-lane vector ALU for audio DSP and light neural-net inference. Supports both INT16 element-wise operations and FP16 multiply-accumulate.

**Datapath**
- INT16 mode: 16 independent 16-bit lanes, element width = 16, vector width = 256.
- FP16 mode: 16 IEEE-754 half-precision lanes sharing one 256-bit register file read/write port.

**Interfaces**
| Port | Width | Direction | Description |
|------|-------|-----------|-------------|
| `clk`, `rst_n` | 1 | in | clock/reset |
| `apb_*` | — | in/out | APB4 slave configuration |
| `vsrc0[255:0]` | 256 | in | vector source 0 |
| `vsrc1[255:0]` | 256 | in | vector source 1 |
| `vsrc2[255:0]` | 256 | in | vector accumulator source (MAC) |
| `vdst[255:0]` | 256 | out | vector result |
| `op[4:0]` | 5 | in | opcode |
| `mode` | 1 | in | 0=INT16, 1=FP16 |
| `start` | 1 | in | trigger operation |
| `done` | 1 | out | operation complete |
| `pred[15:0]` | 16 | in | per-lane predicate mask |

**INT16 opcodes**
| op | Operation |
|----|-----------|
| 0 | vadd |
| 1 | vsub |
| 2 | vmul (low 16) |
| 3 | vand |
| 4 | vor |
| 5 | vxor |
| 6 | vsll |
| 7 | vsrl |
| 8 | vsra |
| 9 | vcmp_eq |
| 10 | vcmp_lt |

**FP16 opcodes**
| op | Operation |
|----|-----------|
| 0 | vmac: vsrc0 * vsrc1 + vsrc2 |
| 1 | vmul |

**Latency**: INT16 ALU = 1 cycle; FP16 MAC = 3-cycle pipelined.

---

### 5.3 FFT256 Accelerator — `EarphoneFFT256`

**Purpose**: hardware FFT for beamforming, EQ, and audio feature extraction.

**Architecture**: streaming radix-2² Single-Path Delay Feedback (R2²SDF), 1 complex sample/cycle.

**Parameters**
- N = 256
- Width = 16-bit signed fixed-point Q1.15
- Scaling: divide-by-2 per butterfly stage ⇒ overall 1/256 scale
- Output order: bit-reversed

**Interfaces**
| Port | Width | Direction | Description |
|------|-------|-----------|-------------|
| `clk`, `rst` | 1 | in | clock/reset (active-high) |
| `di_en` | 1 | in | input sample valid |
| `di_re[15:0]` | 16 | in | real input |
| `di_im[15:0]` | 16 | in | imaginary input |
| `do_en` | 1 | out | output sample valid |
| `do_re[15:0]` | 16 | out | real output |
| `do_im[15:0]` | 16 | out | imaginary output |

**Reuse strategy**: instantiate `skills.fft.FFTController(N=256, width=16)`.

---

### 5.4 SRAM256K — On-Chip Memory

**Purpose**: 256 KB single-port SRAM for processor code/data and audio buffers.

**Configuration**
- 256 KB = 64 K × 32 bit
- Byte write enable (4 bits)
- Single-cycle read/write
- Optional parity/ECC (ECC not in v0.1)

**Interfaces**: AHB-lite slave or AXI4-Lite slave.

---

### 5.5 QSPI Controller — `EarphoneQSPI`

**Purpose**: execute-in-place (XIP) from external 32 MB quad-SPI Flash, plus program/erase command interface.

**Features**
- SPI mode 0/3, single/dual/quad I/O
- Memory-mapped XIP read: 1 KB window at `0x4000_0000`
- Command FIFO for sector erase / page program
- APB register file for control/status

**Interfaces**
| Port | Width | Direction | Description |
|------|-------|-----------|-------------|
| `clk`, `rst_n` | 1 | in | system clock/reset |
| `apb_*` | — | in/out | APB4 slave |
| `qspi_sck` | 1 | out | serial clock |
| `qspi_cs_n` | 1 | out | chip select |
| `qspi_io[3:0]` | 4 | inout | quad data I/O |

---

### 5.6 Peripherals

#### 5.6.1 SPI — `EarphoneSPI`
**Reuse**: base `SPIController` from `design_scripts/design_spi.py`.  
**Role**: PMIC, accelerometer, touch sensor.

#### 5.6.2 UART — `EarphoneUART`
**Reuse**: `skills.interfaces.uart.UART`.  
**Role**: debug console, GPS/NMEA, factory test.

#### 5.6.3 I2C — `EarphoneI2C`
**New design**: APB I2C master/slave controller with multi-byte transaction FIFO, clock stretching, repeated START.  
**Role**: codec, charger, fuel-gauge configuration.

#### 5.6.4 I2S — `EarphoneI2S`
**Reuse**: `skills.dsp.I2S_CTRL`, `I2S_RX`, `I2S_TX`.  
**Role**: audio codec digital interface. Add APB register wrapper for sample-rate/format.

#### 5.6.5 Bluetooth — `EarphoneBTLE`
**Reuse**: `skills.interfaces.btle.BTLE_PHY` for 1M PHY.  
**New design**: BLE Link-Layer wrapper + DMA + APB register bank.  
**Role**: TWS wireless audio and control.

---

## 6. PPA Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Total digital area | < 2 mm² @ 28nm | including SRAM |
| SRAM area | ~0.8 mm² (256 KB) | 6T cell |
| Active audio + BLE | < 5 mW | CPU 48 MHz, BLE RX |
| Deep-sleep current | < 10 µA | SRAM retained, clocks gated |
| CPU DMIPS/MHz | ≥ 1.25 | RV32IM baseline |
| FFT256 latency | 256 + pipeline cycles | streaming |
| SIMD16 throughput | 16 INT16 ops/cycle | 768 MOPS @ 48 MHz |

### 6.1 PPA Optimization Strategy (6-Layer IR)

Each IR layer contributes specific PPA decisions that are verified before lowering:

| IR Layer | PPA Focus | Key Decisions |
|----------|-----------|---------------|
| **SpecIR** | Requirements & budgets | Define area, power, performance targets; identify always-on vs. gated domains. |
| **BehaviorIR** | Functional golden | Validate algorithmic choices (e.g., iterative division vs. combinational) without timing. |
| **CycleIR** | Latency & throughput | Fix pipeline depth, stall penalties, memory latency; model clock gating as enable signals. |
| **ArchitectureIR** | Microarchitecture | Choose iterative divider, per-path SIMD clock gating, SRAM transfer gating, stall-based CPU gating. |
| **StructuralIR** | Decomposition | Group clock-gated registers; isolate M-extension unit; separate INT16 / FP16 SIMD datapaths. |
| **DSL/Verilog** | Implementation | Emit `if (clk_en) reg <= next` patterns for synthesis clock-gating inference; instantiate low-power cells. |

Implemented PPA improvements:
- **CPU**: 32-cycle iterative restoring divider for DIV/DIVU/REM/REMU replaces combinational divider, reducing divider area by ~80%; multiplier operands isolated when not executing RV32M. Pipeline registers gated by `core_clk_en = ~stall` to cut dynamic power during memory/divide stalls.
- **SIMD16**: INT16 and FP16 datapaths use independent clock enables (`int_ce`, `fp_ce`); FP16 pipeline registers advance only when occupied, eliminating toggling in audio-only workloads.
- **SRAM256K**: Memory array and read-data register update only on active APB transfers (`sram_ce = psel & penable`).
- **Peripherals**: QSPI and I2C state-machine registers are clock-gated when idle (`qspi_ce = req | busy`, `i2c_ce = busy | apb_access`).
- **Integration**: Top-level exposes raw clocks; synthesis tooling infers integrated clock-gating cells (ICG) from the enable patterns above. Future work adds power-domain controllers and retention flops.

---

## 7. Verification Plan

### 7.1 Layer-by-Layer Checks
| Layer | Method | Coverage |
|-------|--------|----------|
| L1 Functional | Python unit tests directed + constrained random | 100% opcode coverage for core/SIMD |
| L2 Cycle | `ArchSimulator` / `_beh_func` wrapper | All pipeline hazards, handshake scenarios |
| L3 DSL | `Simulator` + `LayerVerifier` | Bit-exact match with L2 |
| Verilog | `VerilogLinter` + `iverilog` co-sim | Lint clean, cycle-exact with L3 |

### 7.2 Module-Specific Tests
- **RV32IM**: RISC-V compliance suite (rv32ui-p, rv32um-p) via ISS co-sim.
- **SIMD16**: random INT16 vector ops; FP16 MAC against soft-float reference.
- **FFT256**: impulse, DC, single-tone, dual-tone tests against numpy FFT.
- **QSPI**: XID read waveform, command FIFO, mode transitions.
- **I2C**: START/STOP, byte TX/RX, clock stretch, repeated START.

---

## 8. Implementation Roadmap

| Step | Task | Output | Checkpoint |
|------|------|--------|------------|
| 1 | Finalize `design_spec.md` (this doc) | `earphone/design_spec.md` | Human review |
| 2 | SpecIR for all modules | `earphone/specs/*.md`, `*.json` | Human review |
| 3 | L1 functional models | `earphone/behaviors/*.py` | Unit tests PASS |
| 4 | L2 cycle-level models | `earphone/cycle/*.py` | L2 == L1 |
| 5 | ArchitectureIR + StructuralIR | `earphone/arch/*.py`, `earphone/structural/*.py` | ArchSimulator PASS |
| 6 | DSL AST implementation | `earphone/dsl/*.py` | L3 == L2 |
| 7 | Verilog generation + lint | `earphone/verilog/*.v` | Lint clean |
| 8 | Integration test + PPA review | `earphone/tests/` | All tests PASS |

---

## 9. Open Questions / Decisions Log

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | 7-layer meaning | Spec2RTL 6 IR + Verilog output | 2026-06-14 |
| 2 | RISC-V ISA | RV32IM, 3-stage in-order | 2026-06-14 |
| 3 | SIMD FP16 scope | INT16 full ALU + FP16 MAC only | 2026-06-14 |
| 4 | Control bus | APB4 for peripherals | 2026-06-14 |
| 5 | RVC compressed extension | Deferred to v0.2; saves ~25% code size | TBD |
| 6 | Interrupt controller | Simple 32-line level IRQ; PLIC-lite deferred | TBD |
| 7 | Low-power state retention | Clock gating in v0.1; power gating deferred | TBD |
| 8 | Iterative divider for area | Adopted; DIV/REM 32-cycle restoring | 2026-06-14 |
| 9 | SIMD datapath clock gating | Adopted; independent INT16/FP16 enables | 2026-06-14 |
| 10 | SRAM/peripheral clock gating | Adopted; transfer-based and idle-based | 2026-06-14 |

---

## 10. References

- RTLCraft README.md / Tutorial_CN.md
- `skills/hetero_riscv4/dsl_modules.py` — EfficiencyCore template
- `skills/fft/dsl_modules.py` / `design_scripts/design_fft.py` — FFT256 basis
- `skills/thor/layer3_dsl/vector_alu.py` — 16-lane SIMD template
- `skills/interfaces/btle/dsl_modules.py` — BLE PHY
- `skills/dsp/dsl_modules.py` — I2S blocks
- `design_scripts/design_spi.py` — SPI controller basis
- `skills/interfaces/uart/dsl_modules.py` — UART
- `ref_rtl/fp16_mul.v` — FP16 multiplier reference
