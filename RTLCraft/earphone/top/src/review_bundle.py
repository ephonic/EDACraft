"""Review-bundle helpers for the Earphone top-level SoC closure."""

from __future__ import annotations

import os


def generate_review_bundle(review_dir: str = "earphone/specs") -> None:
    """Emit the staged review bundle markdown files."""
    print("\n" + "=" * 70)
    print("Review Bundle Generation")
    print("=" * 70)

    os.makedirs(review_dir, exist_ok=True)

    bundles = {
        "01_spec_review.md": """# 01 Spec Review — Smart Earphone SoC

## Modules
| Module | Type | Key Ports | PPA Goals |
|--------|------|-----------|-----------|
| EarphoneRV32 | RV32IM core | imem/dmem buses | <30k NAND2, <0.5mW/MHz |
| EarphoneSIMD16 | Vector ALU | vsrc0/1/2[255:0], vdst | 16 ops/cycle |
| EarphoneFFT256 | FFT accelerator | di_re/im, do_re/im | 256-pt streaming |
| EarphoneQSPI | QSPI XIP | qspi_io[3:0] | memory-mapped flash |
| EarphoneI2C | I2C master | scl, sda | codec/PMIC config |
| EarphoneSRAM256K | SRAM | APB | 256KB single-cycle |
| EarphoneAPBBridge | APB decoder | 8 slave slots | low area |
| EarphoneTop | Top-level | SoC ports | integration |
""",
        "02_behavior_review.md": """# 02 Behavior Review

- RV32IM ISS: architectural state = x0-x31, pc, memory.
- SIMD16: per-lane INT16 ops, predicate mask, FP16 MAC.
- FFT256: DFT with 1/N scaling per stage.
- QSPI: XIP read transaction = cmd + addr + dummy + data.
- I2C: START + 7-bit addr + R/W + byte + ACK + STOP.
- SRAM: single-cycle APB read/write with byte strobe.
- APBBridge: address decode into 1 MB regions.
""",
        "03_cycle_review.md": """# 03 Cycle Review

- RV32IM: 3-stage IF/ID-EX/WB; branch flushes fetch/exec.
- SIMD16: INT16 1-cycle; FP16 MAC 3-cycle pipeline.
- FFT256: streaming R2^2SDF, latency = N + pipeline.
- QSPI: 4-state FSM, ~15-cycle read latency.
- I2C: bit-counter FSM, ~36 cycles/byte.
- SRAM: registered read data, pready after 1 cycle.
- APBBridge: combinational decode.
""",
        "04_microarch_review.md": """# 04 Microarchitecture Review

- CPU: single-issue in-order, no cache, physical memory. Pipeline registers clock-gated by `~stall`.
- M-extension: MUL* single-cycle combinational; DIV/DIVU/REM/REMU use 32-cycle iterative restoring divider for area.
- SIMD: 16 parallel INT16 ALUs + 16 FP16 MAC lanes. Independent `int_ce`/`fp_ce` clock enables per datapath.
- FFT: reuse skills/fft R2^2SDF pipeline.
- QSPI: command/address/data shift register; FSM clock-gated when idle.
- I2C: bit-level shift register with open-drain IO; FSM clock-gated between transactions.
- SRAM: single-port memory array with byte-write mask; clock gated between APB transfers.
- Bridge: one-hot region decoder; `s_psel` reused as peripheral clock-enable downstream.
""",
        "05_structure_review.md": """# 05 Structure Review

```
EarphoneTop
├── EarphoneRV32
│   ├── 3-stage pipeline regs (clock-gated)
│   ├── M-extension unit (operand-isolated multiplier, iterative divider)
│   └── register file
├── EarphoneSIMD16
│   ├── INT16 ALU array (int_ce gated)
│   └── FP16 MAC pipeline (fp_ce gated)
├── EarphoneFFT256 (wraps FFTController)
├── EarphoneQSPI (idle-gated FSM)
├── EarphoneI2C (idle-gated FSM)
├── EarphoneSRAM256K (transfer-gated memory)
└── EarphoneAPBBridge
```
""",
        "06_verification_plan.md": """# 06 Verification Plan

1. Functional tests for ISS (including RV32M MUL/DIV/DIVU/REM/REMU), SIMD16, FFT256.
2. Cycle-level co-simulation against L1.
3. DSL simulation against L2 (SIMD16 vadd, QSPI XIP, SRAM R/W, RV32IM MUL/DIV program).
4. Cross-layer LayerVerifier checks.
5. Verilog lint + co-simulation with iverilog.
6. RISC-V compliance suite (rv32ui-p, rv32um-p), with emphasis on iterative divider.
""",
        "07_lowering_report.md": """# 07 Lowering Report

| Module | SpecIR | BehaviorIR | CycleIR | ArchIR | StructuralIR | DSL | Verilog |
|--------|--------|------------|---------|--------|--------------|-----|---------|
| EarphoneRV32 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneSIMD16 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneFFT256 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneQSPI | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneI2C | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneSRAM256K | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneAPBBridge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| EarphoneTop | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
""",
        "08_ppa_review.md": """# 08 PPA Review

## Power Optimizations

| Module | Technique | Expected Impact |
|--------|-----------|-----------------|
| EarphoneRV32 | Stall-based pipeline clock gating (`core_clk_en`) | Reduced dynamic power during mem/div stalls |
| EarphoneRV32 | Multiplier operand isolation (`is_muldiv`) | Reduced toggle power when not executing RV32M |
| EarphoneRV32 | Iterative restoring divider | ~80% divider area reduction vs combinational |
| EarphoneSIMD16 | Independent INT16/FP16 clock enables | FP16 pipeline idle in audio-only workloads |
| EarphoneSRAM256K | Transfer-gated memory clock | No memory dynamic power between APB accesses |
| EarphoneQSPI | Idle-gated FSM | No toggle when flash is idle |
| EarphoneI2C | Idle-gated FSM | No toggle between I2C transactions |

## Performance Notes

- MUL* remains single-cycle; DIV/REM is 32-cycle iterative (area/power trade-off).
- SIMD throughput unchanged: 16 INT16 ops/cycle, 1 FP16 MAC result every 3 cycles.
- SRAM remains single-cycle read/write.

## Area Notes

- Iterative divider replaces large combinational divider/remainder tree.
- Clock-gating logic adds small enable-mux overhead; net area expected to decrease after synthesis.

## Synthesis Guidance

- Synthesis tools should infer integrated clock-gating cells (ICG) from `if (clk_en) reg <= next` patterns.
- Mark `core_clk_en`, `int_ce`, `fp_ce`, `sram_ce`, `qspi_ce`, `i2c_ce` as clock-gating enables in the constraints file.
- For deeper power savings, group modules into power domains and add retention cells in v0.2.
""",
    }

    for filename, content in bundles.items():
        with open(os.path.join(review_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    print("  Wrote 01_spec_review.md .. 08_ppa_review.md")


__all__ = ["generate_review_bundle"]
