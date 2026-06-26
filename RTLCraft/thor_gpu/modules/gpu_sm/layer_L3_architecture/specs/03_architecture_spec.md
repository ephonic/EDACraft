# ThorGpuSM — L3 architecture Specification

| Document ID | GPU_SM-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | ThorGpuSM |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
One streaming multiprocessor: scheduler + SIMT core + exec units + LSU + shared memory.

### 1.2 Scope
Micro-architectural decisions for ThorGpuSM.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `GPU_SM-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `GPU_SM-L3_ARCHITECTURE-001`.

---

## 3. Outputs to Next Layer

Emits `GPU_SM-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `GPU_SM-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorGpuSM as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Pipeline | fetch -> decode -> execute/writeback (multi-cycle for memory) |
| Stages | fetch, decode, execute, writeback |
| Xlen | 32 |
| Nlane | 8 |
| Vlen | 256 |
| Vregs | 8 |
| Nwarp | 4 |
| Imem Depth | 32 |
| Accw | 64 |
| Latency Cycles | 1 |
| Invariants | VRF is a flat array; warp w owns indices [w*VREGS, (w+1)*VREGS)., The sticky-RR scheduler dispatches one warp per cycle., VMAC accumulates lane-0 product into a 64-bit per-warp accumulator., sm_done asserts when all warps reach DONE. |

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
