# ThorVectorALU — L3 architecture Specification

| Document ID | VECTOR_ALU-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | ThorVectorALU |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
8-lane INT32 vector ALU with per-lane active-mask predication.

### 1.2 Scope
Micro-architectural decisions for ThorVectorALU.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `VECTOR_ALU-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `VECTOR_ALU-L3_ARCHITECTURE-001`.

---

## 3. Outputs to Next Layer

Emits `VECTOR_ALU-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `VECTOR_ALU-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorVectorALU as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Pipeline | combinational per-lane compute feeding a 1-stage result register |
| Stages | lane_compute, result_register |
| Lane Width | 32 |
| Lane Count | 8 |
| Vector Width | 256 |
| Latency Cycles | 1 |
| Function Codes | 0, 1, 4, 5, 6, 7, 10, 12, 14 |
| Invariants | Each lane computes independently on a 32-bit slice of the source vectors., Disabled lanes (active_mask bit low) produce zero and clear their result_mask bit., ADD/SUB wrap modulo 2**32 (two's-complement)., SLT is signed; SLTU is unsigned., Shift amount is masked to 5 bits (s2 & 0x1F). |

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
