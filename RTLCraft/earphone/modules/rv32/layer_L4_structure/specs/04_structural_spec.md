# EarphoneRV32 — L4 StructuralIR Specification

| Document ID | RV32-L4_STRUCTURE-001 |
|-------------|--------------|
| Layer       | L4 StructuralIR |
| Module      | EarphoneRV32 |
| Version     | 0.1 |
| Date        | 2026-06-15 |
| Author      | RTLCraft Agent |
| Owner       | Design Team |
| Status      | Draft |

---

## 1. Purpose and Scope

### 1.1 Purpose
Define the major sub-blocks and their interface contracts.

### 1.2 Scope
Internal decomposition used by the L5 DSL generator.

---

## 2. Inputs from Previous Layer

Consumes approved outputs from `RV32-L3_ARCHITECTURE-001` (`layer_L3_architecture/specs/03_architecture_spec.md`), plus verification intent `RV32-L3_ARCHITECTURE-TP-001` (`layer_L3_architecture/specs/03_architecture_test_plan.md`) and latest evidence `RV32-L3_ARCHITECTURE-TR-001` (`layer_L3_architecture/specs/03_architecture_test_report.md`).

---

## 3. Outputs to Next Layer

Emits `RV32-L4_STRUCTURE-001` (`layer_L4_structure/specs/04_structural_spec.md`), `RV32-L4_STRUCTURE-TP-001` (`layer_L4_structure/specs/04_structural_test_plan.md`), and `RV32-L4_STRUCTURE-TR-001` (`layer_L4_structure/specs/04_structural_test_report.md`) as inputs to `RV32-L5_DSL-001` (`layer_L5_dsl/specs/05_dsl_spec.md`).

---

## 4. Key Design Decisions

| ID | Decision | Rationale | Impact |
|----|----------|-----------|--------|
| DEC-01 | Implement EarphoneRV32 as specified in top-level SoC spec | Matches target application and power/area constraints | Drives downstream implementation and verification |

---

## 5. Detailed Description

### Structure

| Sub-block | Description | Interfaces |
| --- | --- | --- |
| pc_unit | program counter generation and branch target | clk, rst_n, pc_next, pc |
| regfile | 32-entry x 32-bit register file | clk, rst_n, rs1_addr, rs2_addr, rd_addr, rd_wdata, rs1_rdata, rs2_rdata |
| decoder | instruction decode and control signal generation | instr, alu_op, imm, mem_op |
| alu | arithmetic/logic operations and branch comparison | a, b, alu_op, result, zero, lt, ltu |
| muldiv_unit | iterative M-extension multiply/divide | clk, rst_n, start, done, result |
| load_store_unit | data memory interface | addr, wdata, mask, we, rdata, valid |


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
| D-01 | structure.py | Python source | RTLCraft Agent |

---

## 9. Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | 2026-06-15 | RTLCraft Agent | Initial draft. |
