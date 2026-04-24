# codec — Encoders, Decoders & Line Codes

## Overview

Line code encoders/decoders and other data-format transformation blocks used in high-speed serial links (PCIe, SATA, DisplayPort, etc.).

## Sub-directories

### `8b10b/` — 8b/10b Line Code

| File | Description |
|------|-------------|
| `decoder_8b10b.py` | 8b/10b decoder with Running Disparity (sequential) |
| `decoder_8b10b_comb.py` | 8b/10b decoder (pure combinational lookup) |

**Key Concepts:**
- **Running Disparity (RD)**: Maintains DC balance by tracking +1/-1 difference between 1s and 0s
- **Control Symbols**: K28.5, K28.1, etc. for comma alignment
- **Lookup Tables**: DATA5_TABLE, DATA3_TABLE, CONTROL_TABLE

## Design Patterns

### Sequential vs Combinational Decoder

- **Sequential**: Maintains RD state across cycles; suitable for continuous streams
- **Combinational**: Outputs decoded result + next RD in one cycle; requires external state register

## See Also

- `../fundamentals/SKILL.md` — Standard library (Decoder, PriorityEncoder)
