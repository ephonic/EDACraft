# skills.dsp — DSP Accelerator Skill

## Project Source

DSP library including multipliers, I/Q synchronizers, I2S controllers, DDS generators, and CIC filters.

- **Original project**: [alexforencich/verilog-dsp](https://github.com/alexforencich/verilog-dsp)
- **Reference RTL**: `ref_rtl/dsp/` in this repository
- **License**: MIT

## Architecture

- DSP_MULT: 4-stage pipelined signed scalar multiplier
- IQ_JOIN / IQ_SPLIT: AXI-Stream synchronizers
- I2S_CTRL: I2S bus clock generator
- DDS: Sine/cosine generator via ROM lookup
- CIC_DECIMATOR / CIC_INTERPOLATOR: Sample-rate converters

## DSL Modules

`dsl_modules.py` — 12 DSL Module classes
`models.py` — DSP behavioral models
`behaviors.py` — DSP behavior templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
