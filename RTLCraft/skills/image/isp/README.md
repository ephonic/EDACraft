# skills.image.isp — Image Signal Processor

## Project Source

Bayer→RGB→YUV ISP pipeline based on the Infinite-ISP v1.1 reference model.

- **Original project**: [10x-Engineers/Infinite-ISP](https://github.com/10x-Engineers/Infinite-ISP)
- **Reference RTL**: `ref_rtl/ISP/` in this repository
- **Author**: 10xEngineers Pvt Ltd
- **License**: Apache-2.0

## Pipeline Stages

- **Bayer**: Crop → DPC → BLC → OECF → DG → LSC → BNR → WB
- **RGB**: Demosaic → CCM → Gamma
- **YUV**: CSC → LDCI → Sharpen → NR2D → Scale → YUV
- **Stats**: AWB, AE
- **Config**: APB register bank (32×32-bit)

## DSL Modules

`dsl_modules.py` — 23 DSL Module classes
`models.py` — Python behavioral simulators
`behaviors.py` — 22 cycle-accurate behavior templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
