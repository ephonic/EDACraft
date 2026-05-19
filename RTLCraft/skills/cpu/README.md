# skills.cpu — CPU Design Skill

## Project Source

RISC-V out-of-order CPU core modeled after the T-Head C910 architecture.

- **Original project**: [T-head-Semi/openc910](https://github.com/T-head-Semi/openc910)
- **Reference RTL**: `ref_rtl/cpu/C910_RTL_FACTORY/` in this repository
- **License**: Apache-2.0

## Architecture

- Frontend: IFU (fetch), IDU (decode), BPU (branch prediction)
- Backend: ALU, LSU, ROB, physical register file, issue queue

## DSL Modules

`dsl_modules.py` — 7 DSL Module classes (C910IFU, C910IDU, C910IU, C910LSU, C910RTU, C910PRegFile, C910Core)
`models.py` — Python behavioral simulators
`behaviors.py` — 8 behavior templates

## Parameters

Use `rtlgen.params.PresetSpecs` for rv32_core, rv64_core, high_perf_core, embedded_core presets,
or `PEParams` fluent builder for custom configurations.

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
