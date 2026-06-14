# 08 PPA Review

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
