# skills.mem.ddr3 — DDR3 Controller

## Project Source

DDR3 memory controller with DFI sequencer and JEDEC timing compliance.

- **Original project**: [ultraembedded/core_ddr3_controller](https://github.com/ultraembedded/core_ddr3_controller)
- **Reference RTL**: `ref_rtl/core_ddr3_controller/` in this repository
- **Author**: ultraembedded
- **License**: Apache-2.0

## Architecture

DDR3Controller → DDR3Core (FSM: INIT/IDLE/ACT/READ/WRITE/PRE/REF) → DDR3DFISeq, DDR3FIFO

## DSL Modules

`dsl_modules.py` — 4 DSL Module classes
`models.py` — DDR3 behavioral models with timing
`behaviors.py` — memory_controller, dfi_sequencer templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
