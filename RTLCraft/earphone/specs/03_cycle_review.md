# 03 Cycle Review

- RV32IM: 3-stage IF/ID-EX/WB; branch flushes fetch/exec.
- SIMD16: INT16 1-cycle; FP16 MAC 3-cycle pipeline.
- FFT256: streaming R2^2SDF, latency = N + pipeline.
- QSPI: 4-state FSM, ~15-cycle read latency.
- I2C: bit-counter FSM, ~36 cycles/byte.
- SRAM: registered read data, pready after 1 cycle.
- APBBridge: combinational decode.
