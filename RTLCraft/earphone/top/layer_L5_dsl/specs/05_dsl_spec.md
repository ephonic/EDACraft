# EarphoneTop - L5 DSL Specification

This layer provides the top-level DSL contract consumed by the L6 Verilog
emitter. It currently wraps `earphone.design_earphone.EarphoneTop` so top-level
integration is addressable from the document-driven package while deeper
migration proceeds.

## Required Checks

- `build_top()` instantiates `EarphoneTop`.
- The instance exposes clock/reset, CPU memory, APB debug, QSPI, and I2C ports.
- The wrapper records its compatibility status for audit visibility.
