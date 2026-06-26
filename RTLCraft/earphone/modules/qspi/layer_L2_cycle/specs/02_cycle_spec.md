# EarphoneQSPI — L2 cycle Specification

| Document ID | QSPI-L2_CYCLE-001 |
|-------------|--------------|
| Layer       | L2 cycle |
| Module      | EarphoneQSPI |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Cycle-accurate QSPI XIP read FSM with cmd/addr/data states.

### 1.2 Scope
Cycle-accurate protocol and timing behavior of EarphoneQSPI.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `QSPI-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`), plus verification intent `QSPI-L1_BEHAVIOR-TP-001` (`layer_L1_behavior/specs/01_behavior_test_plan.md`) and latest evidence `QSPI-L1_BEHAVIOR-TR-001` (`layer_L1_behavior/specs/01_behavior_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `QSPI-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), `QSPI-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`), and `QSPI-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`) as inputs to `QSPI-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`).

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
| States | idle, cmd, addr, data |
| First Word Latency Cycles | 9 |


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
