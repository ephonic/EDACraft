# EarphoneTop - L3 ArchitectureIR Specification

The top-level architecture contract defines the integrated SoC blocks, APB slot
map, external interfaces, and sign-off invariants consumed by structural and
DSL layers.

## Contract Source

- Source: `earphone/top/layer_L3_architecture/src/arch.py`
- Contract object: `TOP_ARCH`

## Required Checks

- Required modules: RV32, SIMD16, FFT256, QSPI, APB bridge, SRAM, I2C.
- APB decode field: `m_paddr[29:22]`.
- APB slot size: 4 MB.
- Top-level closure remains behind CP0/CP1 approval gates.
