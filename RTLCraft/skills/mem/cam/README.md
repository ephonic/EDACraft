# skills.mem.cam — CAM (Content Addressable Memory)

## Project Source

Content Addressable Memory using SRL and BRAM implementations.

- **Original project**: [alexforencich/verilog-cam](https://github.com/alexforencich/verilog-cam)
- **Reference RTL**: `ref_rtl/cam/` in this repository
- **Author**: Alex Forencich
- **License**: MIT

## Architecture

CAM (selectable style) → CamSRL (SRL-based) or CamBRAM (BRAM-based)
Sub-blocks: PriorityEncoder, RamDP

## DSL Modules

`dsl_modules.py` — 5 DSL Module classes
`models.py` — CAM behavioral model

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
