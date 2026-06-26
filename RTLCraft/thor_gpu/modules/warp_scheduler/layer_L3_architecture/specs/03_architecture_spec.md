# ThorWarpScheduler — L3 architecture Specification

| Document ID | WARP_SCHEDULER-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | ThorWarpScheduler |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Sticky round-robin warp scheduler with barrier synchronization.

### 1.2 Scope
Micro-architectural decisions for ThorWarpScheduler.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `WARP_SCHEDULER-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `WARP_SCHEDULER-L3_ARCHITECTURE-001`.

---

## 3. Outputs to Next Layer

Emits `WARP_SCHEDULER-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `WARP_SCHEDULER-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorWarpScheduler as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Pipeline | combinational scheduler decision feeding a warp_sel register |
| Stages | decision, warp_sel_register |
| Num Warps | 4 |
| Policy | sticky round-robin (advance only when current warp idle) |
| Latency Cycles | 1 |
| Invariants | warp_sel advances to warp_sel+1 only when the currently selected warp is idle., A warp is idle when in IDLE/DONE/BARRIER state., barrier_release asserts when all warps are at the barrier or done., sm_done asserts when all warps have reached DONE. |

---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests + cross-layer checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional correctness | Directed tests | All operations exercised |

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
| D-01 | arch.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
