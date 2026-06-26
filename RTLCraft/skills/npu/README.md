# skills.npu — NPU Design Skill

## Project Source

Neural Processing Unit based on a parameterizable FPGA-NPU architecture.

- **Original project**: [intel/fpga-npu](https://github.com/intel/fpga-npu)
- **Reference RTL**: `ref_rtl/fpga-npu/` in this repository
- **Author**: Intel Corporation
- **License**: BSD-3-Clause
- **Note**: Project discontinued by Intel in April 2024

## Architecture

- TopScheduler → MVU (MAC array, NTILE×NDPE) → eVRF (banked VRF) → MFU (activation) → LD (load/store)
- Macro-instruction → micro-instruction decode with configurable array size

## DSL Modules

`dsl_modules.py` — 11 DSL Module classes
`models.py` — NPU behavioral models (MAC array, activation functions)
`behaviors.py` — Generic scheduler and datapath templates

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
