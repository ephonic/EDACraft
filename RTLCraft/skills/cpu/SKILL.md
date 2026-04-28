# cpu — Processor Cores & Subsystems

## Overview

CPU designs ranging from simple embedded cores to out-of-order superscalar processors. Includes ALUs, branch predictors, register files, and cache subsystems.

## Status

🚧 **Reserved directory** — Designs will be added in future releases.

## Planned Modules

| Module | Description |
|--------|-------------|
| `RV32ICore` | RISC-V RV32I base integer core |
| `Multiplier` | Booth-encoded / Wallace-tree multiplier |
| `BranchPredictor` | 2-bit saturating counter BHT + BTB |
| `RegisterFile` | 2R1W register file with bypass |
| `InstructionCache` | 4-way set-associative I-cache |

## Design Guidelines

- Follow the **RISC-V ISA** for open-source compatibility
- **Pipeline stages**: IF → ID → EX → MEM → WB
- Use **bypass / forwarding** to resolve RAW hazards

## See Also

- `../fundamentals/SKILL.md` — Basic ALU and FSM tutorials
- `../arithmetic/SKILL.md` — High-performance multiplier designs
