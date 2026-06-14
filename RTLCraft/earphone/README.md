# Smart Earphone SoC — RTLCraft Design

This directory contains a complete Spec2RTL design for a low-power smart earphone chip.

## Directory Layout

```
earphone/
├── design_spec.md              # Top-level design specification
├── README.md                   # This file
├── design_earphone.py          # Single-file Spec2RTL flow (L1→L2→L3→Verilog)
├── specs/
│   ├── 01_spec_review.md       # SpecIR review
│   ├── 02_behavior_review.md   # BehaviorIR review
│   ├── 03_cycle_review.md      # CycleIR review
│   ├── 04_microarch_review.md  # ArchitectureIR review
│   ├── 05_structure_review.md  # StructuralIR review
│   ├── 06_verification_plan.md # Verification plan
│   ├── 07_lowering_report.md   # Cross-layer lowering report
│   └── 08_ppa_review.md        # PPA optimization review
├── twiddle/
│   ├── twiddle_256_re.hex      # FFT256 twiddle factors (real)
│   └── twiddle_256_im.hex      # FFT256 twiddle factors (imag)
└── verilog/
    ├── earphone_rv32.v         # RV32IM core
    ├── earphone_simd16.v       # 16-lane SIMD ALU
    ├── earphone_fft256.v       # 256-point FFT
    ├── earphone_qspi.v         # QSPI XIP controller
    ├── earphone_i2c.v          # APB I2C master
    ├── earphone_sram256k.v     # 256 KB SRAM
    ├── earphone_apb_bridge.v   # APB decoder
    └── earphone_top.v          # SoC top-level
```

## How to Run

```bash
cd /Users/yangfan/release/EDACraft-main/RTLCraft
python earphone/design_earphone.py
```

This executes the full Spec2RTL flow:
1. Generates FFT256 twiddle tables.
2. Writes the 8-stage review bundle (SpecIR through PPA review).
3. Runs Layer 1 functional tests.
4. Runs Layer 3 DSL simulation tests (including RV32IM MUL/DIV program).
5. Runs cross-layer verification (L1 == L2 == L3) for SIMD16.
6. Generates Verilog for all modules and runs lint.

## Design Highlights

| Module | Description | Reuse / New |
|--------|-------------|-------------|
| `EarphoneRV32` | RV32IM 3-stage in-order core with iterative divider | New (based on hetero_riscv4 template) |
| `EarphoneSIMD16` | 16-lane INT16/FP16 SIMD ALU with per-path clock gating | New |
| `EarphoneFFT256` | 256-point streaming FFT | Reuses `design_scripts/design_fft.py` |
| `EarphoneQSPI` | QSPI XIP flash controller with idle clock gating | New |
| `EarphoneI2C` | APB I2C master with idle clock gating | New |
| `EarphoneSRAM256K` | 256 KB on-chip SRAM with transfer-gated clock | New |
| `EarphoneAPBBridge` | APB4 address decoder | New |
| `EarphoneTop` | SoC integration | New |

## Verification Status

- Layer 1 functional tests: **4/4 PASS**
- Layer 3 DSL simulation tests: **4/4 PASS**
- Cross-layer verification: **1/1 PASS**
- Verilog generation: **9/9 PASS**
- Total Verilog: **~2,431 lines**
- Total lint issues: **32**
- Added `earphone/verilog/fft_controller_256.v` (1,188 lines) — self-contained `FFTController` hierarchy for the 256-point FFT accelerator

## PPA Improvements (v0.2)

Following the Spec2RTL 6-layer IR strategy, the following PPA optimizations have been applied:

1. **Area**: RV32IM `DIV`/`REM` instructions now use a 32-cycle iterative restoring divider instead of a combinational divider, significantly reducing divider area.
2. **Power (CPU)**: Pipeline registers are clock-gated when the core is stalled (`core_clk_en = ~stall`), cutting dynamic power during memory/divide stalls.
3. **Power (SIMD)**: INT16 and FP16 datapaths have independent clock enables; the FP16 MAC pipeline only toggles when occupied.
4. **Power (SRAM)**: The 256 KB memory array only clocks during active APB transfers.
5. **Power (Peripherals)**: QSPI and I2C state machines are clock-gated when idle.
6. **Operand isolation**: RV32M multiplier products are forced to zero when no M-extension instruction is in execute, reducing toggle power.

## Known Limitations

- FP16 MAC is a placeholder approximation; full IEEE-754 FP16 add/mul would be needed for production.
- BTLE PHY is not instantiated in the top-level wrapper in this v0.1; only the CPU/accelerator/peripheral infrastructure is integrated.
- UART/SPI/I2S reuse existing skills; APB register wrappers would be added in v0.2.
- Power-domain controllers and retention flops are not yet modeled in Verilog.

## Next Steps

1. Add RISC-V compliance test suite (rv32ui-p, rv32um-p), especially for the iterative divider.
2. Integrate existing `skills.interfaces.uart`, `skills.interfaces.spi`, `skills.dsp.I2S_*`, `skills.interfaces.btle.BTLE_PHY` via APB wrappers.
3. Add clock/reset/POR and power-domain controller with retention cells.
4. Run synthesis feedback loop with ABC / Yosys to quantify area and power savings.
