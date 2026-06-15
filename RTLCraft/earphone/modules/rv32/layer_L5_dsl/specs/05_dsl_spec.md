# EarphoneRV32 — L5 DSL Specification

| Document ID | RV32-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 DSL |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
RTL-ready DSL description of the EarphoneRV32 core.

### 1.2 Scope
3-stage RV32IM core for the smart earphone SoC.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `RV32-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), plus verification intent `RV32-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`) and latest evidence `RV32-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `RV32-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`), `RV32-L5_DSL-TP-001` (`layer_L5_dsl/specs/05_dsl_test_plan.md`), and `RV32-L5_DSL-TR-001` (`layer_L5_dsl/specs/05_dsl_test_report.md`) as inputs to `RV32-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneRV32 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### DSL Class

EarphoneRV32

### Public Methods

- __init__
- __repr__
- __setattr__
- _check_narrow_in_expr
- _collect_assigned_sigs
- _expr_name
- _lint_missing_case_default
- _lint_missing_default_assignment
- _lint_narrow_const
- _lint_narrow_const_comparison
- _lint_redundant_assignment
- _lint_signed_mix
- _lint_valid_ready
- _lint_width_truncation
- add_assertion
- add_comment
- add_constraint
- add_decision
- add_localparam
- add_memory


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
| C-01 | Module specification compliance | Top-level SoC spec |

### 7.2 Assumptions
| ID | Assumption | Rationale |
|----|------------|-----------|
| A-01 | Little-endian byte ordering | Matches target bus architecture |

---

## 8. Deliverables

| ID | Deliverable | Format | Owner |
|----|-------------|--------|-------|
| D-01 | dsl.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-15 | RTLCraft Agent | Initial draft. |
