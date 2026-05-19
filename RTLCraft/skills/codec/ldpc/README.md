# skills.codec.ldpc — LDPC Decoder

WiMax 802.16e LDPC decoder using Min-Sum algorithm with parity-check termination.

## Project Source

- **Original project**: [crboth/LDPC_Decoder](https://github.com/crboth/LDPC_Decoder)
- **Reference RTL**: `ref_rtl/LDPC_Decoder/` in this repository
- **License**: Not specified

## Architecture

LDPC_Decoder (top) → VarNode[N], CheckNode[M], QuantizedAdder, QuantizedSubber, Comparator

## DSL Modules

`dsl_modules.py` — 6 DSL Module classes
`models.py` — 3 Python behavioral simulators

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
