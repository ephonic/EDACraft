# EarphoneRV32 — L5 DSL Specification

| Document ID | RV32-L5_DSL-001 |
|-------------|--------------|
| Layer       | L5 DSL |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-14 |
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

See previous layer specification for inputs.

---

## 3. Outputs to Next Layer

See next layer specification for outputs.

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Single-cycle scalar with iterative M-extension | Area/power optimized for earphone-class MCU | DIV/REM take variable cycles |

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
Python unit tests + cross-layer equivalence checks.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Instruction decode and execution correctness | Directed ISS tests | All RV32IM instructions exercised |

---

## 7. Constraints and Assumptions

### 7.1 Constraints
| ID | Constraint | Source |
|----|------------|--------|
| C-01 | RV32IM ISA compliance | Top-level SoC spec |

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
| 0.1 | 2026-06-14 | RTLCraft Agent | Initial draft. |
