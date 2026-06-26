# ThorLSU — L1 behavior Specification

| Document ID | LSU-L1_BEHAVIOR-001 |
|-------------|--------------|
| Layer       | L1 behavior |
| Module      | ThorLSU |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Vector load/store unit functional reference (req/response handshake).

### 1.2 Scope
Cycle-unaware functional behavior of ThorLSU.

---

## 2. Inputs from Previous Layer

Consumes the module contract `LSU-MOD-001` and the Thor-GPGPU top-level SoC requirements as the seed SpecIR.

---

## 3. Outputs to Next Layer

Emits `LSU-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`) as input to `LSU-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorLSU as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Data Width | 256 |
| Addr Width | 32 |
| Ops | load(0), store(1) |

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
| C-01 | Module specification compliance | Thor-GPGPU top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Two's-complement integer / IEEE-754 FP semantics | Matches the Thor GPGPU datapath |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | behavior.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
