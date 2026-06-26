# ThorCluster — L3 architecture Specification

| Document ID | GPU_CLUSTER-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | ThorCluster |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
2-SM compute cluster sharing one global memory port via a round-robin L2 arbiter.

### 1.2 Scope
Micro-architectural decisions for ThorCluster.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `GPU_CLUSTER-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `GPU_CLUSTER-L3_ARCHITECTURE-001`.

---

## 3. Outputs to Next Layer

Emits `GPU_CLUSTER-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `GPU_CLUSTER-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorCluster as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Pipeline | SM x2 -> round-robin L2 arbiter -> global memory |
| Stages | sm_compute, l2_arbiter, global_memory |
| Nsm | 2 |
| Arbiter | round-robin (1-bit grant toggling on any_req & mem_ready) |
| Latency Cycles | 1 |
| Invariants | Each SM owns its IMEM write port and its warp state., The L2 arbiter grants one SM per cycle and toggles on completion., all_done asserts when both SMs report sm_done., Global memory responses are steered to the SM that holds the grant. |

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
