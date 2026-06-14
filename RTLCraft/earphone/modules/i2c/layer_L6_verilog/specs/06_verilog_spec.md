# i2c — L6 verilog Specification

| Document ID | I2C-L6_VERILOG-001 |
|-------------|--------------|
| Layer       | L6 verilog |
| Module      | i2c |
| Version     | 0.1 |
| Date        | 2026-06-14 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
L6 verilog for i2c.

### 1.2 Scope
stub

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

### Notes

- Status: stub


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
| D-01 | emitter.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
