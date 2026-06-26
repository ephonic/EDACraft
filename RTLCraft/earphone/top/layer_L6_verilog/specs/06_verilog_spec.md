# EarphoneTop - L6 Verilog Specification

The L6 top-level Verilog contract emits `earphone_top.v` from the L5 top-level
DSL wrapper.

## Required Checks

- Emitted source contains `module EarphoneTop`.
- Emitted source contains APB debug, QSPI, and I2C top-level ports.
- Optional output directory writes the same source returned by `emit_verilog()`.
