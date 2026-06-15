# EarphoneRV32 — L6 Verilog Specification

| Document ID | RV32-L6_VERILOG-001 |
|-------------|--------------|
| Layer       | L6 Verilog |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Synthesizable Verilog generation and lint reporting.

### 1.2 Scope
Generated RTL from the L5 DSL via rtlgen VerilogEmitter.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `RV32-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`), plus verification intent `RV32-L5_DSL-TP-001` (`layer_L5_dsl/specs/05_dsl_test_plan.md`) and latest evidence `RV32-L5_DSL-TR-001` (`layer_L5_dsl/specs/05_dsl_test_report.md`).

---

## 3. Outputs to Next Layer

Emits the final RTL-generation contract `RV32-L6_VERILOG-001` (`layer_L6_verilog/specs/06_verilog_spec.md`), verification plan `RV32-L6_VERILOG-TP-001` (`layer_L6_verilog/specs/06_verilog_test_plan.md`), and execution evidence `RV32-L6_VERILOG-TR-001` (`layer_L6_verilog/specs/06_verilog_test_report.md`) for module-level sign-off.

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneRV32 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Deliverables

| Deliverable | Description |
| --- | --- |
| earphone_rv32.v | Top-level RTL |
| Lint report | Static lint issue summary |
| SVA constraints | Derived assertion sequences |


---

## 6. Verification Considerations

### 6.1 Verification Strategy
Verilog generation, lint, and simulation.

### 6.2 Key Verification Points
| ID | Check | Method | Coverage Goal |
|----|-------|--------|---------------|
| V-01 | Generated RTL matches DSL semantics | Verilog simulation + SVA checks | Module-level RTL coverage |

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
| D-01 | emitter.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-15 | RTLCraft Agent | Initial draft. |
