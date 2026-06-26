# EarphoneRV32 — L3 ArchitectureIR Specification

| Document ID | RV32-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 ArchitectureIR |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Capture micro-architectural decisions for the RV32IM core.

### 1.2 Scope
Pipeline organization, execution units, and reset behavior.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `RV32-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `RV32-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `RV32-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `RV32-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `RV32-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `RV32-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `RV32-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneRV32 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Architecture

| Property | Value |
| --- | --- |
| ISA | RV32IM |
| Pipeline | single-cycle scalar with iterative M-extension |
| Stages | IF → ID → EX → MEM → WB |
| Multiplier | iterative 32x32 multiply (MUL/MULH/...) |
| Divider | iterative 32-bit divider (DIV/REM/...) |
| Branch predictor | static not-taken |
| Data memory width | 32 |
| Instruction memory width | 32 |
| Reset PC | 0x00001000 |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests + cross-layer equivalence checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional correctness | Directed tests | All operations exercised |

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
| D-01 | arch.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
