# EarphoneSIMD16 — L3 architecture Specification

| Document ID | SIMD16-L3_ARCHITECTURE-001 |
|-------------|--------------|
| Layer       | L3 architecture |
| Module      | EarphoneSIMD16 |
| Version     | 0.1 |
| Date        | 2026-06-18 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
16-lane vector ALU with single-cycle INT16 ops and a 3-stage FP16 MAC pipeline.

### 1.2 Scope
Micro-architectural decisions for EarphoneSIMD16.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `SIMD16-L2_CYCLE-001` (`layer_L2_cycle/specs/02_cycle_spec.md`), plus verification intent `SIMD16-L2_CYCLE-TP-001` (`layer_L2_cycle/specs/02_cycle_test_plan.md`) and latest evidence `SIMD16-L2_CYCLE-TR-001` (`layer_L2_cycle/specs/02_cycle_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `SIMD16-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), `SIMD16-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`), and `SIMD16-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`) as inputs to `SIMD16-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneSIMD16 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Notes

- Status: implemented

### Detailed Table

| Property | Value |
| --- | --- |
| Pipeline | single-cycle INT16 path plus 3-stage FP16 MAC pipeline |
| Stages | issue, int_execute, fp_stage0, fp_stage1, fp_stage2, writeback |
| Vector Width | 256 |
| Lane Width | 16 |
| Lane Count | 16 |
| Int Latency Cycles | 1 |
| Fp Latency Cycles | 3 |
| Predicate Support | 16-bit per-lane mask |
| Invariants | INT16 operations complete in one cycle when start is asserted in integer mode., FP16 MAC results appear after three occupied pipeline stages., Predicate masking zeros disabled lanes in both INT16 and FP16 datapaths. |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Python unit tests + cross-layer equivalence checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Functional correctness | Directed tests | All operations exercised |

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
| D-01 | arch.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-18 | RTLCraft Agent | Initial draft. |
