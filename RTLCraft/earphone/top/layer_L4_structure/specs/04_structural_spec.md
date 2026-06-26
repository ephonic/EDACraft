# EarphoneTop - L4 StructuralIR Specification

The structural contract names the concrete top-level instances and the
interfaces that connect the external SoC boundary to APB, QSPI, I2C, CPU memory,
and accelerator blocks.

## Contract Source

- Source: `earphone/top/layer_L4_structure/src/structure.py`
- Contract object: `TOP_STRUCTURE`

## Required Checks

- Every top-level subblock has a module binding and at least one interface.
- APB slot 1 is bound to SRAM.
- APB slot 4 is bound to I2C.
- QSPI and I2C pad bundles remain external top-level interfaces.
