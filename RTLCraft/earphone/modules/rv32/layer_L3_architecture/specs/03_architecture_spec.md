# EarphoneRV32 — L3 ArchitectureIR Specification

| Document ID | RV32-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 ArchitectureIR |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-14 |
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

See previous layer specification for inputs.

---

## 3. Outputs to Next Layer

See next layer specification for outputs.

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Single-cycle scalar with iterative M-extension | Area/power optimized for earphone-class MCU | DIV/REM take variable cycles |

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
| V-01 | Instruction decode and execution correctness | Directed ISS tests | All RV32IM instructions exercised |

---

## 7. Constraints and Assumptions

### 7.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | RV32IM ISA compliance | Top-level SoC spec |

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
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
