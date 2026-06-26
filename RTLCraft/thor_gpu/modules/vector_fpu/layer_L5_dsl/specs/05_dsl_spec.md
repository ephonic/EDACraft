# ThorVectorFPU — L5 dsl Specification

| Document ID | VECTOR_FPU-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 dsl |
| Module      | ThorVectorFPU |
| Version     | 0.1 |
| Date        | 2026-06-17 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
RTL-ready 8-lane FP32 FPU structural datapath (FP core black-box in v0.1).

### 1.2 Scope
RTL-ready DSL description of ThorVectorFPU.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `VECTOR_FPU-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`) as input to `VECTOR_FPU-L5_DSL-001`.

---

## 3. Outputs to Next Layer

Emits `VECTOR_FPU-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`) as input to `VECTOR_FPU-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement ThorVectorFPU as specified in the Thor-GPGPU SoC spec | Matches the target GPGPU compute-cluster architecture | Drives downstream implementation and verification |

---

## 5. Detailed Description

| Property | Value |
| --- | --- |
| Dsl Class | ThorVectorFPU |
| Ports | src1[256], src2[256], src3[256], active_mask[8], fpu_fn[2], valid_in -> result[256], result_mask[8], valid |

### Ports

`src1[256], src2[256], src3[256], active_mask[8], fpu_fn[2], valid_in -> result[256], result_mask[8], valid`


### Note

L1/L2 carry exact IEEE-754; L5 is structural black-box FP slice (v0.1).


---

## 6. Verification Considerations

### 6.1 Verification Strategy
DSL simulation and cross-layer equivalence with L1/L2.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | DSL implementation matches reference model | rtlgen Simulator + LayerVerifier | All functional paths covered |

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
| D-01 | dsl.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-17 | RTLCraft Agent | Initial draft. |
