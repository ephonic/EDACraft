# EarphoneQSPI — L2 cycle Specification

| Document ID | QSPI-L2_CYCLE-001 |
|-------------|--------------|
| Layer       | L2 cycle |
| Module      | EarphoneQSPI |
| Version     | 0.1 |
| Date        | 2026-06-15 |
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

See previous layer specification for inputs.

---

## 3. Outputs to Next Layer

See next layer specification for outputs.

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
| 0.1 | 2026-06-15 | RTLCraft Agent | Initial draft. |
