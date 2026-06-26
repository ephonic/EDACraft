# ThorLSU — L4 structure Specification

| Document ID | LSU-L4_STRUCTURE-001 |
|-------------|--------------|
| Layer       | L4 structure |
| Module      | ThorLSU |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Decomposition into request generator and response capture.

### 1.2 Scope
Structural decomposition of ThorLSU.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `LSU-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `LSU-L4_STRUCTURE-001`.

---

## 3. Outputs to Next Layer

Emits `LSU-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`) as input to `LSU-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorLSU as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Subblocks | request_gen, response_cap |
| External Interfaces | mem_request, mem_response |

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
| D-01 | structure.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
