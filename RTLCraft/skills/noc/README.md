# skills.noc — Network-on-Chip Design Skill

## Project Source

2D mesh NoC router and network infrastructure.

- **Original project**: [bakhshalipour/NoC-Verilog](https://github.com/bakhshalipour/NoC-Verilog)
- **Reference RTL**: `ref_rtl/noc/` in this repository
- **License**: Not specified

## Architecture

- Per-router: RouteFunc → CrossBar → VCAlloc → ST (Switch Traversal) → OutputUnit → InputUnit → Buffer
- Network: mesh of ProcessNode (router + PE)

## DSL Modules

`dsl_modules.py` — 15 DSL Module classes
`models.py` — NoC behavioral models (flit routing, buffer management)
`behaviors.py` — 14 behavior templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
