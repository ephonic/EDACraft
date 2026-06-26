# ThorCluster — L2 cycle Specification

| Document ID | GPU_CLUSTER-L2_CYCLE-001 |
|-------------|--------------|
| Layer       | L2 cycle |
| Module      | ThorCluster |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Cycle-level 2-SM cluster model delegating to the L1 functional model.

### 1.2 Scope
Cycle-accurate timing and protocol behavior of ThorCluster.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `GPU_CLUSTER-L1_BEHAVIOR-001` (`layer_L1_behavior/specs/01_behavior_spec.md`) as input to `GPU_CLUSTER-L2_CYCLE-001`.

---

## 3. Outputs to Next Layer

Emits `GPU_CLUSTER-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `GPU_CLUSTER-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorCluster as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Latency Cycles | 1 |
| Pipeline Stages | dispatch, execute |

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
| C-01 | Module specification compliance | Thor-GPGPU top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Two's-complement integer / IEEE-754 FP semantics | Matches the Thor GPGPU datapath |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | cycle.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
