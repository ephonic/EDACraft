# EarphoneQSPI — L1 behavior Specification

| Document ID | QSPI-L1_BEHAVIOR-001 |
|-------------|--------------|
| Layer       | L1 behavior |
| Module      | EarphoneQSPI |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Functional model of 32 MB external QSPI Flash with memory-mapped XIP reads.

### 1.2 Scope
Cycle-unaware functional behavior of EarphoneQSPI.

---

## 2. Inputs from Previous Layer

Consumes the module contract `QSPI-MOD-001` and top-level SoC requirements as the seed SpecIR.

---

## 3. Outputs to Next Layer

Emits `QSPI-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`), `QSPI-L1_BEHAVIOR-TP-001` (`layer_L1_behavior/specs/01_behavior_test_plan.md`), and `QSPI-L1_BEHAVIOR-TR-001` (`layer_L1_behavior/specs/01_behavior_test_report.md`) as inputs to `QSPI-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneQSPI as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Flash Size Bytes | 33554432 |
| Read Command | 0xEB (Fast Read Quad I/O) |
| Endianness | Little-endian |


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
