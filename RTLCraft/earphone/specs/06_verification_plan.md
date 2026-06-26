# 06 Verification Plan

1. Functional tests for ISS (including RV32M MUL/DIV/DIVU/REM/REMU), SIMD16, FFT256.
2. Cycle-level co-simulation against L1.
3. DSL simulation against L2 (SIMD16 vadd, QSPI XIP, SRAM R/W, RV32IM MUL/DIV program).
4. Cross-layer LayerVerifier checks.
5. Verilog lint + co-simulation with iverilog.
6. RISC-V compliance suite (rv32ui-p, rv32um-p), with emphasis on iterative divider.
