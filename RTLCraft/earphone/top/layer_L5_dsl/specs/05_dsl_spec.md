# EarphoneTop - L5 DSL Specification

This layer provides the top-level DSL contract consumed by the L6 Verilog
emitter. It owns the `EarphoneTop` implementation and instantiates the CPU,
accelerators, APB bridge, SRAM, QSPI, and I2C module DSLs according to the
top-level L3/L4 contracts.

## Required Checks

- `build_top()` instantiates `EarphoneTop`.
- The instance exposes clock/reset, CPU memory, APB debug, QSPI, and I2C ports.
- `describe()` records implementation status and the canonical L5 source path
  for audit visibility.
