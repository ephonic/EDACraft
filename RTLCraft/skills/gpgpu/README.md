# skills.gpgpu — GPGPU Design Skill

## Project Source

SIMT GPU modeled after the Ventus open-source GPGPU architecture.

- **Original project**: [THU-DSP-LAB/ventus-gpgpu-verilog](https://github.com/THU-DSP-LAB/ventus-gpgpu-verilog)
- **Reference RTL**: `ref_rtl/gpgpu/` in this repository
- **Author**: THU-DSP-LAB / C*Core Technology Co.,Ltd
- **License**: Mulan PSL v2

## Architecture

- CTA Scheduler → Warp Scheduler → Execution Units → Register File
- SIMT execution with configurable warp size and CTA count

## DSL Modules

`dsl_modules.py` — 24 DSL Module classes
`models.py` — Python behavioral simulators
`behaviors.py` — 2 behavior templates (cta_scheduler, warp_scheduler)

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
