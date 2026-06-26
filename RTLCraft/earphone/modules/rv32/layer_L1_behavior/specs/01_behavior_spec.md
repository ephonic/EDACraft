# EarphoneRV32 — L1 BehaviorIR Specification

| Document ID | RV32-L1_BEHAVIOR-001 |
|-------------|--------------|
| Layer       | L1 BehaviorIR |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Define the cycle-unaware RV32IM instruction-set simulator (ISS) used as the golden reference for all downstream layers and RTL verification.

### 1.2 Scope
Covers RV32I base integer instructions plus RV32M multiply/divide extensions. Memory is modeled as a sparse byte-addressable map.

---

## 2. Inputs from Previous Layer

Consumes the module contract `RV32-MOD-001` and top-level SoC requirements as the seed SpecIR.

---

## 3. Outputs to Next Layer

Emits `RV32-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`), `RV32-L1_BEHAVIOR-TP-001` (`layer_L1_behavior/specs/01_behavior_test_plan.md`), and `RV32-L1_BEHAVIOR-TR-001` (`layer_L1_behavior/specs/01_behavior_test_report.md`) as inputs to `RV32-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneRV32 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### ISA

RV32IM

### Register Width (XLEN)

32

### Register File

| Property | Value |
| --- | --- |
| Register count | 32 (x0–x31) |
| Width | 32 bits |
| x0 behavior | Hardwired to zero |
| Program counter | 32 bits, default reset = 0x1000 |

### Memory Model

| Property | Value |
| --- | --- |
| Address space | 32-bit byte-addressable |
| Endianness | Little-endian |
| Access widths | Byte, halfword, word |
| Implementation | Sparse Python dict (uninitialized reads return 0) |

### Instructions

| Instruction | Format | Description |
| --- | --- | --- |
| LUI | U-type | Load upper immediate |
| AUIPC | U-type | Add upper immediate to PC |
| JAL | J-type | Jump and link |
| JALR | I-type | Jump and link register |
| BEQ | B-type | Branch if equal |
| BNE | B-type | Branch if not equal |
| BLT | B-type | Branch if less than |
| BGE | B-type | Branch if greater or equal |
| BLTU | B-type | Branch if less than unsigned |
| BGEU | B-type | Branch if greater or equal unsigned |
| LB | I-type | Load byte |
| LH | I-type | Load halfword |
| LW | I-type | Load word |
| LBU | I-type | Load byte unsigned |
| LHU | I-type | Load halfword unsigned |
| SB | S-type | Store byte |
| SH | S-type | Store halfword |
| SW | S-type | Store word |
| ADDI | I-type | Add immediate |
| SLTI | I-type | Set less than immediate |
| SLTIU | I-type | Set less than immediate unsigned |
| XORI | I-type | XOR immediate |
| ORI | I-type | OR immediate |
| ANDI | I-type | AND immediate |
| SLLI | I-type | Shift left logical immediate |
| SRLI | I-type | Shift right logical immediate |
| SRAI | I-type | Shift right arithmetic immediate |
| ADD | R-type | Add |
| SUB | R-type | Subtract |
| SLL | R-type | Shift left logical |
| SLT | R-type | Set less than |
| SLTU | R-type | Set less than unsigned |
| XOR | R-type | XOR |
| SRL | R-type | Shift right logical |
| SRA | R-type | Shift right arithmetic |
| OR | R-type | OR |
| AND | R-type | AND |
| MUL | R-type | Multiply (RV32M) |
| MULH | R-type | Multiply high (RV32M) |
| MULHSU | R-type | Multiply high signed/unsigned (RV32M) |
| MULHU | R-type | Multiply high unsigned (RV32M) |
| DIV | R-type | Divide (RV32M) |
| DIVU | R-type | Divide unsigned (RV32M) |
| REM | R-type | Remainder (RV32M) |
| REMU | R-type | Remainder unsigned (RV32M) |
| EBREAK | I-type | Environment break (halt simulation) |

### Tests

| Test Name | Description |
| --- | --- |
| test_add_sub | Validate add sub. |
| test_branch | Validate branch. |
| test_div_by_zero | Validate div by zero. |
| test_load_store | Validate load store. |
| test_mul | Validate mul. |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests against the functional reference model.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional correctness of behavior model | Directed pytest cases | All operations and corner cases exercised |

---

## 7. Constraints and Assumptions

### 7.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | Module specification compliance | Top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian byte ordering | Matches target bus architecture |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | behavior.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
