# 04 Microarchitecture Review

- CPU: single-issue in-order, no cache, physical memory. Pipeline registers clock-gated by `~stall`.
- M-extension: MUL* single-cycle combinational; DIV/DIVU/REM/REMU use 32-cycle iterative restoring divider for area.
- SIMD: 16 parallel INT16 ALUs + 16 FP16 MAC lanes. Independent `int_ce`/`fp_ce` clock enables per datapath.
- FFT: reuse skills/fft R2^2SDF pipeline.
- QSPI: command/address/data shift register; FSM clock-gated when idle.
- I2C: bit-level shift register with open-drain IO; FSM clock-gated between transactions.
- SRAM: single-port memory array with byte-write mask; clock gated between APB transfers.
- Bridge: one-hot region decoder; `s_psel` reused as peripheral clock-enable downstream.
