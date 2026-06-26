# ThorSIMTStack — L3 architecture Specification

| Document ID | SIMT_STACK-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | ThorSIMTStack |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
SIMT divergence/reconvergence stack for conditional branches.

### 1.2 Scope
Micro-architectural decisions for ThorSIMTStack.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `SIMT_STACK-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`) as input to `SIMT_STACK-L3_ARCHITECTURE-001`.

---

## 3. Outputs to Next Layer

Emits `SIMT_STACK-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`) as input to `SIMT_STACK-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorSIMTStack as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Pipeline | combinational push/pop with registered stack pointers |
| Stages | stack_update, output |
| Mask Width | 8 |
| Max Depth | 8 |
| Pc Width | 32 |
| Latency Cycles | 1 |
| Invariants | On push, the not-taken active lanes are saved with the reconvergence PC., On pop, control resumes at the saved PC with the saved mask., A divergent branch only pushes when taken and not-taken lanes both exist. |

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
