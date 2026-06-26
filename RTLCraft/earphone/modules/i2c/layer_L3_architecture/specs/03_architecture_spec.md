# EarphoneI2C — L3 architecture Specification

| Document ID | I2C-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | EarphoneI2C |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
APB-programmable single-byte I2C master controller.

### 1.2 Scope
Micro-architectural decisions for EarphoneI2C.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `I2C-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `I2C-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `I2C-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `I2C-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `I2C-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `I2C-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `I2C-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneI2C as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Pipeline | register-programmed byte-controller state machine |
| States | idle, start, byte, ack, data, stop, finish |
| Apb Addr Width | 12 |
| Transaction Data Width | 8 |
| Host Protocol | APB4 register access to open-drain I2C pin control |
| Timing | APB accesses complete immediately; byte transfers run through a start/address/ack/data/stop FSM. |
| Invariants | Register writes program ctrl and data before the byte controller launches., Open-drain outputs are driven through scl_oe and sda_oe rather than direct push-pull pins., Read and write directions share the same byte-level controller state machine. |


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
