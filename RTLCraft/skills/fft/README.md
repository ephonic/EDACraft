# skills.fft — FFT Accelerator Skill

## Project Source

Radix-2^2 Single-Path Delay Feedback (R2^2SDF) FFT accelerator.

- **Original project**: [nanamake/r22sdf](https://github.com/nanamake/r22sdf)
- **Reference RTL**: `ref_rtl/fft/` in this repository
- **Author**: Nanamaru Namake
- **License**: MIT

## Architecture

FFT_BUTTERFLY → FFT_DELAY_BUFFER → FFT_MULTIPLY → FFT_TWIDDLE → FFT_SDF_UNIT → FFT_CONTROLLER

## DSL Modules

`dsl_modules.py` — 7 DSL Module classes
`models.py` — FFT behavioral models (butterfly, SDF stages)
`behaviors.py` — FFT behavior templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
