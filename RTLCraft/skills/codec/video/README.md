# skills.codec.video — xk265 H.265/HEVC Encoder

## Project Source

xk265 CTU-level H.265/HEVC video encoder developed by VIPcore Group, Fudan University.

- **Original project**: [openasic-org/xk265](https://github.com/openasic-org/xk265)
- **Reference RTL**: `ref_rtl/xk265/` in this repository
- **Copyright**: (C) 2011–2016 VIPcore Group, Fudan University
- **License**: Open source — free for research and production use (see original repository)

## Architecture

38 RTL modules across 9 pipeline stages:
enc_ctrl → prei_top → posi_top → ime_top → fme_top → rec_top → dbsao_top → cabac_top → fetch_top

## DSL Modules

`dsl_modules.py` — 38 DSL Module classes extracted from the reference RTL
`models.py` — 38 cycle-accurate Python behavioral simulators

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
