# skills.interfaces.btle — BTLE Controller

## Project Source

Bluetooth Low Energy PHY transceiver.

- **Original project**: [JiaoXianjun/BTLE](https://github.com/JiaoXianjun/BTLE)
- **Reference RTL**: `ref_rtl/BTLE/` in this repository
- **Author**: Xianjun Jiao
- **License**: Apache-2.0

## Architecture

BTLE_PHY → BTLE_TX, BTLE_RX_CORE, CRC24_CORE, SCRAMBLE_CORE, GFSK_MODULATION, GFSK_DEMODULATION

## DSL Modules

`dsl_modules.py` — 15 DSL Module classes
`models.py` — BTLE behavioral models

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
