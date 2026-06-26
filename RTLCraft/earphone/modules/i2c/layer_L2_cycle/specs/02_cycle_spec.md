# EarphoneI2C — L2 cycle Specification

| Document ID | I2C-L2_CYCLE-001 |
|-------------|--------------|
| Layer       | L2 cycle |
| Module      | EarphoneI2C |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Cycle-accurate I2C master byte controller FSM.

### 1.2 Scope
Cycle-accurate protocol and timing behavior of EarphoneI2C.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `I2C-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`), plus verification intent `I2C-L1_BEHAVIOR-TP-001` (`layer_L1_behavior/specs/01_behavior_test_plan.md`) and latest evidence `I2C-L1_BEHAVIOR-TR-001` (`layer_L1_behavior/specs/01_behavior_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `I2C-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), `I2C-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`), and `I2C-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`) as inputs to `I2C-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`).

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
| States | idle, start, byte, ack, data, stop, finish |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Cycle-accurate simulation and cross-layer equivalence with L1.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Cycle-level timing and protocol compliance | Cycle-context simulation | All states and transitions exercised |

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
| D-01 | cycle.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
